"""Numbers written in the code (rules 6 and 8).

Game values belong in the data, model numbers in ``decision/assumptions.py``. This check
finds module constants and inline decimals in ``src/`` and reports:

- a table that repeats a value table from a set's ``base.json`` (a second copy of a rule);
- the same table defined in two modules;
- any other number not accepted in ``audit.toml`` with a reason.

Integers inside functions are not reported (indexes, counts, loop bounds); decimals are,
except tolerances below 1e-5.
"""

from __future__ import annotations

import ast
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from tft_engine.audit.core import AuditConfig, Finding

SKIP_FILES = ("decision/assumptions.py",)  # the home of model numbers
SKIP_PACKAGES = ("audit/",)
TOLERANCE = 1e-5
MIN_TABLE = 3  # shorter sequences match data by chance


def package_dir(root: Path) -> Path:
    return root / "src" / "tft_engine"


def source_files(root: Path) -> Iterator[tuple[str, ast.Module]]:
    pkg = package_dir(root)
    for path in sorted(pkg.rglob("*.py")):
        rel = path.relative_to(pkg).as_posix()
        if rel in SKIP_FILES or rel.startswith(SKIP_PACKAGES):
            continue
        yield rel, ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _literal_numbers(node: ast.AST) -> list[float] | None:
    """Numbers of a literal (number or container of literals); None if it is not one."""
    if isinstance(node, ast.Constant):
        v = node.value
        if isinstance(v, bool) or not isinstance(v, int | float):
            return [] if isinstance(v, str | bytes | type(None)) else None
        return [v]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        inner = _literal_numbers(node.operand)
        return None if inner is None else [-x for x in inner]
    if isinstance(node, ast.List | ast.Tuple | ast.Set):
        parts = [_literal_numbers(e) for e in node.elts]
    elif isinstance(node, ast.Dict):
        # keys are labels (1/2/3 star, cost ...); the values are the table
        parts = [_literal_numbers(v) for v in node.values]
        if any(k is not None and _literal_numbers(k) is None for k in node.keys):
            return None
    else:
        return None
    if any(p is None for p in parts):
        return None
    return [x for p in parts for x in p]


def module_constants(tree: ast.Module) -> Iterator[tuple[str, int, list[float]]]:
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, value = node.targets[0], node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            target, value = node.target, node.value
        else:
            continue
        # A, B = 1, 2 assigns each name its own value
        if isinstance(target, ast.Tuple) and isinstance(value, ast.Tuple):
            pairs = list(zip(target.elts, value.elts, strict=False))
        else:
            pairs = [(target, value)]
        for name, val in pairs:
            if not isinstance(name, ast.Name) or name.id == "__all__":
                continue
            nums = _literal_numbers(val)
            if nums:
                yield name.id, node.lineno, nums


def inline_decimals(tree: ast.Module) -> Iterator[tuple[str, int, list[float]]]:
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        found = [
            n.value
            for n in ast.walk(fn)
            if isinstance(n, ast.Constant)
            and type(n.value) is float
            and n.value not in (0.0, 1.0)
            and abs(n.value) >= TOLERANCE
        ]
        if found:
            yield fn.name, fn.lineno, found


def _flat_values(node: ast.AST) -> tuple[float, ...] | None:
    """Values of a one-level numeric table literal ({1: 1, 2: 3} or (1, 3, 9)), else None."""
    if isinstance(node, ast.Dict):
        nums = [_literal_numbers(v) for v in node.values]
    elif isinstance(node, ast.List | ast.Tuple):
        nums = [_literal_numbers(v) for v in node.elts]
    else:
        return None
    if nums and all(n is not None and len(n) == 1 for n in nums):
        return tuple(float(n[0]) for n in nums)
    return None


def _plain_counter(values: tuple[float, ...]) -> bool:
    """Zero-filled counters and 0, 1, 2 ... orderings are not rule tables."""
    if all(v == 0 for v in values):
        return True
    start = values[0]
    return start in (0, 1) and values == tuple(start + i for i in range(len(values)))


def inline_tables(tree: ast.Module) -> Iterator[tuple[str, int, list[tuple[float, ...]]]]:
    """Numeric tables written inside functions (a rule table hidden in the code)."""
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        found = []
        for n in ast.walk(fn):
            values = _flat_values(n)
            if values and len(values) >= MIN_TABLE and not _plain_counter(values):
                found.append(values)
        if found:
            yield fn.name, fn.lineno, found


def _sequences(value: Any, path: str) -> Iterator[tuple[str, tuple[float, ...]]]:
    """Every list, and every dict of plain numbers, inside a data value."""
    if isinstance(value, list):
        if all(isinstance(x, int | float) and not isinstance(x, bool) for x in value):
            yield path, tuple(float(x) for x in value)
        for i, x in enumerate(value):
            yield from _sequences(x, f"{path}.{i}")
    elif isinstance(value, dict):
        vals = list(value.values())
        if vals and all(isinstance(x, int | float) and not isinstance(x, bool) for x in vals):
            yield path, tuple(float(x) for x in vals)
        for k, x in value.items():
            yield from _sequences(x, f"{path}.{k}")


def data_tables(root: Path) -> dict[tuple[float, ...], str]:
    tables: dict[tuple[float, ...], str] = {}
    for base in sorted((root / "data" / "sets").glob("*/base.json")):
        raw = json.loads(base.read_text(encoding="utf-8"))
        for group in ("params", "shop_rules"):
            for name, param in raw.get(group, {}).items():
                for path, seq in _sequences(param.get("value"), name):
                    if len(seq) >= MIN_TABLE:
                        tables.setdefault(seq, f"{base.parent.name} {path}")
    return tables


def check_constants(root: Path, config: AuditConfig) -> Iterator[Finding]:
    tables = data_tables(root)
    defined: dict[tuple[float, ...], str] = {}
    for rel, tree in source_files(root):
        for name, line, nums in module_constants(tree):
            key = f"{rel}:{name}"
            values = tuple(float(x) for x in nums)
            # dict tables: compare the values only (the keys are labels)
            node_values = _table_values(tree, name)
            if node_values and node_values in tables:
                yield Finding(
                    "constants",
                    key,
                    f"line {line}: same numbers as data value {tables[node_values]}; if it is "
                    "the same rule, read it through the data layer (rule 8), otherwise accept "
                    "it in audit.toml",
                )
                defined.setdefault(node_values, key)
                continue
            if node_values and len(node_values) >= MIN_TABLE and node_values in defined:
                yield Finding(
                    "constants",
                    key,
                    f"line {line}: same table as {defined[node_values]} (one source of truth)",
                )
                continue
            if node_values and len(node_values) >= MIN_TABLE:
                defined[node_values] = key
            yield Finding(
                "constants",
                key,
                f"line {line}: number(s) {_short(values)} in code; move to the data or "
                "assumptions.py, or accept it in audit.toml with a reason",
            )
        for fn, line, found in inline_tables(tree):
            known = [defined.get(v) or tables.get(v) for v in found]
            same = "; ".join(f"same numbers as {k}" for k in known if k)
            yield Finding(
                "constants",
                f"{rel}:{fn}():table",
                f"line {line}: number table(s) {', '.join(_short(v) for v in found)} inside "
                f"the function{'; ' + same if same else ''}; move to the data or "
                "assumptions.py, or accept it in audit.toml with a reason",
            )
        for fn, line, nums in inline_decimals(tree):
            yield Finding(
                "constants",
                f"{rel}:{fn}()",
                f"line {line}: decimal(s) {_short(nums)} inside the function; move to "
                "assumptions.py or the data, or accept it in audit.toml with a reason",
            )


def _table_values(tree: ast.Module, name: str) -> tuple[float, ...] | None:
    for node in tree.body:
        targets = node.targets if isinstance(node, ast.Assign) else []
        if isinstance(node, ast.AnnAssign):
            targets = [node.target]
        if any(isinstance(t, ast.Name) and t.id == name for t in targets):
            return _flat_values(node.value)
    return None


def _short(nums: list[float] | tuple[float, ...]) -> str:
    text = ", ".join(f"{x:g}" for x in list(nums)[:6])
    return text + (", ..." if len(nums) > 6 else "")
