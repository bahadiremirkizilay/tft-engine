"""Layer rules: no network in the core (rule 7), no unseeded randomness (rule 5)."""

from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path

from tft_engine.audit.core import AuditConfig, Finding
from tft_engine.audit.source_scan import source_files

CORE = ("gamedata/", "state/", "rules/", "prob/", "decision/", "sim/")
NETWORK = ("urllib", "requests", "http", "socket", "httpx", "aiohttp", "ftplib", "smtplib")
# a seeded generator is built only through tft_engine.repro (derive_seed / make_rng)
SEEDED_HOME = "repro/"


def _imports(tree: ast.Module) -> Iterator[tuple[str, int]]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name, node.lineno
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            yield node.module, node.lineno


def _dotted(node: ast.AST) -> str:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def check(root: Path, config: AuditConfig) -> Iterator[Finding]:
    for rel, tree in source_files(root):
        if rel.startswith(CORE):
            for mod, line in _imports(tree):
                if mod.split(".")[0] in NETWORK:
                    yield Finding(
                        "layers",
                        f"{rel}:import {mod}",
                        f"line {line}: network module in a core layer (rule 7: network lives "
                        "in tools/)",
                    )
        if rel.startswith(SEEDED_HOME):
            continue
        for mod, line in _imports(tree):
            if mod == "random":
                yield Finding(
                    "layers",
                    f"{rel}:import random",
                    f"line {line}: stdlib random; use tft_engine.repro.make_rng (rule 5)",
                )
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = _dotted(node.func)
                if ".random." in f".{name}" and name.split(".")[0] in ("np", "numpy"):
                    yield Finding(
                        "layers",
                        f"{rel}:{name}",
                        f"line {node.lineno}: numpy randomness outside repro; use "
                        "tft_engine.repro.make_rng with derive_seed (rule 5)",
                    )
