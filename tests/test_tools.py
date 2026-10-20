import importlib.util
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools" / "extract_frames.py"
spec = importlib.util.spec_from_file_location("extract_frames", TOOL)
extract_frames = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extract_frames)


def test_ffmpeg_command_samples_at_the_given_interval(tmp_path):
    cmd = extract_frames.build_command(Path("game.mp4"), tmp_path, 20, 1280)
    assert cmd[0] == "ffmpeg"
    assert "fps=1/20,scale=1280:-2" in cmd
    assert cmd[-1].endswith("frame_%05d.png")


def test_rejects_bad_interval(tmp_path):
    with pytest.raises(ValueError):
        extract_frames.build_command(Path("game.mp4"), tmp_path, 0, 1280)


def test_missing_video_is_an_error(tmp_path, monkeypatch):
    monkeypatch.setattr(extract_frames.shutil, "which", lambda _: "/usr/bin/ffmpeg")
    assert extract_frames.main([str(tmp_path / "nope.mp4")]) == 2
