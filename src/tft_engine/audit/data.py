"""Knowledge base checks for every patch, not only the one in use."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from tft_engine.audit.core import REPO_ROOT, AuditConfig, Finding
from tft_engine.gamedata.entities import CheckReport, KnowledgeBase, check_all
from tft_engine.gamedata.loader import load_gamedata
from tft_engine.gamedata.sources import load_sources
from tft_engine.rules.board_stats import check_trait_models, load_trait_models
from tft_engine.rules.comps import check_comps, load_comps


def check_patch(set_id: str, patch: str) -> tuple[KnowledgeBase, CheckReport]:
    """Every data check for one patch: records, sources, comps and trait models.

    ``check_all`` lives in gamedata and cannot see the rules layer, so the comp and trait
    model checks are added here; the CLI and the audit both call this.
    """
    kb, rep = check_all(set_id, patch)
    rep.errors += check_comps(kb, load_comps(set_id, patch), load_sources())
    rep.errors += check_trait_models(kb, load_trait_models(set_id))
    return kb, rep


def patches_with_knowledge(root: Path = REPO_ROOT) -> Iterator[tuple[str, str]]:
    for set_dir in sorted((root / "data" / "sets").iterdir()):
        gen = set_dir / "generated"
        if gen.is_dir():
            for patch_dir in sorted(p for p in gen.iterdir() if p.is_dir()):
                yield set_dir.name, patch_dir.name


def check(root: Path, config: AuditConfig) -> Iterator[Finding]:
    if root != REPO_ROOT:  # the loaders read the repo's own data folder
        return
    sets = root / "data" / "sets"
    for set_dir in sorted(p for p in sets.iterdir() if p.is_dir()):
        for patch_file in sorted((set_dir / "patches").glob("*.json")):
            try:
                load_gamedata(set_dir.name, patch_file.stem)
            except Exception as e:  # any load error is a finding, not a crash
                yield Finding("data", f"{set_dir.name}@{patch_file.stem}", f"load failed: {e}")
    for set_id, patch in patches_with_knowledge(root):
        key = f"{set_id}@{patch}"
        try:
            _, rep = check_patch(set_id, patch)
        except Exception as e:
            yield Finding("data", key, f"load failed: {e}")
            continue
        for err in rep.errors:
            yield Finding("data", key, err)
