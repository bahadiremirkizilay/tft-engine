"""Command line entry point.

Examples:
    tft-engine run toy_dice_mean --config configs/example.json --seed 1 --log runs/runs.jsonl
    tft-engine replay runs/runs.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tft_engine.experiments import load_records, replay, run_experiment


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

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
