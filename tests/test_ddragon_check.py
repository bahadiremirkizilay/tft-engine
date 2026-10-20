import importlib.util
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools" / "ddragon_check.py"
spec = importlib.util.spec_from_file_location("ddragon_check", TOOL)
ddragon_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ddragon_check)

DD = {
    "data": {
        "Maps/Shipping/Map22/Sets/TFTSetX/Shop/X_Sett": {"id": "X_Sett", "name": "Sett", "cost": 4},
        "Maps/Shipping/Map22/Sets/TFTSetX/Shop/X_Lux": {"id": "X_Lux", "name": "Lux", "cost": 5},
        "Maps/Shipping/Map22/Sets/TFTSetY/Shop/Y_Old": {"id": "Y_Old", "name": "Old", "cost": 1},
    }
}


def test_only_entries_of_the_set_are_used():
    assert set(ddragon_check.set_champions(DD, "TFTSetX")) == {"X_Sett", "X_Lux"}


def test_matching_data_has_no_differences():
    dd = ddragon_check.set_champions(DD, "TFTSetX")
    champs = {"X_Sett": {"name": "Sett", "cost": 4}, "X_Lux": {"name": "Lux", "cost": 5}}
    assert ddragon_check.compare(dd, champs) == []


def test_differences_are_reported():
    dd = ddragon_check.set_champions(DD, "TFTSetX")
    champs = {"X_Sett": {"name": "Sett", "cost": 3}, "X_New": {"name": "New", "cost": 1}}
    text = "\n".join(ddragon_check.compare(dd, champs))
    assert "X_Sett: cost 3 vs Data Dragon 4" in text
    assert "X_New (New): not in Data Dragon" in text
    assert "X_Lux (Lux): in Data Dragon, not a playable champion here" in text
