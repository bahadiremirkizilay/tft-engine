import pytest

from tft_engine.gamedata.hashes import HashResolver, hash_key, is_hashed, placeholders


def test_hash_matches_values_seen_in_set18_game_files():
    # cdragon-16.20, trait DA_18_Brawler: description uses these two names
    assert hash_key("BrawlerTeamHealth") == "{da2472a7}"
    assert hash_key("BrawlerHealthPercent") == "{f1ed73eb}"
    assert hash_key("brawlerteamhealth") == hash_key("BrawlerTeamHealth")  # case-insensitive


def test_placeholders_include_scaled_ones():
    text = "Gain @BrawlerTeamHealth@ Health. @BrawlerHealthPercent*100@% more. @Gold@ gold"
    assert placeholders(text) == ["BrawlerHealthPercent", "BrawlerTeamHealth", "Gold"]


def test_resolver_only_names_what_a_candidate_proves():
    r = HashResolver()
    r.add_candidates(["BrawlerTeamHealth"])
    mapping, unresolved = r.resolve_mapping({"{da2472a7}": 120, "{f1ed73eb}": 0.25, "Gold": 2})
    assert mapping == {"BrawlerTeamHealth": 120, "{f1ed73eb}": 0.25, "Gold": 2}
    assert unresolved == ["{f1ed73eb}"]
    assert is_hashed("{f1ed73eb}") and not is_hashed("Gold")


def test_known_names_must_hash_correctly():
    with pytest.raises(ValueError):
        HashResolver({"{00000000}": "BrawlerTeamHealth"})
