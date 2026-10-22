"""Disconnected pieces: data, files, modules and assumptions that nothing uses.

- every ``base.json`` parameter is read somewhere in the code;
- every ``curated/`` folder or file has a loader in the code;
- every module is reachable from the CLI or a tool;
- every assumption in ``assumptions.py`` is used;
- the lists of item stat names agree.

``connections`` returns the same map as data (parameter -> modules that read it, curated
entry -> loaders, module -> importers) for docs/BAGLANTILAR.md.
"""

from __future__ import annotations

import ast
import json
import re
from collections.abc import Iterator
from pathlib import Path

from tft_engine.audit.core import AuditConfig, Finding
from tft_engine.audit.source_scan import package_dir

PKG = "tft_engine"


def _texts(root: Path, skip: tuple[str, ...] = ()) -> dict[str, str]:
    pkg = package_dir(root)
    out = {}
    for path in sorted(pkg.rglob("*.py")):
        rel = path.relative_to(pkg).as_posix()
        if rel.startswith("audit/") or rel in skip:
            continue
        out[rel] = path.read_text(encoding="utf-8")
    return out


def _tool_texts(root: Path) -> dict[str, str]:
    return {
        f"tools/{p.name}": p.read_text(encoding="utf-8")
        for p in sorted((root / "tools").glob("*.py"))
    }


def _quoted(name: str) -> re.Pattern[str]:
    return re.compile(r"[\"']" + re.escape(name) + r"[\"']")


def _path_ref(name: str) -> re.Pattern[str]:
    n = re.escape(name)
    return re.compile(rf"[\"'/]{n}(\.json)?[\"'/]")


def _readers(texts: dict[str, str], pattern: re.Pattern[str]) -> list[str]:
    return [rel for rel, text in texts.items() if pattern.search(text)]


# --- data parameters and curated files -------------------------------------------------


def param_names(root: Path) -> dict[str, list[str]]:
    """Parameter name -> sets whose base.json defines it."""
    out: dict[str, list[str]] = {}
    for base in sorted((root / "data" / "sets").glob("*/base.json")):
        raw = json.loads(base.read_text(encoding="utf-8"))
        for group in ("params", "shop_rules"):
            for name in raw.get(group, {}):
                out.setdefault(name, []).append(base.parent.name)
    return out


def curated_entries(root: Path) -> dict[str, list[str]]:
    """Top-level curated folder or file name -> sets that have it."""
    out: dict[str, list[str]] = {}
    for cur in sorted((root / "data" / "sets").glob("*/curated")):
        for entry in sorted(cur.iterdir()):
            out.setdefault(entry.stem, []).append(cur.parent.name)
    return out


# --- modules ---------------------------------------------------------------------------


def _module_name(rel: str) -> str:
    parts = rel[:-3].split("/")
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join([PKG, *parts])


def _imported(tree: ast.Module, current: str, is_pkg: bool) -> set[str]:
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = current.split(".")
                base = base if is_pkg else base[:-1]
                base = base[: len(base) - (node.level - 1)]
                mod = ".".join(base + ([node.module] if node.module else []))
            else:
                mod = node.module or ""
            out.add(mod)
            out.update(f"{mod}.{a.name}" for a in node.names)
    return {m for m in out if m == PKG or m.startswith(PKG + ".")}


def import_graph(root: Path) -> dict[str, set[str]]:
    """Module -> tft_engine modules it imports (packages import their __init__)."""
    pkg = package_dir(root)
    graph: dict[str, set[str]] = {}
    for path in sorted(pkg.rglob("*.py")):
        rel = path.relative_to(pkg).as_posix()
        name = _module_name(rel)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        graph[name] = _imported(tree, name, rel.endswith("__init__.py"))
    for name in list(graph):  # importing a.b.c runs a and a.b first
        parts = name.split(".")
        for i in range(1, len(parts)):
            graph[name].add(".".join(parts[:i]))
    return {k: {m for m in v if m in graph and m != k} for k, v in graph.items()}


def tool_imports(root: Path) -> set[str]:
    out: set[str] = set()
    for path in sorted((root / "tools").glob("*.py")):
        out |= _imported(ast.parse(path.read_text(encoding="utf-8")), "tools", False)
    return out


def reachable(root: Path) -> set[str]:
    graph = import_graph(root)
    todo = [m for m in {f"{PKG}.cli", f"{PKG}.__main__"} | tool_imports(root) if m in graph]
    seen: set[str] = set()
    while todo:
        m = todo.pop()
        if m in seen:
            continue
        seen.add(m)
        todo.extend(graph.get(m, ()))
    return seen


# --- checks ----------------------------------------------------------------------------


def check(root: Path, config: AuditConfig) -> Iterator[Finding]:
    texts = _texts(root)
    for name in param_names(root):
        if not _readers(texts, _quoted(name)):
            yield Finding("wiring", f"param:{name}", "no code reads this data parameter")
    loaders = {**texts, **_tool_texts(root)}  # importers in tools/ load curated files too
    for name in curated_entries(root):
        if not _readers(loaders, _path_ref(name)) and not _readers(loaders, _quoted(name)):
            yield Finding("wiring", f"curated:{name}", "no code loads this curated folder/file")
    graph = import_graph(root)
    live = reachable(root)
    for mod in sorted(set(graph) - live):
        if mod.startswith(f"{PKG}.audit"):
            continue
        yield Finding(
            "wiring",
            f"module:{mod}",
            "not reachable from the CLI or a tool (only tests use it, or nothing)",
        )
    yield from _check_assumptions(root, config)
    yield from _check_stats(config)


def _check_assumptions(root: Path, config: AuditConfig) -> Iterator[Finding]:
    from tft_engine.decision.assumptions import DEFAULTS

    texts = _texts(root, skip=("decision/assumptions.py",))
    for key in DEFAULTS:
        if not _readers(texts, _quoted(key)):
            yield Finding("wiring", f"assumption:{key}", "assumption defined but never used")
    # assumptions written before the basis field may lack one; new ones may not
    legacy = set(config.extra.get("assumptions", {}).get("legacy_without_basis", []))
    for key, a in DEFAULTS.items():
        if not a.basis and key not in legacy:
            yield Finding(
                "wiring",
                f"assumption:{key}:basis",
                "new assumption without a basis (where does the value come from?)",
            )
        elif a.basis and key in legacy:
            yield Finding(
                "wiring",
                f"assumption:{key}:basis",
                "has a basis now; remove it from audit.toml legacy_without_basis",
                "warning",
            )


def _check_stats(config: AuditConfig) -> Iterator[Finding]:
    from tft_engine.decision.assumptions import DEFAULTS
    from tft_engine.gamedata.curated import STAT_KEYS
    from tft_engine.rules.board_stats import EFFECT_STATS, ITEM_TO_EFFECT, PCT_ITEM_KEYS

    keys = set(STAT_KEYS)
    if set(ITEM_TO_EFFECT) != keys:
        diff = sorted(set(ITEM_TO_EFFECT) ^ keys)
        yield Finding(
            "wiring",
            "stats:ITEM_TO_EFFECT",
            f"board_stats.ITEM_TO_EFFECT and curated.STAT_KEYS differ: {diff}",
        )
    bad = sorted(set(ITEM_TO_EFFECT.values()) - set(EFFECT_STATS))
    if bad:
        yield Finding("wiring", "stats:EFFECT_STATS", f"effect stats not in EFFECT_STATS: {bad}")
    bad = sorted(PCT_ITEM_KEYS - keys)
    if bad:
        yield Finding("wiring", "stats:PCT_ITEM_KEYS", f"not item stat keys: {bad}")
    extra = set(config.extra.get("stats", {}).get("fit_only_keys", []))
    fit = DEFAULTS["item_fit_weights"].default
    used = {k for v in fit.values() if isinstance(v, dict) for k in v}
    bad = sorted(used - keys - extra)
    if bad:
        yield Finding(
            "wiring",
            "stats:item_fit_weights",
            f"item_fit_weights uses stat names that items do not have: {bad}",
        )


def connections(root: Path) -> dict[str, dict[str, list[str]]]:
    """Who reads what, for docs/BAGLANTILAR.md."""
    texts = _texts(root)
    loaders = {**texts, **_tool_texts(root)}
    params = {n: _readers(texts, _quoted(n)) for n in param_names(root)}
    curated = {
        n: sorted(set(_readers(loaders, _path_ref(n)) + _readers(loaders, _quoted(n))))
        for n in curated_entries(root)
    }
    graph = import_graph(root)
    users: dict[str, list[str]] = {m: [] for m in graph}
    for mod, deps in graph.items():
        for d in deps:
            if not mod.startswith(d + ".") and d != PKG:  # skip "package of" edges
                users[d].append(mod)
    tools = tool_imports(root)
    for m in tools:
        if m in users:
            users[m].append("tools/")
    from tft_engine.decision.assumptions import DEFAULTS

    atexts = _texts(root, skip=("decision/assumptions.py",))
    assumptions = {k: _readers(atexts, _quoted(k)) for k in DEFAULTS}
    return {
        "params": params,
        "curated": curated,
        "modules": {k: sorted(set(v)) for k, v in sorted(users.items())},
        "assumptions": assumptions,
    }
