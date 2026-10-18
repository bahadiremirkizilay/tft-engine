from pathlib import Path

import pytest

from tft_engine.gamedata import load_gamedata

FIXTURE_SETS = Path(__file__).parent / "fixtures" / "sets"


@pytest.fixture
def synthetic():
    """Made-up game data (NOT TFT) at patch 1.2."""
    return load_gamedata("synthetic", "1.2", root=FIXTURE_SETS)


@pytest.fixture
def set18():
    return load_gamedata("set18", "18.4")
