import json

import pytest
from hypothesis import given
from hypothesis import strategies as st

from tft_engine.cli import main
from tft_engine.experiments import config_hash, load_records, replay, run_experiment

json_values = st.recursive(
    st.none() | st.booleans() | st.integers() | st.text(max_size=10),
    lambda children: st.lists(children, max_size=3)
    | st.dictionaries(st.text(max_size=5), children, max_size=3),
    max_leaves=10,
)


@given(st.dictionaries(st.text(max_size=5), json_values, max_size=5))
def test_config_hash_ignores_key_order(cfg):
    reordered = dict(reversed(list(cfg.items())))
    assert config_hash(cfg) == config_hash(reordered)


def test_config_hash_changes_with_values():
    assert config_hash({"a": 1}) != config_hash({"a": 2})


def test_same_seed_same_metrics():
    a = run_experiment("toy_dice_mean", {"samples": 5000}, seed=3)
    b = run_experiment("toy_dice_mean", {"samples": 5000}, seed=3)
    assert a.metrics == b.metrics
    assert a.reproducible_view() == b.reproducible_view()
    assert a.run_id != b.run_id  # different runs, same result


def test_different_seed_different_metrics():
    a = run_experiment("toy_dice_mean", {"samples": 5000}, seed=3)
    b = run_experiment("toy_dice_mean", {"samples": 5000}, seed=4)
    assert a.metrics["mean"] != b.metrics["mean"]


def test_toy_interval_covers_true_mean():
    r = run_experiment("toy_dice_mean", {"samples": 50_000}, seed=11)
    assert r.metrics["ci95_low"] <= r.metrics["true_mean"] <= r.metrics["ci95_high"]


def test_log_roundtrip_and_replay(tmp_path):
    log = tmp_path / "runs.jsonl"
    rec = run_experiment("toy_dice_mean", {"samples": 2000}, seed=5)
    rec.append_to(log)
    loaded = load_records(log)
    assert len(loaded) == 1
    assert loaded[0].reproducible_view() == rec.reproducible_view()
    ok, diffs = replay(loaded[0])
    assert ok, diffs


def test_replay_detects_changed_result(tmp_path):
    rec = run_experiment("toy_dice_mean", {"samples": 2000}, seed=5)
    rec.metrics["mean"] = 0.0  # simulate a result that no longer reproduces
    ok, diffs = replay(rec)
    assert not ok
    assert "metrics" in diffs


def test_unknown_experiment():
    with pytest.raises(KeyError):
        run_experiment("does_not_exist", {}, seed=1)


def test_cli_run_then_replay(tmp_path, capsys):
    cfg = tmp_path / "cfg.json"
    cfg.write_text(json.dumps({"samples": 1000}), encoding="utf-8")
    log = tmp_path / "runs.jsonl"
    args = ["run", "toy_dice_mean", "--config", str(cfg), "--seed", "9", "--log", str(log)]
    assert main(args) == 0
    assert main(["replay", str(log)]) == 0
    assert "OK" in capsys.readouterr().out
