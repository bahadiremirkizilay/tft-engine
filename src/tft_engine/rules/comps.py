"""Comp templates and meta statistics: loading and reference checks (B5).

Two kinds of files, kept apart on purpose (plan rule 10):

    curated/comps/<patch>.json          comp templates: units, carries, style, plan

A template is the best board reachable at its level. ``star`` is the target star
level; ``star_optional`` marks a 3-star that is a bonus (in reroll comps the main
carry's and tank's 3 stars matter most). ``utility_items`` are items a unit holds
for the team (Shred, Burn) so carries and tanks keep their own.
    curated/meta/<patch>/<site>.json    statistics from one site: comps, unit builds

A template says what a comp is; a meta file says how a site measured it, with
the site, rank filter, patch, window and the definition of every number.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tft_engine.gamedata.schema import STATUSES, SchemaError

STYLES = ("reroll_5", "reroll_6", "reroll_7", "fast8", "fast9", "standard")
UNIT_ROLES = ("carry", "tank", "core", "flex")
_META_FIELDS = ("source_id", "site", "patch", "rank_filter", "collected_at", "definition")


@dataclass
class CompSet:
    templates: dict[str, dict[str, Any]] = field(default_factory=dict)
    meta: list[dict[str, Any]] = field(default_factory=list)  # one entry per site file

    def comp_stats(self, comp_id: str) -> list[dict[str, Any]]:
        """Every site's numbers for a comp, each with its site context."""
        out = []
        for m in self.meta:
            for row in m.get("comps", []):
                if row["comp"] == comp_id:
                    out.append({**row, **{k: m.get(k) for k in _META_FIELDS}})
        return out

    def tiers(self, comp_id: str) -> list[dict[str, Any]]:
        """Editorial tier labels (guides), each with its site context."""
        out = []
        for m in self.meta:
            for row in m.get("tiers", []):
                if row["comp"] == comp_id:
                    out.append({**row, **{k: m.get(k) for k in _META_FIELDS}})
        return out

    def unit_builds(self, unit_id: str) -> list[dict[str, Any]]:
        out = []
        for m in self.meta:
            for row in m.get("unit_builds", []):
                if row["unit"] == unit_id:
                    out.append({**row, **{k: m.get(k) for k in _META_FIELDS}})
        return out


def _curated(set_id: str, root: Path | None) -> Path:
    base = Path(root) if root else Path(__file__).resolve().parents[3] / "data" / "sets"
    return base / set_id / "curated"


def load_comps(set_id: str, patch: str, root: Path | None = None) -> CompSet:
    folder = _curated(set_id, root)
    out = CompSet()
    path = folder / "comps" / f"{patch}.json"
    if path.exists():
        doc = json.loads(path.read_text(encoding="utf-8"))
        for r in doc["records"]:
            where = f"comps/{patch} {r.get('id')}"
            if r.get("id") in out.templates:
                raise SchemaError(f"{where}: duplicate id")
            if r.get("style") not in STYLES:
                raise SchemaError(f"{where}: style must be one of {STYLES}")
            if not r.get("source_ids"):
                raise SchemaError(f"{where}: needs source_ids")
            if r.get("status") not in STATUSES:
                raise SchemaError(f"{where}: bad status {r.get('status')!r}")
            for u in r.get("units", []):
                if u.get("role") not in UNIT_ROLES:
                    raise SchemaError(f"{where}: unit role must be one of {UNIT_ROLES}")
                if u.get("star", 1) not in (1, 2, 3):
                    raise SchemaError(f"{where}: star must be 1, 2 or 3")
            out.templates[r["id"]] = r
    meta_dir = folder / "meta" / patch
    if meta_dir.is_dir():
        for p in sorted(meta_dir.glob("*.json")):
            doc = json.loads(p.read_text(encoding="utf-8"))
            missing = [k for k in _META_FIELDS if not doc.get(k)]
            if missing:
                raise SchemaError(f"meta/{patch}/{p.name}: missing {missing}")
            out.meta.append(doc)
    return out


def check_comps(kb, comps: CompSet, sources=None) -> list[str]:
    """Reference errors: every unit, item, comp and source must exist."""
    errors = []
    for cid, r in comps.templates.items():
        ids = [u["id"] for u in r.get("units", [])]
        if len(set(ids)) != len(ids):
            errors.append(f"comp {cid}: a unit appears twice")
        others = list(r.get("early_units", [])) + [f["id"] for f in r.get("flex_units", [])]
        for uid in ids + others:
            if uid not in kb.champions:
                errors.append(f"comp {cid}: unknown champion {uid}")
        for util in r.get("utility_items", []):
            if util["unit"] not in ids:
                errors.append(f"comp {cid}: utility_items for {util['unit']}, not in the comp")
            errors += [f"comp {cid}: unknown item {i}" for i in util["items"] if i not in kb.items]
        for carry in r.get("carry_items", []):
            if carry["unit"] not in ids:
                errors.append(f"comp {cid}: carry_items for {carry['unit']}, not in the comp")
            for build in carry["builds"]:
                errors += [f"comp {cid}: unknown item {i}" for i in build if i not in kb.items]
        for p in r.get("pivots", []):
            if p not in comps.templates:
                errors.append(f"comp {cid}: pivot to unknown comp {p}")
        if sources is not None:
            errors += [
                f"comp {cid}: unknown source {s}" for s in r["source_ids"] if s not in sources
            ]
    for m in comps.meta:
        where = f"meta {m['site']} {m['patch']}"
        if sources is not None and m["source_id"] not in sources:
            errors.append(f"{where}: unknown source {m['source_id']}")
        for row in m.get("comps", []) + m.get("tiers", []):
            if row["comp"] not in comps.templates:
                errors.append(f"{where}: stats for unknown comp {row['comp']}")
        for row in m.get("unit_builds", []):
            if row["unit"] not in kb.champions:
                errors.append(f"{where}: build for unknown champion {row['unit']}")
            errors += [f"{where}: unknown item {i}" for i in row["items"] if i not in kb.items]
    return errors
