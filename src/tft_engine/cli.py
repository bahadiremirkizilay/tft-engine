"""Command line entry point.

Examples:
    tft-engine run toy_dice_mean --config configs/example.json --seed 1 --log runs/runs.jsonl
    tft-engine replay runs/runs.jsonl
    tft-engine odds --set set18 --patch 18.4 --level 8 --gold 50 --target Ahri:4:2 --taken Ahri:3
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tft_engine.experiments import load_records, replay, run_experiment
from tft_engine.gamedata import load_gamedata
from tft_engine.prob import IndependentShopModel, RollQuery, Target, roll_down_exact
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
    model = IndependentShopModel.from_gamedata(data, wisp_takes_slot=args.wisp)
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
    p_odds.add_argument("--wisp", action="store_true", help="assume a Wisp takes a slot")
    p_odds.set_defaults(func=_cmd_odds)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
