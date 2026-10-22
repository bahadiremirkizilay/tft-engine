"""The simple game simulation: deterministic, keeps the pool and the rules intact."""

from tft_engine.sim import GameSim, simulate_game

from .golden_check import assert_golden


def test_same_seed_same_game(update_golden):
    game = simulate_game(3)
    assert game == simulate_game(3)
    assert_golden("sim_seed3", sim_summary(game), update_golden)


def sim_summary(game: dict) -> dict:
    """Placements and each player's last board: what the simulated policy ends up with."""
    last: dict = {}
    for rec in game["rounds"]:
        last.update(rec["players"])
    return {
        "rounds": len(game["rounds"]),
        "placements": game["placements"],
        "players": {
            pid: {
                "level": info["level"],
                "hp": info["hp"],
                "board": sorted(f"{u['name']} {u['star']}*" for u in info["board"]),
                "traits": info["traits"],
            }
            for pid, info in sorted(last.items(), key=lambda kv: str(kv[0]))
        },
    }


def test_game_ends_with_eight_distinct_placements_and_a_conserved_pool():
    sim = GameSim(seed=5)
    full = dict(sim.pool)
    result = sim.run()
    assert sorted(result["placements"].values()) == list(range(1, 9))
    held: dict[str, int] = {}
    for p in sim.players:
        for u in p.state.units:
            base = sim._base(u.unit_id)
            held[base] = held.get(base, 0) + u.copies
    for uid, n in full.items():
        assert sim.pool[uid] + held.get(uid, 0) == n, uid
    for rec in result["rounds"]:
        for info in rec["players"].values():
            assert info["gold"] >= 0 and 0 <= info["hp"] <= 100
            assert len(info["board"]) <= info["level"]
