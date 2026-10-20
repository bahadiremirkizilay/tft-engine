"""Pull still frames from YOUR OWN recorded TFT game, after the game.

Run it only on finished recordings of your own games (for example OBS output).
It does not touch the game, never runs during a match, and does not download
anything. Do not use it on other people's streams or VODs: YouTube and Kick
terms forbid downloading and automated processing.

Usage (PowerShell):
    python tools/extract_frames.py recordings\\2026-10-21_1.mp4 --every 20

Needs ffmpeg on PATH (https://ffmpeg.org/download.html). Frames go to
recordings/<video name>_frames/frame_00001.png ...; the time of each frame is
(index - 1) * every seconds from the start of the video.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def build_command(video: Path, out_dir: Path, every: float, width: int) -> list[str]:
    if every <= 0:
        raise ValueError("--every must be positive")
    vf = f"fps=1/{every:g},scale={width}:-2"
    return [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(video),
        "-vf", vf, str(out_dir / "frame_%05d.png"),
    ]  # fmt: skip


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("video", type=Path)
    p.add_argument("--every", type=float, default=20.0, help="seconds between frames")
    p.add_argument("--width", type=int, default=1280, help="output width in pixels")
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args(argv)
    if shutil.which("ffmpeg") is None:
        print("ffmpeg not found on PATH", file=sys.stderr)
        return 2
    if not args.video.is_file():
        print(f"no such video: {args.video}", file=sys.stderr)
        return 2
    out = args.out or args.video.with_name(args.video.stem + "_frames")
    out.mkdir(parents=True, exist_ok=True)
    subprocess.run(build_command(args.video, out, args.every, args.width), check=True)
    n = len(list(out.glob("frame_*.png")))
    print(f"{n} frames written to {out} (one every {args.every:g} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
