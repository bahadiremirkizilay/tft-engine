"""Download CommunityDragon files for one game version, with resume and retries.

This is the only place that talks to the network for CommunityDragon. Files go to
data/raw/cdragon/<version>/ (git-ignored). Nothing here parses game data.

Usage (PowerShell):
    python tools/cdragon_fetch.py 16.20
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://raw.communitydragon.org"
FILES = {
    "content-metadata.json": "{base}/{version}/content-metadata.json",
    "en_us.json": "{base}/{version}/cdragon/tft/en_us.json",
}
USER_AGENT = "tft-engine (personal research; github.com/bahadiremirkizilay/tft-engine)"
ROOT = Path(__file__).resolve().parents[1]


def file_url(name: str, version: str) -> str:
    return FILES[name].format(base=BASE, version=version)


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path, retries: int = 20, timeout: float = 60.0) -> None:
    """Stream url to dest. A partial dest.part is resumed with an HTTP Range request."""
    part = dest.with_suffix(dest.suffix + ".part")
    dest.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, retries + 1):
        have = part.stat().st_size if part.exists() else 0
        headers = {"User-Agent": USER_AGENT}
        if have:
            headers["Range"] = f"bytes={have}-"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                mode = "ab" if have and resp.status == 206 else "wb"
                with part.open(mode) as f:
                    while chunk := resp.read(1 << 16):
                        f.write(chunk)
            part.replace(dest)
            return
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            print(f"  attempt {attempt}/{retries} failed: {e}; resuming", file=sys.stderr)
            time.sleep(min(5 * attempt, 30))
    raise RuntimeError(f"could not download {url}")


def last_modified(url: str, timeout: float = 30.0) -> str | None:
    """Server's Last-Modified header for url (HEAD request), or None."""
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.headers.get("Last-Modified")
    except (urllib.error.URLError, TimeoutError, OSError):
        return None


def fetch(version: str, out_root: Path) -> dict[str, dict[str, object]]:
    """Download missing files; return name -> {url, bytes, sha256, last_modified}."""
    out = out_root / version
    info: dict[str, dict[str, object]] = {}
    for name in FILES:
        url = file_url(name, version)
        dest = out / name
        if not dest.exists():
            print(f"downloading {url}")
            download(url, dest)
        info[name] = {
            "url": url,
            "bytes": dest.stat().st_size,
            "sha256": sha256_of(dest),
            "last_modified": last_modified(url),
        }
        print(f"{name}: {info[name]}")
    meta = out / "fetch.json"
    meta.write_text(json.dumps(info, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return info


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("version", help="CommunityDragon version folder, e.g. 16.20 or pbe")
    p.add_argument("--out", default=str(ROOT / "data" / "raw" / "cdragon"))
    args = p.parse_args(argv)
    fetch(args.version, Path(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
