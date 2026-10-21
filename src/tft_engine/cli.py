"""Command line entry point.

Examples:
    tft-engine run toy_dice_mean --config configs/example.json --seed 1 --log runs/runs.jsonl
    tft-engine replay runs/runs.jsonl
    tft-engine decide scenarios/p1/o1_one_copy_from_3star.json
    tft-engine odds --set set18 --patch 18.4 --level 8 --gold 50 --target Ahri:4:2 --taken Ahri:3
    tft-engine data check --set set18 --patch 18.4
    tft-engine data diff --set set18 18.4 18.5
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tft_engine.decision import Evaluator, load_scenario
from tft_engine.decision.assumptions import AssumptionSet
from tft_engine.decision.item_fit import best_items, profile
from tft_engine.decision.report import render
from tft_engine.experiments import load_records, replay, run_experiment
from tft_engine.gamedata import load_gamedata
from tft_engine.gamedata.entities import check_all, diff_knowledge, load_knowledge
from tft_engine.prob import IndependentShopModel, RollQuery, Target, roll_down_exact
from tft_engine.rules.items import RecipeBook
from tft_engine.rules.traits import active_traits, trait_counts
from tft_engine.state import PoolBelief, PoolState


def _cmd_run(args: argparse.Namespace) -> int:
    config = json.loads(Path(args.config).read_text(encoding="utf-8")) if args.config else {}
    record = run_experiment(args.name, config, args.seed, args.data_version)
    record.append_to(Path(args.log))
    print(json.dumps(record.metrics, indent=2, ensure_ascii=False))
    print(f"run {record.run_id} logged to {args.log} (config {record.config_hash})")
    return 0


def _cmd_replay(args: argparse.Namespace) -> int:
    records = load_records(Path(args.log))
    if args.run_id:
        records = [r for r in records if r.run_id == args.run_id]
        if not records:
            print(f"no run with id {args.run_id}", file=sys.stderr)
            return 2
    failed = 0
    for rec in records:
        ok, diffs = replay(rec)
        print(f"{rec.run_id} {rec.name}: {'OK' if ok else 'MISMATCH'}")
        for key, (old, new) in diffs.items():
            print(f"  {key}: recorded={old!r} now={new!r}")
        failed += not ok
    return 1 if failed else 0


def _cmd_odds(args: argparse.Namespace) -> int:
    data = load_gamedata(args.set, args.patch)
    tracked, targets = {}, []
    for spec in args.target:
        unit, cost, need = spec.split(":")
        tracked[unit] = int(cost)
        targets.append(Target(unit, int(need)))
    taken = {}
    for spec in args.taken:
        unit, n = spec.split(":")
        taken[unit] = int(n)
    cp = {int(k): v for k, v in data.get("copies_per_champion").items()}
    cc = {int(k): v for k, v in data.get("champions_per_cost").items()}
    pool = PoolState.build(cp, cc, tracked, taken=taken)
    model = IndependentShopModel.from_gamedata(
        data, wisp_prob=args.wisp_prob, wisp_bought=args.buy_wisp
    )
    query = RollQuery(
        level=args.level,
        gold=args.gold,
        targets=tuple(targets),
        roll_cost=data.get("reroll_cost"),
        gold_floor=args.floor,
    )
    r = roll_down_exact(query, PoolBelief.certain(pool), model)
    print(f"set {args.set} patch {args.patch} | model {r.model}")
    print(f"P(success)        = {r.p_success:.4f}")
    print(f"expected rolls    = {r.expected_rolls:.2f}")
    print(f"expected gold left= {r.expected_gold_left:.2f}")
    print("assumptions:")
    for a in r.assumptions:
        print(f"  - {a}")
    if data.unreviewed_patches:
        print(f"WARNING: patches not reviewed yet: {', '.join(data.unreviewed_patches)}")
    return 0


def _cmd_decide(args: argparse.Namespace) -> int:
    sc = load_scenario(args.scenario)
    ev = Evaluator(sc)
    result = ev.evaluate()
    sens = None if args.no_sensitivity else ev.sensitivity(result)
    augs = ev.augments() if sc.augment_offers else None
    print(render(sc, result, sens, augs))
    return 0


def _cmd_data_check(args: argparse.Namespace) -> int:
    kb, rep = check_all(args.set, args.patch)
    print(f"{args.set} {args.patch}: " + ", ".join(f"{k} {len(v)}" for k, v in kb.records.items()))
    for w in rep.warnings[: args.max]:
        print(f"WARNING: {w}")
    if len(rep.warnings) > args.max:
        print(f"... {len(rep.warnings) - args.max} more warnings (use --max)")
    for e in rep.errors:
        print(f"ERROR: {e}")
    print("OK" if rep.ok else f"FAILED: {len(rep.errors)} errors")
    return 0 if rep.ok else 1


def _cmd_data_augments(args: argparse.Namespace) -> int:
    """Coverage of the augment models: which augments change the rules, and how fully."""
    kb = load_knowledge(args.set, args.patch)
    models = kb.augment_models
    offered = [
        a
        for a in kb.augments.values()
        if isinstance(a.get("offered_in_set"), dict) and not a.get("variant_of")
    ]
    print(f"{args.set} {args.patch}: {len(offered)} augments offered, {len(models)} with a model")
    table: dict[str, dict[str, int]] = {}
    for m in models.values():
        row = table.setdefault(m["category"], {"modelled": 0, "partial": 0, "text_only": 0})
        row[m["model_status"]] += 1
    for cat in sorted(table):
        row = table[cat]
        total = sum(row.values())
        print(
            f"  {cat:8} {total:3}: modelled {row['modelled']}, partial {row['partial']}, "
            f"text_only {row['text_only']}"
        )
    if args.list:
        for aid, m in sorted(models.items()):
            name = kb.augments.get(aid, {}).get("name", "?")
            note = f" - {m['note']}" if m.get("note") else ""
            print(f"  [{m['model_status']}] {name} ({aid}){note}")
    return 0


def _champion_id(kb, name_or_id: str) -> str:
    if name_or_id in kb.champions:
        return name_or_id
    key = name_or_id.strip().lower()
    hits = [c["id"] for c in kb.champions.values() if c["name"].lower() == key]
    if len(hits) > 1:  # a name shared with variants: prefer the base champion
        hits = [h for h in hits if not kb.champions[h].get("variant_of")]
    if len(hits) != 1:
        raise SystemExit(f"no single champion named {name_or_id!r}")
    return hits[0]


def _split(text: str) -> list[str]:
    return [x.strip() for x in text.split(",") if x.strip()]


def _cmd_items(args: argparse.Namespace) -> int:
    """What the held components can build."""
    kb = load_knowledge(args.set, args.patch)
    book = RecipeBook(kb)
    try:
        have = [book.item_id(x) for x in _split(args.have)]
    except KeyError as e:
        raise SystemExit(str(e)) from None
    print("held: " + ", ".join(book.name(c) for c in have))
    print("one pair can make:")
    for b in book.options(have):
        stats = kb.items[b.item].get("stats", {})
        stat_text = ", ".join(f"{k} {v:g}" for k, v in stats.items())
        recipe = f"{book.name(b.pair[0])} + {book.name(b.pair[1])}"
        print(f"  {book.name(b.item)} = {recipe}  [{stat_text}]")
    builds = book.full_builds(have)
    if len(have) > 2 and builds:
        print("using every component:")
        for items in builds:
            print("  " + " + ".join(book.name(i) for i in items))
    print("stats: third-party values (tactics.tools, MetaTFT), not checked in game")
    return 0


def _cmd_traits(args: argparse.Namespace) -> int:
    """Active traits of a board."""
    kb = load_knowledge(args.set, args.patch)
    data = load_gamedata(args.set, args.patch)
    book = RecipeBook(kb)
    board = [_champion_id(kb, x) for x in _split(args.board)]
    emblems: dict[str, list[str]] = {}
    for spec in args.emblem:
        holder, item = spec.split(":", 1)
        emblems.setdefault(_champion_id(kb, holder), []).append(book.item_id(item))
    same = data.param("emblem_on_same_trait_counts")
    counts, notes = trait_counts(kb, board, emblems, bool(same.get()))
    for t in active_traits(kb, counts):
        if t.active:
            nxt = f", next at {t.next_breakpoint}" if t.next_breakpoint else ""
            print(f"  {t.name} {t.count} (active at {t.breakpoint}{nxt})")
        else:
            print(f"  {t.name} {t.count} (inactive, needs {t.next_breakpoint})")
    for n in notes:
        print(f"note: {n}")
    print(f"emblem rule ({same.status}): {same.source}")
    return 0


def _cmd_items_for(args: argparse.Namespace) -> int:
    """Items that suit a champion, by rule (assumption)."""
    kb = load_knowledge(args.set, args.patch)
    cid = _champion_id(kb, args.champion)
    a = AssumptionSet()
    prof = profile(kb, cid)
    print(f"{kb.champions[cid]['name']}: {', '.join(prof.tags)} ({'; '.join(prof.reasons)})")
    if prof.role is None:
        print("  role unknown (not in the game data yet); tanks may get damage items")
    done = [i["id"] for i in kb.items.values() if i["kind"] == "completed" and i["family"] == "DA"]
    for f in best_items(kb, cid, a, done, args.top):
        print(f"  {kb.items[f.item]['name']:24} {f.score:+.0f}  {'; '.join(f.reasons)}")
    print("trust: assumption (rule weights in decision/assumptions.py item_fit_weights)")
    return 0


def _cmd_data_diff(args: argparse.Namespace) -> int:
    old = load_knowledge(args.set, args.old)
    new = load_knowledge(args.set, args.new)
    for kind, d in diff_knowledge(old, new).items():
        print(f"== {kind}: +{len(d['added'])} -{len(d['removed'])} changed {len(d['changed'])}")
        for rid in d["added"]:
            print(f"  + {rid}")
        for rid in d["removed"]:
            print(f"  - {rid}")
        for rid, fields in d["changed"].items():
            for name, (a, b) in fields.items():
                print(f"  ~ {rid}.{name}: {a!r} -> {b!r}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tft-engine")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="run an experiment and append it to the log")
    p_run.add_argument("name")
    p_run.add_argument("--config", help="JSON config file")
    p_run.add_argument("--seed", type=int, required=True)
    p_run.add_argument("--data-version", default="none")
    p_run.add_argument("--log", default="runs/runs.jsonl")
    p_run.set_defaults(func=_cmd_run)

    p_rep = sub.add_parser("replay", help="rerun logged experiments and compare results")
    p_rep.add_argument("log")
    p_rep.add_argument("--run-id")
    p_rep.set_defaults(func=_cmd_replay)

    p_odds = sub.add_parser("odds", help="exact roll-down odds for one situation")
    p_odds.add_argument("--set", required=True)
    p_odds.add_argument("--patch", required=True)
    p_odds.add_argument("--level", type=int, required=True)
    p_odds.add_argument("--gold", type=int, required=True)
    p_odds.add_argument("--target", action="append", required=True, help="unit:cost:copies")
    p_odds.add_argument("--taken", action="append", default=[], help="unit:copies held by anyone")
    p_odds.add_argument("--floor", type=int, default=0, help="stop rolling below this gold")
    p_odds.add_argument(
        "--wisp-prob",
        type=float,
        default=None,
        help="chance a shop shows a Wisp and has one champion slot fewer "
        "(default: the set data, every other shop in Set 18)",
    )
    p_odds.add_argument(
        "--buy-wisp",
        action="store_true",
        help="this round's Wisp is bought, so every shop shows all champion slots",
    )
    p_odds.set_defaults(func=_cmd_odds)

    p_dec = sub.add_parser("decide", help="P1: compare candidate decisions for a scenario")
    p_dec.add_argument("scenario", help="scenario JSON file")
    p_dec.add_argument("--no-sensitivity", action="store_true")
    p_dec.set_defaults(func=_cmd_decide)

    p_items = sub.add_parser("items", help="what held components can build")
    p_items.add_argument("--set", required=True)
    p_items.add_argument("--patch", required=True)
    p_items.add_argument(
        "--have", required=True, help='component names, e.g. "B.F. Sword,Recurve Bow"'
    )
    p_items.set_defaults(func=_cmd_items)

    p_traits = sub.add_parser("traits", help="active traits of a board")
    p_traits.add_argument("--set", required=True)
    p_traits.add_argument("--patch", required=True)
    p_traits.add_argument(
        "--board", required=True, help='champion names, e.g. "Ahri,Sett,Lux (Elderwood)"'
    )
    p_traits.add_argument(
        "--emblem", action="append", default=[], help='holder:emblem, e.g. "Sett:Blossom Emblem"'
    )
    p_traits.set_defaults(func=_cmd_traits)

    p_fit = sub.add_parser("items-for", help="items that suit a champion (rule-based)")
    p_fit.add_argument("champion")
    p_fit.add_argument("--set", required=True)
    p_fit.add_argument("--patch", required=True)
    p_fit.add_argument("--top", type=int, default=8)
    p_fit.set_defaults(func=_cmd_items_for)

    p_data = sub.add_parser("data", help="knowledge base: check or compare patches")
    data_sub = p_data.add_subparsers(dest="data_cmd", required=True)
    p_chk = data_sub.add_parser("check", help="load and check one patch")
    p_chk.add_argument("--set", required=True)
    p_chk.add_argument("--patch", required=True)
    p_chk.add_argument("--max", type=int, default=30, help="warnings to print")
    p_chk.set_defaults(func=_cmd_data_check)
    p_aug = data_sub.add_parser("augments", help="coverage of the augment models")
    p_aug.add_argument("--set", required=True)
    p_aug.add_argument("--patch", required=True)
    p_aug.add_argument("--list", action="store_true", help="list every model with its note")
    p_aug.set_defaults(func=_cmd_data_augments)
    p_diff = data_sub.add_parser("diff", help="what changed between two patches")
    p_diff.add_argument("--set", required=True)
    p_diff.add_argument("old")
    p_diff.add_argument("new")
    p_diff.set_defaults(func=_cmd_data_diff)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
