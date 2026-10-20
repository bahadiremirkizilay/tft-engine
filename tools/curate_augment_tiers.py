"""Write curated/augment_tiers/<patch>.json from a hand transcription.

Tier lists read from tactics.tools/info/augments on 2026-10-20 (69 silver,
112 gold, 68 prismatic). The page's numbers are pre-18.4 (e.g. Level Up! shows
6 instant XP, which 18.4 raised to 10), so tier moves from later official notes
are applied on top (TIER_CHANGES). Augment texts and numbers come from the game
files, not from this page. Names are matched to the generated augments by
display name; a "(...)" suffix on the page only tells variants apart.

No network access: this is a manual transcription kept as code.

Usage (PowerShell):
    python tools/curate_augment_tiers.py set18 18.4
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

PAGE = "tactics-tools-augments-2026-10-20"

SILVER = """Augmented Power; Backup Bows; Band of Thieves; Boxing Lessons; Branching Out; Branching Out+;
Called Shot; Capital Gains I; Caretaker's Ally; Carve a Path; Celestial Blessing I; Champ Delivery;
Champ Delivery+; Champ Delivery++; Cognitive Tax; Cognitive Tax+; Component Buffet; Corrosion;
Crafted Crafting; Dummify; Electrocharge I; Expedition; Extra Buckles; Feeling Lucky; Find Your Center;
Flame On; Flowing Tears; Focused Fire; Future Focused; Glass Cannon I; Good For Something I;
Group Hug I; Healing Orbs I; Iron Assets; Item Grab Bag I; Kick Start; Kingslayer; Late Game Specialist;
Latent Forge; Loaded Dice; Makeshift Armor I; Missed Connections; One, Two, Five!; Ones Two Three;
Pandora's Bench; Pandora's Items I; Partial Ascension; Patience Is A Virtue; Quick Streaks; Recombobulator;
Residual Magic; Residual Magic +; Residual Magic ++; Rolling For Days; Silver Destiny; Silver Destiny+;
Silver Destiny++; Silver Spoon; Slice of Life; Slightly Magic Roll; Small Grab Bag; Stand United;
Team Building; The Tower; Twin Guardians; Verticality I; Wisp Rebate; Wisp Rebate+; Young and Wild and Free"""

GOLD = """Advanced Loan; Advanced Loan+; Arcane Viktor-y; Ascension; Backline Blueprint;
Beast Within (Nidalee); Beast Within (Sivir); Beast Within+ (Nidalee); Beast Within+ (Sivir); Big Grab Bag;
Birthday Reunion; Blossom's Call; Bodyguard Training; Bonus Gift; Bonus Gift+; Booster Pack; Booster Pack+;
Booster Pack++; Bronze For Life I; Capital Gains II; Caretaker's Favor; Celestial Blessing II;
Challenger's Grace; Chosen of the Sun; Clear Mind; Clockwork Accelerator; Cluttered Mind; Cognitive Overload;
Consuming Flora; Cooking Pot; Coven Acolyte; Cry Me A River; Cybernetic Implants; Cybernetic Uplink;
Dark Ritual; Duo Queue; Early Learnings; Electrocharge II; Embiggen; Epic Rolldown; Epoch; Epoch+;
Exclusive Customization; Explosive Growth; Explosive Growth+; FOURcing; Frontline Foundation; Gain 21 Gold;
Gilded Steel; Glass Cannon II; Gold Destiny; Gold Destiny+; Group Hug II; Hard Bargain; Healing Orbs II;
Heart of Steel; Heroic Grab Bag; Heroic Grab Bag+; Heroic Grab Bag++; Hustler; Infinity Protection;
Investment Strategy I; It's Me, Baby; Item Extraction; Jeweled Lotus I; Know Your Enemy; Late Game Scaling;
Legion Of Threes; Magic Roll; Makeshift Armor II; Malicious Monetization; Max Build; Money Hungry;
Money Hungry+; NO SCOUT NO PIVOT; Nature's Shelter; Omega Riftbeast; Pandora's Items II; Patient Study;
Pilfer; Plot Armor; Portable Forge; Promised Protection; Replication; Salvage Bin; Salvage Bin+;
Seraphim's Staff; Slammin'; Slammin'+; Small Furry Friend; Solo Leveling; Solo Plate; Speedy Double Kill;
Spirit Of Redemption; Spreading Roots; Spreading Roots+; Staffsmith; Sun and Moon; Sun and Moon+;
Swordsmith; The Golden Dragon; Time Skip; Tons of Stats!; Trade Sector; Trade Sector+; U.R.F; Unrivaled;
Verticality II; Warpath; Weight The Worth; Worth the Wait; Woven Magic"""

PRISMATIC = """Band of Thieves II; Band of Thieves II+; Band of Thieves II++; Baron's Lair; Belt Overflow;
Birthday Present; Bronze For Life II; Build A Bud; Buried Treasures III; Call To Chaos; Celestial Blessing III;
Comeback Story; Commerce Core; Component Quest; Coronation; Deadlier Blades; Deadlier Caps; Flexible;
Forged In Strength; Giant and Mighty; Going Long; Golden Gamble; Golden Gamble+; Golden Gamble++;
Hard Commit; Hedge Fund; Hold the Line; Invested+; Invested++; Investment Strategy II; Jeweled Lotus II;
Level Up!; Living Forge; Lucky Gloves; Lucky Gloves+; Luxury Subscription; Master of All Origins; Min-Max;
Money Monsoon; Nesting Anvils; Nesting Anvils+; Nesting Dolls (first); Nesting Dolls (second);
One Buff Two Buff; Pandora's Items III; Prismatic Destiny; Prismatic Destiny+; Prismatic Ticket;
Radiant Rascal; Radiant Relics; Retribution; Shimmerscale Essence; Shopping Spree; Soul Awakening;
Sweet Treats; Sword Overflow; TONS of Stats!; Tactician's Kitchen; The Golden Egg; The Trait Tree;
The Trait Tree+; Trait Ladder; Upward Mobility; Urf's Grab Bag; Verticality III; Wand Overflow;
We Stick Together; Worth the Wait II"""

# Tier moves in official notes after the page's state: name -> (tier, source id, note)
TIER_CHANGES = {
    "Chosen of the Sun": ("silver", "riot-notes-18.4", "18.4: tier Gold => Silver"),
}


# Page name -> game-file name, where the page spells it differently.
ALIASES = {"Bonus Gift": "Bonus Gifts", "Bonus Gift+": "Bonus Gifts+"}


def names(block: str) -> list[str]:
    return [n.strip() for n in block.replace("\n", " ").split(";") if n.strip()]


def norm(name: str) -> str:
    """Drop a trailing "(...)" and spaces; keep case ("Tons of Stats!" != "TONS of Stats!")."""
    name = re.sub(r"\s*\([^)]*\)\s*$", "", name)  # "(Nidalee)" only tells variants apart
    return re.sub(r"\s+", "", name)


def build(set_id: str, patch: str) -> dict:
    kb = load_knowledge(set_id, patch, curated=False)
    exact: dict[str, str] = {}
    loose: dict[str, set[str]] = {}
    for a in kb.augments.values():
        exact.setdefault(norm(a["name"]), a["name"])
        loose.setdefault(norm(a["name"]).lower(), set()).add(a["name"])
    tiers: dict[str, tuple[str, list[str], str]] = {}
    missing = []
    for tier, block in (("silver", SILVER), ("gold", GOLD), ("prismatic", PRISMATIC)):
        for n in names(block):
            n = ALIASES.get(n, n)
            real = exact.get(norm(n))
            if real is None and len(loose.get(norm(n).lower(), ())) == 1:
                real = next(iter(loose[norm(n).lower()]))
            if real is None:
                missing.append(n)
                continue
            if real in tiers and tiers[real][0] != tier:
                raise SystemExit(f"{real} listed under two tiers")
            tiers[real] = (tier, [PAGE], "")
    for real, (tier, src, note) in TIER_CHANGES.items():
        if real not in tiers:
            raise SystemExit(f"tier change for unknown augment {real}")
        tiers[real] = (tier, [PAGE, src], note)
    records = []
    for real in sorted(tiers):
        tier, src, note = tiers[real]
        rec = {"name": real, "tier": tier, "status": "third_party_unverified", "source_ids": src}
        if note:
            rec["note"] = note
        records.append(rec)
    return {
        "set": set_id,
        "patch": patch,
        "kind": "augment_tiers",
        "note": (
            "Tiers from tactics.tools/info/augments (read 2026-10-20; page state is pre-18.4) "
            "plus tier moves from later official notes. Matched by display name, so every "
            "game-file record with that name gets the tier; names on the page that were not found "
            "in the game files are listed under unmatched."
        ),
        "unmatched": missing,
        "records": records,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("set_id")
    p.add_argument("patch")
    args = p.parse_args(argv)
    doc = build(args.set_id, args.patch)
    out = ROOT / "data" / "sets" / args.set_id / "curated" / "augment_tiers" / f"{args.patch}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {len(doc['records'])} augment names to {out}; unmatched: {doc['unmatched']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
