from tft_engine.cli import main


def test_odds_command_prints_result_and_warns(capsys):
    code = main(
        [
            "odds",
            "--set",
            "set18",
            "--patch",
            "18.4",
            "--level",
            "8",
            "--gold",
            "50",
            "--target",
            "A:4:2",
            "--taken",
            "A:3",
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "P(success)" in out
    assert "not reviewed" in out
