"""Run every check the repo requires before a commit (CLAUDE.md rule 4) plus the audit.

    .venv/Scripts/python.exe tools/verify.py          # everything
    .venv/Scripts/python.exe tools/verify.py --quick  # skip pytest (while working)

The git pre-commit hook (.githooks/pre-commit) runs it without --quick. It checks the
working tree, so unstaged edits count too.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STEPS = [
    ("pytest", [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]),
    ("ruff check", [sys.executable, "-m", "ruff", "check", "."]),
    ("ruff format", [sys.executable, "-m", "ruff", "format", "--check", "."]),
    ("audit", [sys.executable, "-m", "tft_engine", "audit"]),
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--quick", action="store_true", help="skip pytest")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):  # Windows consoles default to a legacy code page
        sys.stdout.reconfigure(encoding="utf-8")
    results = []
    for name, cmd in STEPS:
        if args.quick and name == "pytest":
            results.append((name, None, 0.0))
            continue
        start = time.perf_counter()
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
        took = time.perf_counter() - start
        ok = proc.returncode == 0
        results.append((name, ok, took))
        out = (proc.stdout + proc.stderr).strip().splitlines()
        if name == "audit":  # known debt stays out of the way; `tft-engine audit` lists it
            out = [x for x in out if x.startswith(("ERROR", "WARNING", "audit:", "Traceback"))]
            print(f"--- {name} ---")
            print("\n".join(out))
        elif not ok:
            print(f"--- {name} ---")
            print("\n".join(out[-40:]))
    print("\n=== verify ===")
    for name, ok, took in results:
        mark = "atlandı" if ok is None else ("OK" if ok else "HATA")
        print(f"  {name:12} {mark:8} {took:5.1f} sn")
    failed = [n for n, ok, _ in results if ok is False]
    if failed:
        print(f"Başarısız: {', '.join(failed)}. Commit yapılmamalı.")
        return 1
    print("Hepsi geçti.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
