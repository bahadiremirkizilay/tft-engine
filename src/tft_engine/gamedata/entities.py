"""Knowledge base: champions, traits, items, augments and Wisps for one patch.

Loads ``data/sets/<set>/generated/<patch>/`` (written by tools/import_cdragon.py)
and checks it: links between records, recipes, sources, which patch each
source belongs to, and agreement with the economy parameters in base.json.
Problems are returned as plain sentences; ``errors`` must be empty before the
data is used, ``warnings`` are shown to the reader.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tft_engine.gamedata.cdragon import KINDS
from tft_engine.gamedata.curated import (
    apply_curated,
    effect_refs,
    read_abilities,
    read_augment_models,
    read_item_effects,
)
from tft_engine.gamedata.loader import GameData, load_gamedata
from tft_engine.gamedata.schema import STATUSES, SchemaError
from tft_engine.gamedata.sources import (
    PatchCalendar,
    SourceRegistry,
    load_calendar,
    load_sources,
)

_DATA = Path(__file__).resolve().parents[3] / "data"


@dataclass
class KnowledgeBase:
    set_id: str
    patch: str
    records: dict[str, dict[str, dict[str, Any]]]  # kind -> id -> record
    headers: dict[str, dict[str, Any]]  # kind -> file header
    curated_notes: list[str] = field(default_factory=list)
    augment_models: dict[str, dict[str, Any]] = field(default_factory=dict)
    abilities: dict[str, dict[str, Any]] = field(default_factory=dict)  # champion id -> record
    item_effects: dict[str, dict[str, Any]] = field(default_factory=dict)  # item id -> record

    def __getattr__(self, kind: str) -> dict[str, dict[str, Any]]:
        if kind in KINDS:
            return self.records[kind]
        raise AttributeError(kind)

    def ability(self, champion_id: str) -> dict[str, Any] | None:
        """The ability record of a champion; variants (Lux forms) use their base's."""
        if champion_id in self.abilities:
            return self.abilities[champion_id]
        base = self.records["champions"].get(champion_id, {}).get("variant_of")
        return self.abilities.get(base) if base else None

    def champion_by_name(self, name: str) -> dict[str, Any]:
        hits = [
            c
            for c in self.records["champions"].values()
            if c["name"].lower() == name.lower() and not c.get("variant_of")
        ]
        if len(hits) != 1:
            raise KeyError(f"{len(hits)} champions named {name!r}")
        return hits[0]


@dataclass
class CheckReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def generated_dir(set_id: str, patch: str, root: Path | None = None) -> Path:
    return (Path(root) if root else _DATA / "sets") / set_id / "generated" / patch


def load_knowledge(
    set_id: str, patch: str, root: Path | None = None, curated: bool = True
) -> KnowledgeBase:
    """Generated records for one patch, with the curated layers applied (see curated.py)."""
    folder = generated_dir(set_id, patch, root)
    if not folder.is_dir():
        raise SchemaError(
            f"no generated data for {set_id} {patch} ({folder}); run tools/import_cdragon.py"
        )
    records, headers = {}, {}
    for kind in KINDS:
        doc = json.loads((folder / f"{kind}.json").read_text(encoding="utf-8"))
        if doc.get("set") != set_id or doc.get("patch") != patch or doc.get("kind") != kind:
            raise SchemaError(f"{folder / kind}.json header does not match {set_id} {patch}")
        by_id: dict[str, dict[str, Any]] = {}
        for r in doc["records"]:
            if r["id"] in by_id:
                raise SchemaError(f"{kind}: duplicate id {r['id']}")
            by_id[r["id"]] = r
        records[kind] = by_id
        headers[kind] = {k: v for k, v in doc.items() if k != "records"}
    kb = KnowledgeBase(set_id, patch, records, headers)
    if curated:
        kb.curated_notes = apply_curated(records, folder.parent.parent / "curated", patch)
        kb.augment_models = read_augment_models(folder.parent.parent / "curated")
        kb.abilities = read_abilities(folder.parent.parent / "curated", patch)
        kb.item_effects = read_item_effects(folder.parent.parent / "curated", patch)
    return kb


def check_knowledge(
    kb: KnowledgeBase,
    sources: SourceRegistry | None = None,
    calendar: PatchCalendar | None = None,
    gamedata: GameData | None = None,
) -> CheckReport:
    rep = CheckReport()
    champs, traits, items = kb.champions, kb.traits, kb.items

    # every record: set, patch, status, sources
    used_sources: set[str] = set()
    for kind, by_id in kb.records.items():
        for rid, r in by_id.items():
            where = f"{kind}/{rid}"
            if r.get("set") != kb.set_id or r.get("patch") != kb.patch:
                rep.errors.append(f"{where}: filed under {r.get('set')} {r.get('patch')}")
            if r.get("status") not in STATUSES:
                rep.errors.append(f"{where}: bad status {r.get('status')!r}")
            ids = r.get("source_ids") or []
            if not ids:
                rep.errors.append(f"{where}: no source_ids")
            extra = list(r.get("stats_source_ids", [])) + list(r.get("role_source_ids", []))
            if isinstance(r.get("tier"), dict):
                extra += r["tier"].get("source_ids", [])
            for o in r.get("overrides", []):
                extra += o.get("source_ids", [])
            if kind == "augments" and rid in kb.augment_models:
                extra += kb.augment_models[rid]["source_ids"]
            used_sources.update(ids + extra)
            if sources is not None:
                for sid in ids + extra:
                    if sid not in sources:
                        rep.errors.append(f"{where}: unknown source {sid!r}")

    # stale-data guard: each source must belong to this patch
    if sources is not None and calendar is not None:
        for sid in sorted(used_sources):
            if sid in sources:
                for problem in calendar.check_assignment(sources[sid], kb.patch):
                    rep.warnings.append(problem)
        for kind, header in kb.headers.items():
            mapping = header.get("patch_mapping") or {}
            if mapping.get("status") != "verified":
                rep.warnings.append(
                    f"{kind}: game-file version to patch mapping is {mapping.get('status')} "
                    f"({mapping.get('evidence', 'no evidence')})"
                )
                break

    # augment models: every model names a Set augment and only its own effect values
    for aid, m in kb.augment_models.items():
        where = f"augment model {aid}"
        if aid not in kb.augments:
            rep.errors.append(f"{where}: no such augment")
            continue
        effects = kb.augments[aid].get("effects", {})
        for name in effect_refs(m):
            if effects.get(name) is None:
                rep.errors.append(f"{where}: effect value {name!r} is not in the augment record")
        if sources is not None:
            for sid in m["source_ids"]:
                if sid not in sources:
                    rep.errors.append(f"{where}: unknown source {sid!r}")

    # ability records: a real champion, known sources
    for cid, r in kb.abilities.items():
        where = f"ability {cid}"
        if cid not in champs:
            rep.errors.append(f"{where}: no such champion")
        if sources is not None:
            for sid in r["source_ids"] + [
                s for c in r.get("conflicts", []) for s in c["source_ids"]
            ]:
                if sid not in sources:
                    rep.errors.append(f"{where}: unknown source {sid!r}")

    # item effect records: a real item, known sources
    for iid, r in kb.item_effects.items():
        if iid not in items:
            rep.errors.append(f"item effects {iid}: no such item")
        if sources is not None:
            for sid in r["source_ids"]:
                if sid not in sources:
                    rep.errors.append(f"item effects {iid}: unknown source {sid!r}")

    # champions <-> traits
    for cid, c in champs.items():
        for t in c["traits"]:
            if t not in traits:
                rep.errors.append(f"champion {cid}: unknown trait {t}")
            elif cid not in traits[t].get("units", []):
                rep.errors.append(f"trait {t} does not list champion {cid}")
        base = c.get("variant_of")
        if base and base not in champs:
            rep.errors.append(f"champion {cid}: variant of unknown {base}")
    for tid, t in traits.items():
        for cid in t.get("units", []):
            if cid not in champs or tid not in champs[cid]["traits"]:
                rep.errors.append(f"trait {tid}: lists {cid}, which does not have the trait")
        if t.get("unresolved_hashes"):
            rep.warnings.append(f"trait {tid}: unresolved value names {t['unresolved_hashes']}")

    # recipes
    for iid, it in items.items():
        recipe = it.get("recipe") or []
        for comp in recipe:
            if comp not in items:
                rep.errors.append(f"item {iid}: recipe uses unknown {comp}")
            elif items[comp]["kind"] != "component":
                rep.errors.append(f"item {iid}: recipe uses {comp}, which is not a component")
            elif items[comp]["family"] != it["family"]:
                rep.warnings.append(f"item {iid}: recipe mixes item families ({comp})")
        if it["kind"] == "completed" and len(recipe) != 2:
            rep.errors.append(f"item {iid}: completed item without a two-component recipe")
    recipes: dict[tuple[str, ...], list[str]] = {}
    for iid, it in items.items():
        if it["kind"] == "completed" and it.get("recipe"):
            recipes.setdefault(tuple(sorted(it["recipe"])), []).append(iid)
    for pair, ids in recipes.items():
        if len(ids) > 1:
            rep.warnings.append(f"recipe {pair} makes several items: {sorted(ids)}")

    if gamedata is not None:
        check_parameters(gamedata, sources, rep)

    # agreement with the economy data (two independent sources)
    if gamedata is not None and "champions_per_cost" in gamedata.params:
        p = gamedata.params["champions_per_cost"]
        if p.is_known:
            counted: dict[str, int] = {}
            for c in champs.values():
                if not c.get("variant_of"):
                    counted[str(c["cost"])] = counted.get(str(c["cost"]), 0) + 1
            expected = {str(k): v for k, v in p.value.items()}
            if counted != expected:
                rep.errors.append(
                    f"champions per cost {counted} differ from base.json {expected} ({p.source})"
                )
    return rep


def superseded_values(gamedata: GameData) -> list[str]:
    """Values that a patch replaced but that still show up afterwards.

    For every change that records ``old`` values (per key of a table), the key's
    value after that change must differ from ``old`` unless a later change set
    it back on purpose. Catches a later patch file or base value that copied
    an outdated table.
    """
    last: dict[tuple[str, str], Any] = {}  # (param, key) -> last change touching it
    for ch in gamedata.changes:
        if isinstance(ch.old, dict):
            for key in ch.old:
                last[(ch.param, str(key))] = ch
    problems = []
    for (param, key), ch in sorted(last.items()):
        group, _, name = param.partition(".")
        params = gamedata.params if group == "params" else gamedata.shop_rules
        if name not in params or not isinstance(params[name].value, dict):
            continue
        now = params[name].value.get(key)
        if now == ch.old[key] and (ch.new or {}).get("value", {}).get(key) != ch.old[key]:
            problems.append(
                f"{param}[{key}] is {now!r}, the value {ch.patch} replaced; the data looks stale"
            )
    return problems


def check_parameters(gamedata: GameData, sources: SourceRegistry | None, rep: CheckReport) -> None:
    """Sources behind economy and shop parameters and patch changes."""
    if sources is not None:
        for group in (gamedata.params, gamedata.shop_rules):
            for name, p in group.items():
                ids = list(p.source_ids)
                for c in p.conflicts:
                    ids.extend(c["source_ids"])
                for sid in ids:
                    if sid not in sources:
                        rep.errors.append(f"param {name}: unknown source {sid!r}")
                if p.is_known and not p.source_ids:
                    rep.warnings.append(f"param {name}: no source_ids (only free text)")
        for ch in gamedata.changes:
            for sid in ch.source_ids:
                if sid not in sources:
                    rep.errors.append(f"{ch.patch} change {ch.param}: unknown source {sid!r}")
    for name, p in {**gamedata.params, **gamedata.shop_rules}.items():
        if p.conflicts:
            rep.warnings.append(
                f"param {name}: {len(p.conflicts)} conflicting source value(s) kept"
            )
    rep.errors.extend(superseded_values(gamedata))
    for patch in gamedata.unreviewed_patches:
        rep.warnings.append(f"patch {patch}: notes not reviewed for parameter changes")


def check_all(set_id: str, patch: str) -> tuple[KnowledgeBase, CheckReport]:
    kb = load_knowledge(set_id, patch)
    rep = check_knowledge(kb, load_sources(), load_calendar(set_id), load_gamedata(set_id, patch))
    return kb, rep


def diff_knowledge(old: KnowledgeBase, new: KnowledgeBase) -> dict[str, dict[str, Any]]:
    """Per kind: added ids, removed ids, and changed fields of common ids."""
    ignore = {"patch", "source_ids"}
    out: dict[str, dict[str, Any]] = {}
    for kind in KINDS:
        a, b = old.records[kind], new.records[kind]
        changed: dict[str, dict[str, tuple[Any, Any]]] = {}
        for rid in sorted(set(a) & set(b)):
            fields = {
                k: (a[rid].get(k), b[rid].get(k))
                for k in sorted(set(a[rid]) | set(b[rid]))
                if k not in ignore and a[rid].get(k) != b[rid].get(k)
            }
            if fields:
                changed[rid] = fields
        out[kind] = {
            "added": sorted(set(b) - set(a)),
            "removed": sorted(set(a) - set(b)),
            "changed": changed,
        }
    return out
