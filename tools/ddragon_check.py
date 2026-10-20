"""Cross-check champion names and costs against Riot's Data Dragon.

Data Dragon is Riot's own static data (names, costs, icons; no stats). This
tool downloads tft-champion.json for one Data Dragon version into
data/raw/ddragon/<version>/ and compares the set's champions with the
generated knowledge base. Differences are printed; nothing is changed.

Usage (PowerShell):
    python tools/ddragon_check.py set18 18.4 16.20.1 --set-path TFTSet18
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tft_engine.gamedata.entities import load_knowledge  # noqa: E402

URL = "https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/tft-champion.json"
USER_AGENT = "tft-engine (personal research; github.com/bahadiremirkizilay/tft-engine)"


def set_champions(ddragon: dict, set_path: str) -> dict[str, dict]:
    """Data Dragon entries whose key path names the set, by champion id."""
    out = {}
    for key, entry in ddragon.get("data", {}).items():
        if f"/{set_path}/" in key:
            out[entry["id"]] = entry
    return out


def compare(dd: dict[str, dict], champions: dict[str, dict]) -> list[str]:
    """Differences between Data Dragon entries and knowledge-base champions."""
    problems = []
    playable = {cid: c for cid, c in champions.items()}
    for cid, c in sorted(playable.items()):
        e = dd.get(cid)
        if e is None:
            problems.append(f"{cid} ({c['name']}): not in Data Dragon")
            continue
        if e.get("name") != c["name"]:
            problems.append(f"{cid}: name {c['name']!r} vs Data Dragon {e.get('name')!r}")
        if e.get("cost") != c["cost"]:
            problems.append(f"{cid}: cost {c['cost']} vs Data Dragon {e.get('cost')}")
    for cid in sorted(set(dd) - set(playable)):
        problems.append(
            f"{cid} ({dd[cid].get('name')}): in Data Dragon, not a playable champion here"
        )
    return problems


def fetch(version: str, out_root: Path) -> dict:
    dest = out_root / version / "tft-champion.json"
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(
            URL.format(version=version), headers={"User-Agent": USER_AGENT}
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            dest.write_bytes(resp.read())
    return json.loads(dest.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("set_id")
    p.add_argument("patch")
    p.add_argument("version", help="Data Dragon version, e.g. 16.20.1")
    p.add_argument(
        "--set-path", required=True, help="set folder in Data Dragon keys, e.g. TFTSet18"
    )
    p.add_argument("--raw", default=str(ROOT / "data" / "raw" / "ddragon"))
    args = p.parse_args(argv)
    dd = set_champions(fetch(args.version, Path(args.raw)), args.set_path)
    kb = load_knowledge(args.set_id, args.patch)
    problems = compare(dd, kb.champions)
    print(
        f"Data Dragon {args.version}: {len(dd)} {args.set_path} entries; "
        f"knowledge base: {len(kb.champions)} champions"
    )
    for line in problems:
        print("DIFF", line)
    print("OK" if not problems else f"{len(problems)} differences")
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
