"""Turn a downloaded CommunityDragon export into knowledge-base files.

Reads data/raw/cdragon/<version>/ (download it first with tools/cdragon_fetch.py),
checks the file against the source registry, and writes
data/sets/<set>/generated/<patch>/{champions,traits,items,augments,wisps,summary}.json.
The TFT patch comes from the set's calendar.json (cdragon_versions). Generated
files are never edited by hand; corrections go to data/sets/<set>/curated/.

Usage (PowerShell):
    python tools/import_cdragon.py set18 16.20
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tft_engine.gamedata.cdragon import GENERATOR, KINDS, normalize, summary  # noqa: E402
from tft_engine.gamedata.sources import load_calendar, load_sources  # noqa: E402


def dump(obj: object) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run(set_id: str, version: str, data_root: Path, raw_root: Path) -> dict:
    calendar = load_calendar(set_id, data_root / "sets")
    mapping = calendar.cdragon.get(version)
    if not mapping:
        raise SystemExit(f"{set_id}/calendar.json has no cdragon_versions entry for {version}")
    patch = mapping["patch"]

    source_id = f"cdragon-{version}"
    sources = load_sources(data_root / "sources.json")
    source = sources[source_id]
    raw_path = raw_root / version / "en_us.json"
    actual = sha256_of(raw_path)
    expected = source.sha256.get("en_us.json")
    if actual != expected:
        raise SystemExit(
            f"{raw_path} sha256 {actual} does not match sources.json ({expected}). "
            "The file changed: register it as a new source before importing."
        )
    for problem in calendar.check_assignment(source, patch):
        print(f"WARNING: {problem}")

    rules_path = data_root / "sets" / set_id / "curated" / "cdragon_rules.json"
    rules = json.loads(rules_path.read_text(encoding="utf-8"))
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    records = normalize(raw, rules, set_id, patch, source_id)

    out = data_root / "sets" / set_id / "generated" / patch
    out.mkdir(parents=True, exist_ok=True)
    header = {
        "set": set_id,
        "patch": patch,
        "source_id": source_id,
        "generator": GENERATOR,
        "patch_mapping": mapping,
    }
    for kind in KINDS:
        doc = {**header, "kind": kind, "count": len(records[kind]), "records": records[kind]}
        (out / f"{kind}.json").write_text(dump(doc), encoding="utf-8")
    info = {**header, "summary": summary(records)}
    (out / "summary.json").write_text(dump(info), encoding="utf-8")
    return info


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("set_id", help="e.g. set18")
    p.add_argument("version", help="CommunityDragon version folder, e.g. 16.20")
    p.add_argument("--data", default=str(ROOT / "data"))
    p.add_argument("--raw", default=str(ROOT / "data" / "raw" / "cdragon"))
    args = p.parse_args(argv)
    info = run(args.set_id, args.version, Path(args.data), Path(args.raw))
    print(dump(info))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
