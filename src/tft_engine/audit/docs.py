"""Docs that point at nothing, and a status page older than the work it describes."""

from __future__ import annotations

import re
import subprocess
from collections.abc import Iterator
from datetime import date
from pathlib import Path

from tft_engine.audit.core import AuditConfig, Finding

LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
# backticked repo paths such as `src/tft_engine/rules/items.py` or `curated/comps/`
CODE_PATH = re.compile(r"`((?:src|docs|data|tools|tests|scenarios|templates)/[^`\s]*)`")
STATUS_DATE = re.compile(r"Son güncelleme:\s*(\d{4}-\d{2}-\d{2})")
PLACEHOLDER = re.compile(r"[<*{]|\.\.\.")
# docs that describe the repo as it is now; plans and reviews of other projects name
# paths that do not exist (yet), so only their links are checked
CURRENT_STATE_DOCS = ("README.md", "CLAUDE.md", "docs/DURUM.md")


def doc_files(root: Path) -> list[Path]:
    files = [root / "README.md", root / "CLAUDE.md", *sorted((root / "docs").glob("*.md"))]
    return [f for f in files if f.exists()]


def _exists(root: Path, base: Path, target: str) -> bool:
    target = target.split("#")[0]
    if not target or target.startswith(("http://", "https://", "mailto:")):
        return True
    return (base / target).exists() or (root / target).exists()


def check(root: Path, config: AuditConfig) -> Iterator[Finding]:
    for doc in doc_files(root):
        rel = doc.relative_to(root).as_posix()
        text = doc.read_text(encoding="utf-8")
        for m in LINK.finditer(text):
            if not _exists(root, doc.parent, m.group(1)):
                yield Finding("docs", f"{rel}->{m.group(1)}", "link points at a missing file")
        if rel not in CURRENT_STATE_DOCS:
            continue
        for m in CODE_PATH.finditer(text):
            path = m.group(1)
            if PLACEHOLDER.search(path):
                continue
            if not (root / path).exists():
                yield Finding("docs", f"{rel}->{path}", "path in the text does not exist")
    yield from _status_freshness(root)
    yield from _generated(root, config)


def _generated(root: Path, config: AuditConfig) -> Iterator[Finding]:
    from tft_engine.audit.registry import generated_docs

    for rel, text in generated_docs(root, config).items():
        path = root / rel
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            yield Finding(
                "docs",
                f"{rel}:generated",
                "out of date with the code; run tft-engine audit --write-docs",
            )


def last_change(root: Path, *paths: str) -> date | None:
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", *paths],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return date.fromisoformat(out) if out else None


def _status_freshness(root: Path) -> Iterator[Finding]:
    status = root / "docs" / "DURUM.md"
    if not status.exists():
        return
    m = STATUS_DATE.search(status.read_text(encoding="utf-8"))
    if not m:
        yield Finding("docs", "docs/DURUM.md:date", "no 'Son güncelleme: YYYY-MM-DD' line")
        return
    stated = date.fromisoformat(m.group(1))
    work = last_change(root, "src", "data")
    if work and work > stated:
        yield Finding(
            "docs",
            "docs/DURUM.md:date",
            f"says {stated}, but src/ or data/ changed on {work}; update the status",
            "warning",
        )
