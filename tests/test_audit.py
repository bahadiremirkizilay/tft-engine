"""The project audit: each check finds what it should, and the repo itself passes."""

import json
import textwrap
from pathlib import Path

import pytest

from tft_engine.audit import AuditConfig, load_config, run_audit
from tft_engine.audit.core import REPO_ROOT, Finding, apply_config
from tft_engine.audit.wiring import connections

BASE = {
    "set": "toy",
    "valid_from_patch": "1.1",
    "params": {
        "star_multipliers": {"value": {"hp": [1, 1.8, 3.24]}},
        "used_param": {"value": 1},
        "unused_param": {"value": 2},
    },
    "shop_rules": {},
}


def make_repo(tmp_path: Path, files: dict[str, str]) -> Path:
    """A tiny repo with one set and the given source files (paths under the package)."""
    sets = tmp_path / "data" / "sets" / "toy"
    sets.mkdir(parents=True)
    (sets / "base.json").write_text(json.dumps(BASE), encoding="utf-8")
    (sets / "curated" / "loaded_thing").mkdir(parents=True)
    (sets / "curated" / "orphan_thing").mkdir(parents=True)
    (tmp_path / "tools").mkdir()
    (tmp_path / "docs").mkdir()
    pkg = tmp_path / "src" / "tft_engine"
    files = {
        "__init__.py": "",
        "cli.py": "from tft_engine import used\n",
        "used.py": "X = 'used_param'\nPATH = 'curated/loaded_thing/'\n",
        **files,
    }
    for rel, text in files.items():
        path = pkg / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(text), encoding="utf-8")
    return tmp_path


def keys(findings: list[Finding], check: str | None = None) -> set[str]:
    return {f.key for f in findings if check is None or f.check == check}


def test_repo_passes_its_own_audit():
    findings = run_audit()
    errors = [f.line() for f in findings if f.level == "error"]
    assert errors == []


def test_audit_config_entries_are_well_formed():
    config = load_config()
    assert config.accept, "audit.toml should load"
    for entry in config.accept.values():
        assert entry["reason"].strip()


def test_copy_of_a_data_table_is_an_error(tmp_path):
    root = make_repo(tmp_path, {"sim.py": "STAR_POWER = {1: 1.0, 2: 1.8, 3: 3.24}\n"})
    found = run_audit(root, only=["constants"], config=AuditConfig())
    f = next(f for f in found if f.key == "sim.py:STAR_POWER")
    assert "star_multipliers.hp" in f.message and f.level == "error"


def test_same_table_in_two_modules_is_reported(tmp_path):
    root = make_repo(
        tmp_path,
        {"a.py": "COPIES = {1: 1, 2: 3, 3: 9}\n", "b.py": "STAR = {1: 1, 2: 3, 3: 9}\n"},
    )
    found = run_audit(root, only=["constants"], config=AuditConfig())
    f = next(f for f in found if f.key == "b.py:STAR")
    assert "a.py:COPIES" in f.message


def test_inline_decimals_are_reported_but_tolerances_are_not(tmp_path):
    src = """
    def policy(x):
        return x * 0.35

    def close(a, b):
        return abs(a - b) < 1e-9 and a * 1.0 == b
    """
    root = make_repo(tmp_path, {"p.py": src})
    found = keys(run_audit(root, only=["constants"], config=AuditConfig()))
    assert "p.py:policy()" in found
    assert "p.py:close()" not in found


def test_tuple_assignment_is_scanned(tmp_path):
    root = make_repo(tmp_path, {"t.py": "LOW, HIGH = 0.5, 2.0\n"})
    found = keys(run_audit(root, only=["constants"], config=AuditConfig()))
    assert {"t.py:LOW", "t.py:HIGH"} <= found


def test_rule_tables_inside_functions_are_found_but_counters_are_not(tmp_path):
    src = """
    COPIES = {1: 1, 2: 3, 3: 9}

    def give_back(star):
        return {1: 1, 2: 3, 3: 9}[star]

    def count():
        order = {"a": 0, "b": 1, "c": 2}
        return [0, 0, 0], order
    """
    root = make_repo(tmp_path, {"g.py": src})
    found = run_audit(root, only=["constants"], config=AuditConfig())
    f = next(f for f in found if f.key == "g.py:give_back():table")
    assert "g.py:COPIES" in f.message
    assert "g.py:count():table" not in keys(found)


def test_strings_and_paths_are_not_numbers(tmp_path):
    root = make_repo(tmp_path, {"q.py": "NAMES = ('a', 'b')\nROOT = Path(__file__).parents[3]\n"})
    found = keys(run_audit(root, only=["constants"], config=AuditConfig()))
    assert not {"q.py:NAMES", "q.py:ROOT"} & found


def test_network_and_unseeded_randomness_are_layer_errors(tmp_path):
    files = {
        "rules/__init__.py": "",
        "rules/net.py": "import urllib.request\n",
        "decision/__init__.py": "",
        "decision/rand.py": "import numpy as np\nrng = np.random.default_rng()\n",
        "decision/rand2.py": "import random\n",
        "repro/__init__.py": "",
        "repro/seeds.py": "import numpy as np\nG = np.random.Generator(np.random.PCG64(1))\n",
    }
    root = make_repo(tmp_path, files)
    found = keys(run_audit(root, only=["layers"], config=AuditConfig()))
    assert "rules/net.py:import urllib.request" in found
    assert "decision/rand.py:np.random.default_rng" in found
    assert "decision/rand2.py:import random" in found
    assert not any(k.startswith("repro/") for k in found)


def test_wiring_finds_unused_params_files_and_modules(tmp_path):
    root = make_repo(tmp_path, {"lonely.py": "def f():\n    return 1\n"})
    found = keys(run_audit(root, only=["wiring"], config=AuditConfig()))
    assert "param:unused_param" in found
    assert "param:used_param" not in found
    assert "curated:orphan_thing" in found
    assert "curated:loaded_thing" not in found
    assert "module:tft_engine.lonely" in found
    assert "module:tft_engine.used" not in found


def test_a_module_used_by_a_tool_is_reachable(tmp_path):
    root = make_repo(tmp_path, {"importer.py": ""})
    (root / "tools" / "imp.py").write_text("from tft_engine.importer import x\n", encoding="utf-8")
    found = keys(run_audit(root, only=["wiring"], config=AuditConfig()))
    assert "module:tft_engine.importer" not in found


def test_every_assumption_is_used_in_the_repo():
    found = keys(run_audit(only=["wiring"]))
    assert not any(k.startswith("assumption:") for k in found)


def test_docs_links_must_exist(tmp_path):
    root = make_repo(tmp_path, {})
    (root / "docs" / "A.md").write_text("[ok](A.md) [bad](MISSING.md)", encoding="utf-8")
    (root / "CLAUDE.md").write_text("see `src/tft_engine/nope.py` and `data/<set>/x`", "utf-8")
    found = keys(run_audit(root, only=["docs"], config=AuditConfig()))
    assert "docs/A.md->MISSING.md" in found
    assert "docs/A.md->A.md" not in found
    assert "CLAUDE.md->src/tft_engine/nope.py" in found
    assert not any("<set>" in k for k in found)


def test_accept_list_downgrades_and_reports_stale_entries():
    config = AuditConfig(
        accept={
            "a": {"kind": "debt", "reason": "later"},
            "b": {"kind": "technical", "reason": "hash"},
            "gone": {"kind": "debt", "reason": "fixed already"},
        }
    )
    found = apply_config([Finding("x", "a", "m"), Finding("x", "b", "m")], config)
    levels = {f.key: f.level for f in found}
    assert levels == {"a": "debt", "b": "accepted", "gone": "warning"}


def test_accept_entries_need_a_reason(tmp_path):
    (tmp_path / "audit.toml").write_text('[[accept]]\nkey = "k"\nkind = "debt"\n', "utf-8")
    with pytest.raises(ValueError, match="reason"):
        load_config(tmp_path)


def test_connections_map_lists_readers():
    conn = connections(REPO_ROOT)
    assert conn["params"]["reroll_cost"]
    assert "gamedata/curated.py" in conn["curated"]["overrides"]
    assert "tft_engine.cli" in conn["modules"]["tft_engine.audit.core"] or any(
        "cli" in m for m in conn["modules"]["tft_engine.audit"]
    )
    assert conn["assumptions"]["horizon_rounds"]


def test_new_assumptions_need_a_basis():
    strict = AuditConfig(accept={}, extra={"assumptions": {"legacy_without_basis": []}})
    found = keys(run_audit(only=["wiring"], config=strict))
    assert "assumption:horizon_rounds:basis" in found  # legacy, no basis yet
    assert "assumption:wisp_shop_prob:basis" not in found  # has one


def test_generated_docs_are_current():
    found = keys(run_audit(only=["docs"]))
    assert "docs/VARSAYIMLAR.md:generated" not in found
    assert "docs/BAGLANTILAR.md:generated" not in found
