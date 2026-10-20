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
Adaptive Helm | 20 MR, 3 Mana Regen | +15% Mana gain. Tanks and Fighters gain 30 Armor and MR; other roles gain 10% AD and AP. | METATFT | MetaTFT says 80 Armor and MR for Tanks and Fighters (kept as a conflict; 80 is the Radiant value in the older game-file copy, the base copy has 30)
Archangel's Staff | 30 AP, 1 Mana Regen | Combat start and every 5s in combat: +20 AP. | SHOTS |
Bloodthirster | 18% AD, 18 AP, 20 MR, 20% Omnivamp | Once per combat at 50% Health: shield of 30% max Health for up to 5s. | METATFT |
Blue Buff | 15% AD, 15 AP, 5 Mana Regen | +10% additional AD and AP from all sources. | SHOTS |
Bramble Vest | 50 Armor | +6% max Health; 5% less damage from attacks; when struck, 100 magic damage to adjacent enemies (2s cooldown). | METATFT |
Crownguard | 100 HP, 20 AP, 20 Armor | Combat start: shield of 25% max Health for 8s; when it expires, +20 AP. | METATFT, SHOTS, riot-notes-18.4 | 18.4: AP on shield expire 25 => 20; the screenshot still shows the pre-18.4 25% AP on expire
Deathblade | 55% AD, 10% Damage Amp | Stacking bonus with more copies (page text was a placeholder). | METATFT |
Dragon's Claw | 60 MR | +6% max Health; every 2s heal 2.5% max Health. | SHOTS |
Edge of Night | 10% AD, 10 AP, 20 Armor, 15% AS | At 40% Health: briefly untargetable, shed negative effects, heal 15% missing Health. | SHOTS |
Evenshroud | 20 MR, 250 HP | 30% Sunder to enemies within 2 hexes; first 15s of combat: +15 Armor and MR. | METATFT |
Gargoyle Stoneplate | 100 HP, 25 Armor, 25 MR | +10 Armor and MR for each enemy targeting the holder. | METATFT |
Giant Slayer | 15% AD, 15 AP, 15% AS, 15% Damage Amp | +15% additional Damage Amp against Tanks. | METATFT |
Guinsoo's Rageblade | 10 AP, 10% AS | +7% stacking Attack Speed every second. | METATFT |
Hand of Justice | 20% Crit, 1 Mana Regen | 18% AD and AP and 15% Omnivamp; AD/AP doubled above 50% Health, Omnivamp doubled below 50% Health. | METATFT |
Hextech Gunblade | 20% AD, 20 AP, 15% Omnivamp, 1 Mana Regen | Heals the lowest-Health ally for 20% of damage dealt. | METATFT |
Infinity Edge | 35% AD, 35% Crit | Precision: abilities can crit; extra Precision adds 10% Crit Damage. | SHOTS |
Ionic Spark | 250 HP, 15 AP, 35 MR | 30% Shred to enemies within 2 hexes; enemy casts take magic damage equal to 150% of the Mana spent. | SHOTS |
Jeweled Gauntlet | 35 AP, 35% Crit | Precision: abilities can crit; extra Precision adds 10% Crit Damage. | SHOTS |
Kraken's Fury | 10% AD, 20 MR, 10% AS | Attacks grant 3.5% stacking AD (up to 15 attacks), then +15% Attack Speed. | SHOTS |
Last Whisper | 15% AD, 20% AS, 20% Crit | Attacks and abilities Sunder 30% for 3s (does not stack). | SHOTS |
Morellonomicon | 150 HP, 20 AP, 1 Mana Regen | Attacks and abilities apply 1% Burn and 33% Wound for 10s. | METATFT |
Nashor's Tooth | 150 HP, 15 AP, 10% AS, 20% Crit | Attacks grant 2 bonus Mana (2 more on crit). | METATFT |
Protector's Vow | 25 Armor, 25 MR, 1 Mana Regen | Combat start: 20 Mana. At 40% Health: 15 Mana and a shield of 20% max Health. | SHOTS |
Quicksilver | 20 MR, 15% AS, 20% Crit | Combat start: Unstoppable for 18s; +3% stacking Attack Speed per second. | SHOTS |
Rabadon's Deathcap | 55 AP, 15% Damage Amp | Stacking bonus with more copies (page text was a placeholder). | METATFT |
Red Buff | 45% AS, 3% Damage Amp | Attacks and abilities apply 1% Burn and 33% Wound for 5s. | METATFT |
Spear of Shojin | 15% AD, 15 AP, 1 Mana Regen | Attacks grant 5 bonus Mana. | SHOTS |
Spirit Visage | 300 HP, 10% Durability, 2 Mana Regen | Regenerate 2% of missing Health per second. | METATFT, riot-notes-18.4 | 18.4: Durability 8% => 10% (the page called it damage reduction)
Steadfast Heart | 250 HP, 20 Armor, 20% Crit | 5% Durability (15% above 50% Health). | METATFT | MetaTFT shows a Health stat with the value '?'
Sterak's Gage | 300 HP, 45% AD | At 60% Health: shield of 40% max Health, decaying over 4s. | METATFT |
Striker's Flail | 150 HP, 10% AS, 20% Crit, 10% Damage Amp | Crits grant 5% Damage Amp for 5s, up to 4 stacks. | METATFT |
Sunfire Cape | 150 HP, 20 Armor | +8% max Health; every 2s, 1% Burn and 33% Wound to a nearby enemy for 10s. | METATFT |
Thief's Gloves | 150 HP, 20% Crit | Each round: equip 2 random items (uses all 3 slots). | SHOTS |
Titan's Resolve | 20 Armor, 10% AS | +2% AD and AP per attack or damage taken (up to 25 stacks); at full: 10% Damage Amp and Unstoppable. | SHOTS |
Void Staff | 35 AP, 15% AS, 1 Mana Regen | Attacks and abilities Shred 30% for 5s (does not stack). | SHOTS |
Warmog's Armor | 500 HP | +18% max Health. | SHOTS |
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

SHOTS = "owner-screenshots-2026-10-20"
METATFT = "metatft-items-2026-10-20"
TOKENS = {"SHOTS": SHOTS, "METATFT": METATFT}

# The owner's screenshots come from a site whose tooltips leave out some stats
# (Health on Gargoyle Stoneplate, Steadfast Heart, Sunfire Cape ...; every Damage
# Amp line; the whole stat line on Bloodthirster, Guinsoo's Rageblade ...). For all
# 19 craftable items where it differs, the older game-file copy has exactly the
# page values, so the page values stay and the screenshot values are kept here.
# Values another source gave that lost to a better source; never dropped silently.
SHOT_NOTE = (
    "owner's screenshot (stats site) shows only these stats; the older game-file copy "
    "matches the page values, so the site likely leaves stats out"
)
RADIANT_SHOT_NOTE = (
    "owner's screenshot (same stats site) shows only these stats; that site also leaves "
    "Health out of the base items, so the page values stay"
)
CONFLICTS: dict[str, list[dict]] = {
    "Gargoyle Stoneplate": [
        {"stats": {"armor": 25, "mr": 25}, "source_ids": [SHOTS], "note": SHOT_NOTE}
    ],
    "Rabadon's Deathcap": [{"stats": {"ap": 55}, "source_ids": [SHOTS], "note": SHOT_NOTE}],
    "Deathblade": [{"stats": {"ad_pct": 55}, "source_ids": [SHOTS], "note": SHOT_NOTE}],
    "Adaptive Helm": [
        {"stats": {}, "source_ids": [SHOTS], "note": SHOT_NOTE},
        {
            "effect": "Tanks and Fighters gain 80 Armor and MR",
            "source_ids": [METATFT],
            "note": "MetaTFT tooltip; the older game-file copy has FrontlineResists 30 for the base item and 80 for the Radiant one; no patch note changed it",
        },
    ],
    "Giant Slayer": [
        {"stats": {"ad_pct": 15, "ap": 15, "as_pct": 15}, "source_ids": [SHOTS], "note": SHOT_NOTE}
    ],
    "Striker's Flail": [
        {
            "stats": {"hp": 150, "as_pct": 10, "crit_pct": 20},
            "source_ids": [SHOTS],
            "note": SHOT_NOTE,
        }
    ],
    "Morellonomicon": [{"stats": {}, "source_ids": [SHOTS], "note": SHOT_NOTE}],
    "Red Buff": [{"stats": {"as_pct": 45}, "source_ids": [SHOTS], "note": SHOT_NOTE}],
    "Bloodthirster": [{"stats": {}, "source_ids": [SHOTS], "note": SHOT_NOTE}],
    "Spirit Visage": [{"stats": {}, "source_ids": [SHOTS], "note": SHOT_NOTE}],
    "Steadfast Heart": [
        {"stats": {"armor": 20, "crit_pct": 20}, "source_ids": [SHOTS], "note": SHOT_NOTE}
    ],
    "Guinsoo's Rageblade": [{"stats": {}, "source_ids": [SHOTS], "note": SHOT_NOTE}],
    "Hand of Justice": [{"stats": {}, "source_ids": [SHOTS], "note": SHOT_NOTE}],
    "Evenshroud": [{"stats": {"mr": 20}, "source_ids": [SHOTS], "note": SHOT_NOTE}],
    "Bramble Vest": [{"stats": {}, "source_ids": [SHOTS], "note": SHOT_NOTE}],
    "Hextech Gunblade": [{"stats": {}, "source_ids": [SHOTS], "note": SHOT_NOTE}],
    "Sterak's Gage": [{"stats": {}, "source_ids": [SHOTS], "note": SHOT_NOTE}],
    "Sunfire Cape": [{"stats": {"armor": 20}, "source_ids": [SHOTS], "note": SHOT_NOTE}],
    "Nashor's Tooth": [{"stats": {"crit_pct": 20}, "source_ids": [SHOTS], "note": SHOT_NOTE}],
    "Radiant Bloodthirster": [{"stats": {}, "source_ids": [SHOTS], "note": RADIANT_SHOT_NOTE}],
    "Radiant Gargoyle Stoneplate": [
        {"stats": {"armor": 50, "mr": 50}, "source_ids": [SHOTS], "note": RADIANT_SHOT_NOTE}
    ],
    "Radiant Steadfast Heart": [
        {"stats": {"armor": 40, "crit_pct": 40}, "source_ids": [SHOTS], "note": RADIANT_SHOT_NOTE}
    ],
}

# Emblems: transcribed from the owner's tooltip screenshots (2026-10-20). Their numbers
# predate 18.3 (e.g. Hunter 18% AD), so 18.3/18.4 note changes are applied on top.
EMBLEM = """
Blackthorn Emblem | 15% AD, 15 AP, 250 HP | The holder gains the Blackthorn trait. | SHOTS |
Blossom Emblem | 250 HP | The holder gains the Blossom trait. | SHOTS |
Brawler Emblem | 150 HP | The holder gains the Brawler trait. Attacks deal 2.5% of the holder's max Health as magic damage. | SHOTS, riot-notes-18.3 | 18.3: damage 2% => 2.5% max Health (screenshot showed 2%)
Coven Emblem | 150 HP | The holder gains the Coven trait. | SHOTS | not craftable (no recipe)
Defender Emblem | 30 Armor, 30 MR | The holder gains the Defender trait. Combat start: gain 6% Attack Speed for every ally that starts in the front row. | SHOTS | not craftable (no recipe)
Elderwood Emblem | 25 Armor, 25% AS, 25 MR | The holder gains the Elderwood trait. | SHOTS, riot-notes-18.4 | 18.4: resists 35 => 25 (screenshot showed 35)
Executioner Emblem | 20% Crit | The holder gains the Executioner trait. Damage executes enemies below 8% of their max Health. | SHOTS |
Fae Emblem | 200 HP | The holder gains the Fae trait. | SHOTS |
Hunter Emblem | 25% AD | The holder gains the Hunter trait. Takedowns grant 15% Attack Damage. | SHOTS, riot-notes-18.3 | 18.3: AD per takedown 18% => 15% (screenshot showed 18%)
Inferno Emblem | 40% AS | The holder gains the Inferno trait. | SHOTS |
Invoker Emblem | 2 Mana Regen | The holder gains the Invoker trait. On cast, gain Ability Power equal to 8% of Mana spent. | SHOTS, riot-notes-18.3 | 18.3: Mana Regen 3 => 2 (screenshot showed 3)
Juggernaut Emblem | 250 HP | The holder gains the Juggernaut trait. Gain 10 Mana whenever a Juggernaut dies. | SHOTS, riot-notes-18.3 | 18.3: Mana restore on death 15 => 10 (screenshot showed 15); not craftable (no recipe)
Lunar Emblem | 20% AS, 3 Mana Regen | The holder gains the Lunar trait. | SHOTS |
Primal Emblem | 35% AS, 20% Crit, 250 HP | The holder gains the Primal trait. | SHOTS |
Rapidfire Emblem | 20% AS | The holder gains the Rapidfire trait. Attacks deal 1% of the target's max Health as true damage. | SHOTS |
Ravager Emblem | 20% AD, 20 AP, 20 Armor, 20 MR | The holder gains the Ravager trait. Gain 3% Damage Amp per 300 Health restored. | SHOTS |
Spellweaver Emblem | 25 AP | The holder gains the Spellweaver trait. Gain 2 Mana whenever an ally casts their Ability. | SHOTS |
Sprykin Emblem | 15 Armor, 15 MR | The holder gains the Sprykin trait. If the holder is riding the BFF, it gains more (tooltip text broken: 'an additional 20% 15 15'). | SHOTS |
Vanguard Emblem | 25 Armor, 25 MR | The holder gains the Vanguard trait. If the holder survives 22 seconds in player combat, gain 1 player Health. | SHOTS |
"""

# Records that share a display name: name -> explicit id per screenshot.
FLORA = [
    (
        "DA_18_EmblemFloraFatalis",
        "250 HP, 2 Mana Regen",
        "The holder gains the Flora Fatalis trait.",
        "plain emblem (first screenshot); the owner marked the second screenshot as the right one, see the Augment record",
    ),
    (
        "DA_18_EmblemFloraFatalisAugment",
        "250 HP, 2 Mana Regen",
        "The holder gains the Flora Fatalis trait. They gain 50% increased benefits from Flora Fatalis.",
        "second screenshot; the Consuming Flora augment grants a Flora Fatalis emblem with +50% benefits, which matches this text",
    ),
]

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
        if i["kind"] in ("completed", "radiant", "artifact", "emblem"):
            target = by_name if i["family"] == "DA" else other
            target.setdefault(i["name"].lower(), []).append(i["id"])
    records, missing = [], []
    blocks = ((CRAFTABLE, [PAGE]), (RADIANT, [PAGE]), (ARTIFACT, [PAGE]), (EMBLEM, []))
    for block, base_sources in blocks:
        for name, stats, effect, extra, note in rows(block):
            extra = [TOKENS.get(s.strip(), s.strip()) for s in extra]
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
                "source_ids": base_sources + extra,
            }
            if note:
                rec["note"] = note
            if name in CONFLICTS:
                rec["conflicts"] = CONFLICTS[name]
            # Emblems of the same name in older sets are different items; no comparison.
            check = (
                None
                if block is EMBLEM
                else compare_with_copy(rec["stats"], copies.get(name.lower(), []))
            )
            if check is not None:
                rec["older_copy_check"] = check
            records.append(rec)
    for item_id, stats, effect, note in FLORA:
        if item_id not in kb.items:
            missing.append(f"{item_id}: not in the generated data")
            continue
        records.append(
            {
                "id": item_id,
                "name": kb.items[item_id]["name"],
                "stats": parse_stats(stats),
                "effect": effect,
                "status": "third_party_unverified",
                "source_ids": [SHOTS],
                "note": note,
            }
        )
    if missing:
        raise SystemExit("unmatched names:\n  " + "\n  ".join(missing))
    return {
        "set": set_id,
        "patch": patch,
        "kind": "item_stats",
        "note": (
            "Hand transcription of tactics.tools/info/items (read 2026-10-20; numbers match 18.2) "
            "and of the owner's emblem tooltip screenshots (numbers predate 18.3). "
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
