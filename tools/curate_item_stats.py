"""Write curated/item_stats/<patch>.json from a hand transcription.

The transcription below was read from tactics.tools/info/items on 2026-10-20
(the page says "Set 18" without a patch; its numbers match 18.2: Bloodthirster
has the 18.2 values, while the 18.3 and 18.4 item changes are missing). The
items those later patches changed are entered with the official values and
the patch notes as an extra source. Names are matched to the Set 18 (DA_)
items of the generated data; anything that does not match stops the script.

This is a manual transcription kept as code so it can be re-run and reviewed,
not a scraper: it never touches the network.

Usage (PowerShell):
    python tools/curate_item_stats.py set18 18.4
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tft_engine.gamedata.entities import load_knowledge  # noqa: E402

PAGE = "tactics-tools-items-2026-10-20"

# name | stats | effect | extra sources (comma separated) | note
CRAFTABLE = """
Adaptive Helm | 20 MR, 3 Mana Regen | +15% Mana gain. Tanks and Fighters gain 30 Armor and MR; other roles gain 10% AD and AP. | |
Archangel's Staff | 30 AP, 1 Mana Regen | Combat start and every 5s in combat: +20 AP. | |
Bloodthirster | 18% AD, 18 AP, 20 MR, 20% Omnivamp | Once per combat at 50% Health: shield of 30% max Health for up to 5s. | |
Blue Buff | 15% AD, 15 AP, 5 Mana Regen | +10% additional AD and AP from all sources. | |
Bramble Vest | 50 Armor | +6% max Health; 5% less damage from attacks; when struck, 100 magic damage to adjacent enemies (2s cooldown). | |
Crownguard | 100 HP, 20 AP, 20 Armor | Combat start: shield of 25% max Health for 8s; when it expires, +20 AP. | riot-notes-18.4 | 18.4: AP on shield expire 25 => 20
Deathblade | 55% AD, 10% Damage Amp | Stacking bonus with more copies (page text was a placeholder). | |
Dragon's Claw | 60 MR | +6% max Health; every 2s heal 2.5% max Health. | |
Edge of Night | 10% AD, 10 AP, 20 Armor, 15% AS | At 40% Health: briefly untargetable, shed negative effects, heal 15% missing Health. | |
Evenshroud | 20 MR, 250 HP | 30% Sunder to enemies within 2 hexes; first 15s of combat: +15 Armor and MR. | |
Gargoyle Stoneplate | 100 HP, 25 Armor, 25 MR | +10 Armor and MR for each enemy targeting the holder. | |
Giant Slayer | 15% AD, 15 AP, 15% AS, 15% Damage Amp | +15% additional Damage Amp against Tanks. | |
Guinsoo's Rageblade | 10 AP, 10% AS | +7% stacking Attack Speed every second. | |
Hand of Justice | 20% Crit, 1 Mana Regen | 18% AD and AP and 15% Omnivamp; AD/AP doubled above 50% Health, Omnivamp doubled below 50% Health. | |
Hextech Gunblade | 20% AD, 20 AP, 15% Omnivamp, 1 Mana Regen | Heals the lowest-Health ally for 20% of damage dealt. | |
Infinity Edge | 35% AD, 35% Crit | Precision: abilities can crit; extra Precision adds 10% Crit Damage. | |
Ionic Spark | 250 HP, 15 AP, 35 MR | 30% Shred to enemies within 2 hexes; enemy casts take magic damage equal to 150% of the Mana spent. | |
Jeweled Gauntlet | 35 AP, 35% Crit | Precision: abilities can crit; extra Precision adds 10% Crit Damage. | |
Kraken's Fury | 10% AD, 20 MR, 10% AS | Attacks grant 3.5% stacking AD (up to 15 attacks), then +15% Attack Speed. | |
Last Whisper | 15% AD, 20% AS, 20% Crit | Attacks and abilities Sunder 30% for 3s (does not stack). | |
Morellonomicon | 150 HP, 20 AP, 1 Mana Regen | Attacks and abilities apply 1% Burn and 33% Wound for 10s. | |
Nashor's Tooth | 150 HP, 15 AP, 10% AS, 20% Crit | Attacks grant 2 bonus Mana (2 more on crit). | |
Protector's Vow | 25 Armor, 25 MR, 1 Mana Regen | Combat start: 20 Mana. At 40% Health: 15 Mana and a shield of 20% max Health. | |
Quicksilver | 20 MR, 15% AS, 20% Crit | Combat start: Unstoppable for 18s; +3% stacking Attack Speed per second. | |
Rabadon's Deathcap | 55 AP, 15% Damage Amp | Stacking bonus with more copies (page text was a placeholder). | |
Red Buff | 45% AS, 3% Damage Amp | Attacks and abilities apply 1% Burn and 33% Wound for 5s. | |
Spear of Shojin | 15% AD, 15 AP, 1 Mana Regen | Attacks grant 5 bonus Mana. | |
Spirit Visage | 300 HP, 10% Durability, 2 Mana Regen | Regenerate 2% of missing Health per second. | riot-notes-18.4 | 18.4: Durability 8% => 10% (the page called it damage reduction)
Steadfast Heart | 250 HP, 20 Armor, 20% Crit | 5% Durability (15% above 50% Health). | |
Sterak's Gage | 300 HP, 45% AD | At 60% Health: shield of 40% max Health, decaying over 4s. | |
Striker's Flail | 150 HP, 10% AS, 20% Crit, 10% Damage Amp | Crits grant 5% Damage Amp for 5s, up to 4 stacks. | |
Sunfire Cape | 150 HP, 20 Armor | +8% max Health; every 2s, 1% Burn and 33% Wound to a nearby enemy for 10s. | |
Thief's Gloves | 150 HP, 20% Crit | Each round: equip 2 random items (uses all 3 slots). | |
Titan's Resolve | 20 Armor, 10% AS | +2% AD and AP per attack or damage taken (up to 25 stacks); at full: 10% Damage Amp and Unstoppable. | |
Void Staff | 35 AP, 15% AS, 1 Mana Regen | Attacks and abilities Shred 30% for 5s (does not stack). | |
Warmog's Armor | 500 HP | +18% max Health. | |
"""

RADIANT = """
Radiant Adaptive Helm | 40 MR, 7 Mana Regen | +30% Mana gain. Tanks and Fighters gain 80 Armor and MR; others gain 40% AD and AP. | |
Radiant Archangel's Staff | 60 AP, 2 Mana Regen | Combat start and every 5s: +40 AP. | |
Radiant Bloodthirster | 40% AD, 40 AP, 40 MR, 40% Omnivamp | Once per combat at 50% Health: shield of 60% max Health for up to 5s. | |
Radiant Blue Buff | 30% AD, 30 AP, 10 Mana Regen | +20% additional AD and AP. | |
Radiant Bramble Vest | 100 Armor | +12% max Health; 10% less damage from attacks; when struck, 200 magic damage to adjacent enemies (2s cooldown). | |
Radiant Crownguard | 200 HP, 40 AP, 40 Armor | Combat start: shield of 50% max Health for 8s; when it expires, +50 AP. | | 18.4 changed base Crownguard's AP on expire; the notes list no Radiant change
Radiant Deathblade | 100% AD, 20% Damage Amp | Stacking bonus (page text was a placeholder). | |
Radiant Dragon's Claw | 120 MR | +28% max Health; every 2s heal 5% max Health. | |
Radiant Edge of Night | 30% AD, 30 AP, 40 Armor, 30% AS | At 40% Health: untargetable, shed negative effects, heal all missing Health. | |
Radiant Evenshroud | 500 HP, 40 MR | 30% Sunder within 3 hexes; first 20s: +50 Armor and MR. | |
Radiant Gargoyle Stoneplate | 400 HP, 50 Armor, 50 MR | +20 Armor and MR for each enemy targeting the holder. | |
Radiant Giant Slayer | 30% AD, 30 AP, 30% AS, 30% Damage Amp | +30% additional Damage Amp against Tanks. | |
Radiant Guinsoo's Rageblade | 20 AP, 25% AS | +16% stacking Attack Speed per second. | |
Radiant Hand of Justice | 40% Crit, 2 Mana Regen | 35% AD and AP and 30% Omnivamp; same doubling rule as the base item. | |
Radiant Hextech Gunblade | 40% AD, 40 AP, 30% Omnivamp, 2 Mana Regen | Heals the lowest-Health ally for 40% of damage dealt. | |
Radiant Infinity Edge | 75% AD, 75% Crit | Precision. | |
Radiant Ionic Spark | 500 HP, 30 AP, 70 MR | 30% Shred within 2 hexes; enemy casts take 300% of Mana spent as magic damage. | |
Radiant Jeweled Gauntlet | 75 AP, 75% Crit | Precision. | |
Radiant Kraken's Fury | 20% AD, 40 MR, 20% AS | Attacks grant 7% stacking AD (15 attacks), then +30% Attack Speed. | |
Radiant Last Whisper | 45% AD, 40% AS, 40% Crit | 30% Sunder for the rest of combat (does not stack). | |
Radiant Morellonomicon | 300 HP, 35 AP, 2 Mana Regen | 2% Burn and 33% Wound for 10s. | |
Radiant Nashor's Tooth | 300 HP, 30 AP, 20% AS, 40% Crit | Attacks grant 4 bonus Mana (2 more on crit). | |
Radiant Protector's Vow | 50 Armor, 50 MR, 2 Mana Regen | Combat start: 40 Mana. At 40% Health: 30 Mana and a shield of 50% max Health. | |
Radiant Quicksilver | 40 MR, 40% AS, 40% Crit | Unstoppable for 45s; +6% stacking Attack Speed per second. | |
Radiant Rabadon's Deathcap | 100 AP, 30% Damage Amp | Stacking bonus (page text was a placeholder). | |
Radiant Red Buff | 80% AS, 6% Damage Amp | 2% Burn and 33% Wound for 5s. | |
Radiant Spear of Shojin | 30% AD, 30 AP, 2 Mana Regen | Attacks grant 10 bonus Mana. | |
Radiant Spirit Visage | 700 HP, 18% Durability, 4 Mana Regen | Regenerate 4% of missing Health per second. | riot-notes-18.4 | 18.4: Radiant Durability 15% => 18% (the page called it damage reduction)
Radiant Steadfast Heart | 500 HP, 40 Armor, 40% Crit | 10% Durability (30% above 50% Health). | |
Radiant Sterak's Gage | 600 HP, 90% AD | At 60% Health: shield of 80% max Health, decaying over 6s. | |
Radiant Striker's Flail | 300 HP, 20% AS, 40% Crit, 20% Damage Amp | Crits grant 10% Damage Amp for 5s, up to 4 stacks. | |
Radiant Sunfire Cape | 300 HP, 40 Armor | +16% max Health; every 2s, 2% Burn and 33% Wound to a nearby enemy. | |
Radiant Thief's Gloves | 150 HP, 20% Crit | Each round: equip 2 random Radiant items. | |
Radiant Titan's Resolve | 40 Armor, 20% AS | +4% AD and AP per attack or damage taken (25 stacks); at full: 20% Damage Amp and Unstoppable. | |
Radiant Void Staff | 75 AP, 30% AS, 2 Mana Regen | 30% Shred for the rest of combat (does not stack). | |
Radiant Warmog's Armor | 1200 HP | +36% max Health. | |
"""

ARTIFACT = """
Aegis of Dawn | 400 HP, 50 Armor | Every 2.5s: steal 3 Armor from adjacent enemies and heal 20% of the holder's Armor (1.25s with Aegis of Dusk). | |
Aegis of Dusk | 400 HP, 70 MR | Every 2.5s: steal 3 MR from adjacent enemies and deal 18% of the holder's MR as magic damage (1.25s with Aegis of Dawn). | |
Blighting Jewel | 30 AP, 2 Mana Regen | Magic damage reduces the target's MR by 3; at 0 MR, gain 4 Mana. | |
Dawncore | 20% AD, 20 AP, 1 Mana Regen | Reduces max Mana by 10, then 5% per cast (minimum 15). | |
Death's Defiance | 25% AD, 15% AS | 25% of damage received is dealt over time as non-lethal damage. Unique. Armor and Omnivamp values were not readable on the page. | |
Eternal Pact | 35 AP, 1 Mana Regen | Combat start: pact with the highest-Health ally; shields that ally every 6s for 200% of the holder's AP. The ally gains 10 Mana on Tank ability cast. | riot-notes-18.3 | 18.3: Mana on Tank ability cast 15 => 10
Fishbones | 25% AD, 25% AS | Attacks target random enemies; +2 attack range. | |
Flickerblades | 10 AP, 20% AS | Attacks grant 4% stacking Attack Speed; every 3 attacks grant 2% AD and AP. | |
Forbidden Idol | 500 HP, 2 Mana Regen | Shields convert 40% of their value to max Health. | |
Gambler's Blade | 55% AS | +1% Attack Speed per gold banked (up to 30); attacks have a 6% chance to drop gold. | |
Gold Collector | 35% AD, 20% Crit | Attacks and abilities execute enemies below 12% Health; champion executions have a 33% chance to drop gold. Unique. | riot-notes-18.3 | 18.3: AD 40% => 35% (notes call it The Collector)
Hellfire Hatchet | 400 HP, 20% Omnivamp | Attacks deal 3% max Health as bonus physical damage; +1.5% Attack Speed per 1% missing Health. | |
Horizon Focus | 250 HP, 20 Armor, 20 MR, 2 Mana Regen | Stunning an enemy strikes it with lightning for 30% of its max Health as magic damage. | |
Hullcrusher | 60 Armor, 60 MR | Combat start with no adjacent allies: +400 Health, 10% AD, 10% AP. | |
Infinity Force | 300 HP, 30% AD, 30 AP, 30 Armor, 30 MR, 30% AS | Stats only. | |
Lich Bane | 55 AP, 10% AS | First attack after each cast deals 250/350/500/600/700/700 bonus magic damage (by stage). | |
Lightshield Crest | 55 Armor, 55 MR | Every 3s: shield the lowest-Health ally for 70% of the holder's Armor+MR for 5s; on death, shield all allies. | |
Luden's Tempest | 55% AD, 55 AP | 100% of overkill damage plus 130 hits the two nearest enemies as magic damage. | |
Manazane | 15% AD, 15 AP, 1 Mana Regen | After the first cast in combat, gain 110 Mana over 5s. | |
Mittens | 65% AS, 15% Damage Amp | Shrinks the holder: faster movement, immune to Slow, Burn and Wound. | |
Mogul's Mail | 300 HP | +1 Armor, 1 MR and 5 Health per hit taken (up to 35 stacks); at full, 1 gold every 11s. Unique. | |
Rapid Firecannon | 55% AS, 5% Damage Amp | +1 attack range, +1 more per kill. | |
Seeker's Armguard | 25 AP, 10 Armor, 10 MR, 20% Omnivamp | Takedowns grant +20 Armor, MR and AP. | |
Silvermere Dawn | 150% AD, 30 Armor, 30 MR, 30% Omnivamp | Stun immunity; attacks stun for 0.8s; Attack Speed locked at 0.5. | |
Statikk Shiv | 25 AP, 40% AS | Every 3rd attack deals 15 + 35% of the holder's AP as magic damage to up to 6 enemies. | riot-notes-18.3 | 18.3: base AP 15% => 25%
Talisman of Ascension | 450 HP, 20% AD, 20 AP | After 22s: +100% max Health, 12 Mana Regen and 120% Damage Amp for the rest of combat. | |
The Indomitable | 500 HP, 20 Armor, 20 MR | Much slower movement; +15% max Health, Unstoppable, pulls its target into melee. | |
Titanic Hydra | 300 HP, 20% AD, 20% AS | Attacks deal 2% max Health + 4% AD as bonus physical damage to the target and adjacent enemies. | |
Void Gauntlet | 300 HP, 10% Damage Reduction | Combat start: stores 30% max Health (+2.5% per second); on death, releases it as magic damage within 4 hexes. Unique. | |
Wit's End | 300 HP, 20 Armor, 20 MR, 25% AS | Attacks deal 25/45/65/85/100 bonus magic damage (by stage); heal 25% of magic damage dealt. | |
Zhonya's Paradox | 25 AP, 25 Armor, 25 MR | Once per combat at 40% Health: invulnerable and untargetable for 3s. Unique. | |
"""

STAT_PATTERNS = [
    (r"^(\d+(?:\.\d+)?) HP$", "hp"),
    (r"^(\d+(?:\.\d+)?)% AD$", "ad_pct"),
    (r"^(\d+(?:\.\d+)?)%? AP$", "ap"),
    (r"^(\d+(?:\.\d+)?)% AS$", "as_pct"),
    (r"^(\d+(?:\.\d+)?) Armor$", "armor"),
    (r"^(\d+(?:\.\d+)?) MR$", "mr"),
    (r"^(\d+(?:\.\d+)?)% Crit$", "crit_pct"),
    (r"^(\d+(?:\.\d+)?) Mana Regen$", "mana_regen"),
    (r"^(\d+(?:\.\d+)?)% Omnivamp$", "omnivamp_pct"),
    (r"^(\d+(?:\.\d+)?)% Damage Amp$", "damage_amp_pct"),
    (r"^(\d+(?:\.\d+)?)% Damage Reduction$", "damage_reduction_pct"),
    (r"^(\d+(?:\.\d+)?)% Durability$", "durability_pct"),
]


def parse_stats(text: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for token in (t.strip() for t in text.split(",") if t.strip()):
        for pat, key in STAT_PATTERNS:
            m = re.match(pat, token)
            if m:
                v = float(m.group(1))
                out[key] = int(v) if v.is_integer() else v
                break
        else:
            raise ValueError(f"cannot read stat {token!r}")
    return out


COPY_KEYS = {
    "AD": ("ad_pct", 100),
    "AP": ("ap", 1),
    "AS": ("as_pct", 1),
    "Armor": ("armor", 1),
    "MagicResist": ("mr", 1),
    "Health": ("hp", 1),
    "CritChance": ("crit_pct", 1),
    "ManaRegen": ("mana_regen", 1),
    "StatOmnivamp": ("omnivamp_pct", 100),
}


def older_copies(raw_path: Path) -> dict[str, list[dict]]:
    """Older-set entries of the same items in the export (stats present, values may be old)."""
    if not raw_path.exists():
        return {}
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    out: dict[str, list[dict]] = {}
    for i in raw["items"]:
        if not i["apiName"].startswith("DA_") and i.get("effects") and i.get("name"):
            out.setdefault(i["name"].lower(), []).append(i)
    return out


def compare_with_copy(stats: dict, copies: list[dict]) -> dict | None:
    """Closest older copy and the stats that differ from it."""
    best = None
    for c in copies:
        diffs = []
        for k, (key, mult) in COPY_KEYS.items():
            if c["effects"].get(k) is None:
                continue
            v = round(c["effects"][k] * mult, 2)
            v = int(v) if float(v).is_integer() else v
            if stats.get(key) is None or abs(stats[key] - v) > 0.01:
                diffs.append(f"{key}: {stats.get(key)} here, {v} in {c['apiName']}")
        if best is None or len(diffs) < len(best["diffs"]):
            best = {"older_copy": c["apiName"], "diffs": diffs}
    return best


def rows(block: str):
    for line in block.strip().splitlines():
        name, stats, effect, extra, note = (p.strip() for p in line.split("|"))
        yield name, stats, effect, [s for s in extra.split(",") if s.strip()], note


def build(set_id: str, patch: str) -> dict:
    kb = load_knowledge(set_id, patch, curated=False)
    version = kb.headers["items"]["source_id"].removeprefix("cdragon-")
    copies = older_copies(ROOT / "data" / "raw" / "cdragon" / version / "en_us.json")
    by_name: dict[str, list[str]] = {}
    other: dict[str, list[str]] = {}  # same kinds, older families (used only if no DA match)
    for i in kb.items.values():
        if i["kind"] in ("completed", "radiant", "artifact"):
            target = by_name if i["family"] == "DA" else other
            target.setdefault(i["name"].lower(), []).append(i["id"])
    records, missing = [], []
    for block in (CRAFTABLE, RADIANT, ARTIFACT):
        for name, stats, effect, extra, note in rows(block):
            ids = by_name.get(name.lower(), [])
            if not ids and len(other.get(name.lower(), [])) == 1:
                ids = other[name.lower()]
                note = (note + "; " if note else "") + f"Set 18 uses the older entry {ids[0]}"
            if len(ids) != 1:
                missing.append(f"{name}: {len(ids)} matching DA items {ids}")
                continue
            rec = {
                "id": ids[0],
                "name": name,
                "stats": parse_stats(stats),
                "effect": effect,
                "status": "third_party_unverified",
                "source_ids": [PAGE] + [s.strip() for s in extra],
            }
            if note:
                rec["note"] = note
            check = compare_with_copy(rec["stats"], copies.get(name.lower(), []))
            if check is not None:
                rec["older_copy_check"] = check
            records.append(rec)
    if missing:
        raise SystemExit("unmatched names:\n  " + "\n  ".join(missing))
    return {
        "set": set_id,
        "patch": patch,
        "kind": "item_stats",
        "note": (
            "Hand transcription of tactics.tools/info/items (read 2026-10-20; numbers match 18.2). "
            "Items changed in 18.3/18.4 carry the official values and the notes as a source. "
            "Effect texts are short paraphrases, not Riot's wording. AP is stored as a number. "
            "older_copy_check compares with the older-set entry of the same item in the game-file "
            "export (values there can be outdated): equal stats support the transcription, "
            "differences need a look."
        ),
        "records": sorted(records, key=lambda r: r["id"]),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("set_id")
    p.add_argument("patch")
    args = p.parse_args(argv)
    doc = build(args.set_id, args.patch)
    out = ROOT / "data" / "sets" / args.set_id / "curated" / "item_stats" / f"{args.patch}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {len(doc['records'])} items to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
