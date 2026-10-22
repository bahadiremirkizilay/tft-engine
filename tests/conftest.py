from pathlib import Path

import pytest

from tft_engine.gamedata import load_gamedata

FIXTURE_SETS = Path(__file__).parent / "fixtures" / "sets"


def pytest_addoption(parser):
    parser.addoption(
        "--update-golden",
        action="store_true",
        help="rewrite tests/golden/*.json from the current results (then log it in KARARLAR)",
    )


@pytest.fixture
def update_golden(request) -> bool:
    return request.config.getoption("--update-golden")


@pytest.fixture
def synthetic():
    """Made-up game data (NOT TFT) at patch 1.2."""
    return load_gamedata("synthetic", "1.2", root=FIXTURE_SETS)


@pytest.fixture
def set18():
    return load_gamedata("set18", "18.4")
