"""Normalize a CommunityDragon TFT export into knowledge-base records.

Pure functions, no network: the raw file is downloaded by tools/cdragon_fetch.py
and written out by tools/import_cdragon.py. Set-specific choices (which entries
are playable champions, how items are classified) come from a hand-made rules
file, ``data/sets/<set>/curated/cdragon_rules.json``, never from code.

Output is deterministic: the same input gives byte-identical records.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from tft_engine.gamedata.hashes import HashResolver, is_hashed, placeholders
from tft_engine.gamedata.schema import SchemaError

GENERATOR = "tft_engine.gamedata.cdragon/1"
KINDS = ("champions", "traits", "items", "augments", "wisps")


def _num(x: Any) -> Any:
    """Round float noise from the game files (0.4000000059604645 -> 0.4)."""
    if isinstance(x, float):
        r = round(x, 6)
        return int(r) if r.is_integer() else r
    if isinstance(x, list):
        return [_num(v) for v in x]
    if isinstance(x, dict):
        return {k: _num(v) for k, v in x.items()}
    return x


def _set_block(raw: dict[str, Any], mutator: str) -> dict[str, Any]:
    blocks = [s for s in raw.get("setData", []) if s.get("mutator") == mutator]
    if len(blocks) != 1:
        raise SchemaError(f"expected one setData block with mutator {mutator!r}, got {len(blocks)}")
    return blocks[0]


def _resolver_for(text: str, extra: list[str] = ()) -> HashResolver:
    r = HashResolver()
    r.add_candidates(placeholders(text))
    r.add_candidates(extra)
    return r


def _effects(values: dict[str, Any] | None, text: str) -> tuple[dict[str, Any], list[str]]:
    mapping, unresolved = _resolver_for(text).resolve_mapping(values or {})
    return _num(dict(sorted(mapping.items()))), unresolved


def _tags(tags: list[str] | None, known: dict[str, str]) -> list[str]:
    """Keep tags; replace hashed ones we can name (from the rules file) by the name."""
    return sorted(known.get(t, t) for t in (tags or []))


def _matches(rule: dict[str, Any], item: dict[str, Any]) -> bool:
    if "tag" in rule:
        return rule["tag"] in (item.get("tags") or [])
    if "api_contains" in rule:
        return rule["api_contains"] in item["apiName"]
    if "composition_len" in rule:
        return len(item.get("composition") or []) == rule["composition_len"]
    return True  # catch-all rule


def classify_item(item: dict[str, Any], rules: list[dict[str, Any]]) -> str:
    for rule in rules:
        if _matches(rule, item):
            return rule["kind"]
    raise SchemaError(f"no item rule matched {item['apiName']}; add a catch-all rule")


def _variant_groups(records: list[dict[str, Any]], base_of: dict[str, str]) -> None:
    """Mark entries that share a display name as variants of the shortest api name."""
    by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in records:
        by_name[r["name"]].append(r)
    for group in by_name.values():
        if len(group) < 2:
            continue
        base = min(group, key=lambda r: (len(r["id"]), r["id"]))["id"]
        for r in group:
            if r["id"] != base:
                base_of[r["id"]] = base


def normalize(
    raw: dict[str, Any], rules: dict[str, Any], set_id: str, patch: str, source_id: str
) -> dict[str, list[dict[str, Any]]]:
    block = _set_block(raw, rules["mutator"])
    all_items = {i["apiName"]: i for i in raw.get("items", [])}
    common = {"set": set_id, "patch": patch, "status": "community_extracted"}
    src = [source_id]

    # --- traits (needed first: champions list trait display names) ---------
    traits: list[dict[str, Any]] = []
    name_to_trait: dict[str, str] = {}
    for t in block.get("traits", []):
        if t["name"] in name_to_trait:
            raise SchemaError(f"two traits share the display name {t['name']!r}")
        name_to_trait[t["name"]] = t["apiName"]
        breakpoints, unresolved = [], set()
        for e in t.get("effects", []):
            values, unres = _effects(e.get("variables"), t.get("desc", ""))
            unresolved.update(unres)
            breakpoints.append(
                {
                    "min_units": e.get("minUnits"),
                    "max_units": None if e.get("maxUnits") == 25000 else e.get("maxUnits"),
                    "style": e.get("style"),
                    "values": values,
                }
            )
        traits.append(
            {
                "id": t["apiName"],
                "name": t["name"],
                "text": t.get("desc", ""),
                "breakpoints": breakpoints,
                "unresolved_hashes": sorted(unresolved),
                **common,
                "source_ids": src,
            }
        )

    # --- champions -----------------------------------------------------------
    crules = rules["champions"]
    variant_base = {}
    for g in crules.get("variant_groups", []):
        for c in block.get("champions", []):
            trait_ids = [name_to_trait.get(n) for n in c.get("traits", [])]
            if g["trait"] in trait_ids and c["apiName"] != g["base"]:
                variant_base[c["apiName"]] = g["base"]
    champions = []
    for c in block.get("champions", []):
        if not c["apiName"].startswith(tuple(crules["api_prefixes"])):
            continue
        if crules.get("require_traits") and not c.get("traits"):
            continue
        trait_ids = []
        for n in c.get("traits", []):
            if n not in name_to_trait:
                raise SchemaError(f"{c['apiName']}: unknown trait name {n!r}")
            trait_ids.append(name_to_trait[n])
        ability = c.get("ability") or {}
        variables = {v["name"]: _num(v["value"]) for v in ability.get("variables") or []}
        champions.append(
            {
                "id": c["apiName"],
                "name": c["name"],
                "cost": c["cost"],
                "traits": trait_ids,
                "role": c.get("role"),
                "stats": _num(dict(sorted((c.get("stats") or {}).items()))),
                "ability": {
                    "name": ability.get("name"),
                    "text": ability.get("desc", ""),
                    "variables": dict(sorted(variables.items())),
                    "values_status": "present" if variables else "missing",
                },
                "variant_of": variant_base.get(c["apiName"]),
                **common,
                "source_ids": src,
            }
        )
    trait_units: dict[str, list[str]] = defaultdict(list)
    for c in champions:
        for t in c["traits"]:
            trait_units[t].append(c["id"])
    for t in traits:
        t["units"] = sorted(trait_units.get(t["id"], []))

    # --- items and wisps -------------------------------------------------------
    known_tags = {r["tag"]: r["tag_name"] for r in rules.get("item_kinds", []) if r.get("tag_name")}
    items, wisps = [], []
    for api in block.get("items", []):
        it = all_items.get(api)
        if it is None:
            raise SchemaError(f"set lists item {api!r} that is not in the export")
        kind = classify_item(it, rules["item_kinds"])
        effects, unresolved = _effects(it.get("effects"), it.get("desc") or "")
        rec = {
            "id": api,
            "name": it.get("name") or "",
            "kind": kind,
            "text": it.get("desc") or "",
            "effects": effects,
            "unresolved_hashes": unresolved,
            "tags": _tags(it.get("tags"), known_tags),
            "unique": bool(it.get("unique")),
            **common,
            "source_ids": src,
        }
        if kind == "wisp":
            wisps.append(rec)
        else:
            rec["recipe"] = list(it.get("composition") or [])
            rec["family"] = api.split("_")[0]
            rec["associated_traits"] = sorted(it.get("associatedTraits") or [])
            rec["incompatible_traits"] = sorted(it.get("incompatibleTraits") or [])
            items.append(rec)

    # --- augments ----------------------------------------------------------------
    augments = []
    for api in block.get("augments", []):
        a = all_items.get(api)
        if a is None:
            raise SchemaError(f"set lists augment {api!r} that is not in the export")
        effects, unresolved = _effects(a.get("effects"), a.get("desc") or "")
        augments.append(
            {
                "id": api,
                "name": a.get("name") or "",
                "text": a.get("desc") or "",
                "effects": effects,
                "unresolved_hashes": unresolved,
                "tags": _tags(a.get("tags"), known_tags),
                "unique": bool(a.get("unique")),
                "associated_traits": sorted(a.get("associatedTraits") or []),
                "incompatible_traits": sorted(a.get("incompatibleTraits") or []),
                "tier": {"value": None, "status": "unknown", "note": "tier tag is hashed"},
                **common,
                "source_ids": src,
            }
        )

    for group in (wisps, augments):
        base_of: dict[str, str] = {}
        _variant_groups(group, base_of)
        for r in group:
            r["variant_of"] = base_of.get(r["id"])

    out = {
        "champions": champions,
        "traits": traits,
        "items": items,
        "augments": augments,
        "wisps": wisps,
    }
    return {k: sorted(v, key=lambda r: r["id"]) for k, v in out.items()}


def summary(records: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """Counts used in reports and tests."""
    champs = [c for c in records["champions"] if not c.get("variant_of")]
    return {
        "champions_per_cost": dict(sorted(Counter(str(c["cost"]) for c in champs).items())),
        "champion_forms": sum(1 for c in records["champions"] if c.get("variant_of")),
        "champions_missing_ability_values": sum(
            1 for c in records["champions"] if c["ability"]["values_status"] == "missing"
        ),
        "traits": len(records["traits"]),
        "trait_unresolved_hashes": sum(len(t["unresolved_hashes"]) for t in records["traits"]),
        "items_by_kind": dict(sorted(Counter(i["kind"] for i in records["items"]).items())),
        "augments": len(records["augments"]),
        "augment_names": len({a["name"] for a in records["augments"]}),
        "wisps": len(records["wisps"]),
        "wisp_names": len({w["name"] for w in records["wisps"]}),
        "hashed_tags_left": sum(
            1
            for kind in ("items", "augments", "wisps")
            for r in records[kind]
            for t in r["tags"]
            if is_hashed(t)
        ),
    }
