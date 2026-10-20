# Instructions for Claude working in this repo

## Who and what

- The owner is Bahadır. Talk to them in **Turkish**, plainly; code, identifiers, commit messages in English.
- This is an offline TFT strategy research and post-game analysis engine. It never runs during a live game, never reads or controls the game client, and never gives live in-game advice. Keep it that way.
- Before any Riot API integration, check the current official developer policies; capacity is not permission. YouTube/Kick content is never downloaded or processed automatically; manual notes only.

## Where things are

- Plan (source of truth): `docs/PLAN.md`. Status and next steps: `docs/DURUM.md`. P1 results: `docs/P1_SONUC.md`.
- Game data: `data/sets/<set>/base.json` plus `data/sets/<set>/patches/<patch>.json`. Every value carries `status` and `source`.
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
7. Keep core layers (gamedata, state, rules, prob, decision) free of network calls.

## Next work (see docs/DURUM.md)

- M1b: sell rules and partial buys (main cause of P1's bias to keep gold); Wisp/Inferno/Riftbeast variants; bad luck protection research; tests against the owner's recorded games.
- P1: convert the owner's labelled situations into `scenarios/p1/` with `expert_choice`, keep a seeded dev/test split, and report agreement as described in docs/PLAN.md (P1).
