# Instructions for Claude working in this repo

## Who and what

- The owner is Bahadır. Talk to them in **Turkish**, plainly; code, identifiers, commit messages in English.
- This is a TFT strategy research and decision engine. The current phase (PLAN v0.5) builds the game knowledge base: champions, traits, items, augments, Wisps, economy, shop, comps; versioned per patch and portable to later sets.
- Live in-game use is out of scope for now. The owner wants it eventually (local, personal use); it will be decided after the MVP, with Riot's TFT policy quoted in docs/KAYNAKLAR.md 1.4 and the account risk stated plainly. Never read game memory, inject into or automate the game client.
- Before any Riot API integration, check the current official developer policies; capacity is not permission. YouTube/Kick content is never downloaded or processed automatically; manual notes only.
- Work plan-first: for a new phase, research and present a plan; implement only after the owner approves.

## Where things are

- Plan (source of truth): `docs/PLAN.md` (v0.5). Previous plan: `docs/PLAN_v0.4.md`. Sources and research findings: `docs/KAYNAKLAR.md`. Data access, permissions and the owner's decisions: `docs/VERI_KAYNAKLARI.md` (personal use only; automatic data only from CommunityDragon, Data Dragon, official notes and later the Riot API; stats sites: since 2026-10-21 the owner allows reading public pages for personal verification and extension, per patch or on request, only where robots.txt and the terms allow (TFT Academy yes, MetaTFT and tactics.tools no stated ban, METAsrc banned); no hidden APIs, no bypassing logins or bot protection, no scheduled scraping (VERI_KAYNAKLARI, owner's decision 2026-10-21); meta rank filter Master+, widen to Diamond/Emerald if samples are small). Status and next steps: `docs/DURUM.md`. P1 results: `docs/P1_SONUC.md`.
- Game data: `data/sets/<set>/base.json` plus `data/sets/<set>/patches/<patch>.json`. Every value carries `status` and `source`. Planned (PLAN v0.5 section 4): `generated/<patch>/` written only by the importer, `curated/` for hand-made records; the importer never overwrites curated files.
- Python: system Python may be too old; use the repo `.venv` (`.\.venv\Scripts\python.exe`).
- Code: `src/tft_engine/` with
  - `gamedata`: schema and patch loader
  - `state`: game state and pool belief
  - `rules`: economy
  - `prob`: shop model, exact solver and Monte Carlo sampler
  - `decision`: the P1 prototype
  - `repro`: seeds
  - `experiments`: run log and replay
- Scenarios: `scenarios/p1/*.json`. Templates for the owner: `templates/`.

## Non-negotiable rules

1. Do not invent game mechanics or values. Unknown values stay `"status": "unknown"` with `null` and raise `UnknownMechanicError` when used. New values need a source; third-party values are `third_party_unverified` until checked in-game.
2. Everything is per patch. Buffs and nerfs go in `patches/<patch>.json` as change records with `kind` and `source`. Never edit `base.json` to reflect a later patch.
3. Separate verified facts, assumptions and unknowns in every output (trust classes: exact, data_estimated, assumption).
4. Every important component gets tests. Run `python -m pytest` and `ruff check .` and `ruff format --check .` before each commit.
5. Reproducibility: seeds through `tft_engine.repro.derive_seed`; no unseeded randomness.
6. Decision assumptions live in `src/tft_engine/decision/assumptions.py` with a default and a low/high range; never hard-code them elsewhere.
7. Keep core layers (gamedata, state, rules, prob, decision) free of network calls. Network access lives only in `tools/` importers.
8. One source of truth per game rule: rules read parameters through the data layer (and, from B3, modifiers); never a second hard-coded copy of a value.
9. Conflicting sources are never merged silently: keep both values with their sources in `conflicts`. Source priority: official patch notes > in-game observation > game files (CommunityDragon) > Data Dragon > wiki and stats sites.
10. Meta statistics stay separate from game rules and from comp templates; every stat records site, rank filter, patch and definition.

## Next work (see docs/DURUM.md and PLAN v0.5 section 8)

- B1 done for 18.4 (`tools/cdragon_fetch.py`, `tools/import_cdragon.py`, `gamedata/{cdragon,entities,sources,hashes}.py`, `tft-engine data check|diff`). Repeat for 18.5 when CommunityDragon has it (add the source with its sha256 and a `cdragon_versions` entry first).
- B2 done: patches 18.2/18.2b/18.3/18.4 reviewed; odds and pool sizes from map22.bin.json; params carry `source_ids` and `conflicts`; `sell_value`, `player_damage`; `tools/ddragon_check.py`; `templates/oyun_ici_kontrol.md`. The owner's review notes live in the "Set 18 Veri İncelemesi" artifact (https://claude.ai/artifact/3aDCUtrQ8fAFh6aYP5DWFg, db collection `corrections`); read them with ArtifactData and turn accepted ones into sourced curated corrections.
- Curated layers (`gamedata/curated.py`): `curated/item_stats/<patch>.json` (from tools/curate_item_stats.py), `curated/augment_tiers/<patch>.json` (tools/curate_augment_tiers.py), `curated/overrides/<patch>.json` (official note values; each states the old value it replaces). Game-file balance numbers can lag the notes and Set 18 `DA_` items have no stats in the export; older `TFT_Item_*` copies carry outdated values and must never be used as Set 18 values. tactics.tools info pages showed 18.2 state on 2026-10-20.
- B3 done (2026-10-21): `rules/modifiers.py` (Modifier, Event, ModifierSet, `build` from curated models); `Rules(data, modifiers=...)` applies modifiers on every read and fires events; `curated/effects/augments.json` models 64 economy/XP/shop augments by reference to their effect values (`tft-engine data augments`); shop model has `slot_probs`, Wisp buy/never policies (`wisp_shop_prob`, `wisp_price` assumptions), Blossom every-shop rule from data, Lux form `share`. Never put a game number in code or in a model when the augment record has it.
- B4 done (2026-10-21): `rules/items.py` (RecipeBook: 55 DA recipes, options, full builds, missing; `stat_bonus`; `emblem_trait` by name), `rules/traits.py` (unique champions, Avatar counts its trait twice, emblem rule from data `emblem_on_same_trait_counts`), `decision/item_fit.py` (rule-based, weights in assumptions), CLI `items`, `traits`, `items-for`; Evaluator computes active traits from real boards. Roles: `curated/champion_roles.json` (empty, waiting for the owner). Set 18 ability values are not in any CommunityDragon file (KAYNAKLAR section 2).
- B5 infrastructure done (2026-10-21): `rules/comps.py` (templates in `curated/comps/<patch>.json`, meta in `curated/meta/<patch>/<site>.json` with site, patch, rank filter, definition; `check_comps`), `decision/comp_match.py` (`match_comps`, `best_trio`, weights in assumptions), CLI `comps`, `trio`. 18.4 has 3 test comps from tactics.tools; 18.5 comps and MetaTFT trio stats (Master+) once 18.5 data settles.
- Next B6 (combat interface), B7 (patch loop, Set 19 rehearsal). 18.5 import when CommunityDragon has it.
