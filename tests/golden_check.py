"""Golden outputs: the engine's results saved in tests/golden/*.json.

A test builds a summary of what the engine decides (P1 rankings, a simulated game, a
built board) and compares it with the saved file. When a change moves a result on
purpose, run ``pytest --update-golden`` and add a line to docs/KARARLAR.md that says what
moved and why (the pre-commit check asks for it).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

GOLDEN_DIR = Path(__file__).parent / "golden"
DIGITS = 4
MAX_SHOWN = 25


def rounded(value: Any) -> Any:
    """Round floats and turn tuples into lists so a summary survives a JSON round trip."""
    if isinstance(value, float):
        return round(value, DIGITS)
    if isinstance(value, dict):
        return {str(k): rounded(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [rounded(v) for v in value]
    return value


def _flat(value: Any, path: str = "") -> dict[str, Any]:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            out.update(_flat(v, f"{path}.{k}" if path else str(k)))
        return out
    return {path: value}


def differences(old: Any, new: Any) -> list[str]:
    a, b = _flat(old), _flat(new)
    lines = []
    for key in sorted(set(a) | set(b)):
        if key not in a:
            lines.append(f"  + {key} = {b[key]!r}")
        elif key not in b:
            lines.append(f"  - {key} (was {a[key]!r})")
        elif a[key] != b[key]:
            lines.append(f"  ~ {key}: {a[key]!r} -> {b[key]!r}")
    return lines


def assert_golden(name: str, summary: Any, update: bool) -> None:
    path = GOLDEN_DIR / f"{name}.json"
    summary = rounded(summary)
    if update or not path.exists():
        if not update:
            raise AssertionError(f"{path.name} missing; create it with pytest --update-golden")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n", "utf-8")
        return
    saved = json.loads(path.read_text(encoding="utf-8"))
    if saved != summary:
        diff = differences(saved, summary)
        shown = "\n".join(diff[:MAX_SHOWN])
        more = f"\n  ... {len(diff) - MAX_SHOWN} more" if len(diff) > MAX_SHOWN else ""
        raise AssertionError(
            f"golden output {path.name} changed ({len(diff)} values):\n{shown}{more}\n"
            "If this is intended: pytest --update-golden, then a line in docs/KARARLAR.md."
        )
