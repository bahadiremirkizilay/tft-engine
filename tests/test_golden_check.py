"""The golden-output helper reports moved results and rewrites only on request."""

import json

import pytest

from tests import golden_check
from tests.golden_check import assert_golden, differences


def test_differences_name_each_moved_value():
    old = {"ranking": ["A", "B"], "c": {"A": {"score": 1.0}, "B": {"score": 2.0}}}
    new = {"ranking": ["B", "A"], "c": {"A": {"score": 1.5}}, "flips": {"x": ["A", "B"]}}
    diff = "\n".join(differences(old, new))
    assert "~ ranking" in diff
    assert "~ c.A.score: 1.0 -> 1.5" in diff
    assert "- c.B.score" in diff
    assert "+ flips.x" in diff


def test_changed_result_fails_until_updated(tmp_path, monkeypatch):
    monkeypatch.setattr(golden_check, "GOLDEN_DIR", tmp_path)
    with pytest.raises(AssertionError, match="missing"):
        assert_golden("g", {"v": 1.0}, update=False)
    assert_golden("g", {"v": 1.0}, update=True)
    assert_golden("g", {"v": 1.00001}, update=False)  # below the rounding step
    with pytest.raises(AssertionError, match="KARARLAR"):
        assert_golden("g", {"v": 2.0}, update=False)
    assert json.loads((tmp_path / "g.json").read_text("utf-8")) == {"v": 1.0}
