---
name: denetim
description: Full project audit for tft-engine - runs tools/verify.py, then the three read-only auditor agents (veri-denetci, tutarlilik-denetci, varsayim-denetci) on a git range, and gives the owner one Turkish report. Use at the end of each plan step, before closing a phase, after a large change, or when the owner types /denetim.
---

# /denetim

Goal: before a step is called done, confirm that data, code, assumptions, golden outputs and docs still agree, and show the owner what needs their judgement.

## Arguments

- none: range `main...HEAD` plus uncommitted changes
- a ref or range (`HEAD~3`, `abc123..HEAD`): that range plus uncommitted changes
- `tam` (full): the whole repo, not just a range (slow; use at phase end)

## Steps

1. **Deterministic checks first (free).** Run `.venv/Scripts/python.exe tools/verify.py` (use `--quick` only if the owner asked for a fast pass). Then `.venv/Scripts/python.exe -m tft_engine audit` for the full list including known debt. If verify fails, still continue, but the report leads with the failure.
2. **Scope.** `git diff --stat <range>` and `git status --short`. Decide which agents are needed:
   - `veri-denetci` if anything under `data/`, `src/tft_engine/gamedata/` or `tools/` changed (or `tam`);
   - `varsayim-denetci` if anything under `src/tft_engine/decision/`, `src/tft_engine/sim/`, `src/tft_engine/rules/board_stats.py`, `tests/golden/` or `docs/KARARLAR.md` changed (or `tam`);
   - `tutarlilik-denetci` always.
   Skipping an agent that has nothing to review saves the owner's Claude Pro usage; say which were skipped and why.
3. **Run the chosen agents in parallel** (one message, several Agent calls). Give each: the range, whether to include uncommitted changes, and the verify/audit summary so they do not rerun the slow parts. They are read-only.
4. **Check their findings** before reporting: open the cited file:line for each error; drop anything that is wrong, mark anything uncertain as such. Do not forward findings unverified.
5. **Report to the owner in Turkish**, plain and short:
   - first line: verdict (temiz / düzeltilecek N şey / sahibin kararı gereken M şey);
   - **Hatalar** (must fix before the step closes), **Gevşek uçlar**, **Senin kararın gerekenler** (questions only the owner can answer), **Bilinen borç** (count from audit.toml; new debt named);
   - each item one line with a file link.
6. Do not fix anything inside /denetim unless the owner asks; propose fixes. After fixes, a new commit runs verify again through the pre-commit hook.

## Notes

- Agents run on `sonnet` to spend less of the Pro plan; the deterministic audit costs nothing and runs on every commit anyway.
- Accepted exceptions and known debt live in `audit.toml`; generated maps in `docs/BAGLANTILAR.md` and `docs/VARSAYIMLAR.md`; decision log in `docs/KARARLAR.md`.
