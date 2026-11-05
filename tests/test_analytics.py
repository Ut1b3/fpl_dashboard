from pathlib import Path

import pandas as pd

from utils.calculations import comeback_table, gameweek_leaderboard, longest_winning_streaks, simulate_season
from utils.data_loader import _build_podium_table, load_dashboard_data


def test_comeback_table_computes_points_recovered():
    scores = pd.DataFrame([
        {"manager": "A", "gameweek": 1, "cumulative_points": 60},
        {"manager": "B", "gameweek": 1, "cumulative_points": 40},
        {"manager": "A", "gameweek": 2, "cumulative_points": 100},
        {"manager": "B", "gameweek": 2, "cumulative_points": 110},
    ])

    result = comeback_table(scores).set_index("manager")

    assert not result.isna().any().any()
    assert result.loc["B", "initial_deficit"] == 20
    assert result.loc["B", "latest_deficit"] == 0
    assert result.loc["B", "points_recovered"] == 20
    assert result.loc["A", "points_recovered"] == -10
    assert result.loc["B", "previous_deficit"] == 20
    assert result.loc["B", "total_recovered"] == 20


ROOT = Path(__file__).resolve().parents[1]


def test_supplied_workbooks_load_and_reconcile():
    data = load_dashboard_data(ROOT / "data" / "FPL Points.xlsx", ROOT / "data" / "FPL Chips.xlsx")

    assert len(data.managers) == 14
    assert data.completed_gameweeks == list(range(1, 10))
    assert not data.validation
    utibe_gw7 = data.scores.query("manager == 'Utibe' and gameweek == 7").iloc[0]
    assert utibe_gw7["adjusted_gw_points"] == 73
    assert utibe_gw7["podium_points"] + utibe_gw7["chip_bonus"] == 73
    assert data.scores["gameweek"].max() == 9
    assert data.scores.groupby("manager")["adjusted_gw_points"].sum().max() == 606


def test_tied_podium_places_split_award_points():
    scores = pd.DataFrame([
        {"manager": "A", "gameweek": 1, "podium_points": 80},
        {"manager": "B", "gameweek": 1, "podium_points": 80},
        {"manager": "C", "gameweek": 1, "podium_points": 70},
        {"manager": "D", "gameweek": 1, "podium_points": 60},
    ])
    podium = _build_podium_table(scores, ["A", "B", "C", "D"]).set_index("manager")

    assert podium.loc["A", "podium_points"] == 2.5
    assert podium.loc["B", "podium_points"] == 2.5
    assert podium.loc["C", "podium_points"] == 1
    assert podium.loc["D", "appearances"] == 0


def test_winning_streaks_break_on_non_wins():
    scores = pd.DataFrame([
        {"manager": "A", "gameweek": 1, "podium_points": 90},
        {"manager": "A", "gameweek": 2, "podium_points": 80},
        {"manager": "A", "gameweek": 3, "podium_points": 95},
        {"manager": "B", "gameweek": 1, "podium_points": 70},
        {"manager": "B", "gameweek": 2, "podium_points": 85},
        {"manager": "B", "gameweek": 3, "podium_points": 70},
    ])
    streaks = longest_winning_streaks(scores).set_index("manager")

    assert streaks.loc["A", "longest_winning_streak"] == 1
    assert streaks.loc["B", "longest_winning_streak"] == 1


def test_simulation_has_probabilities_summing_to_one():
    scores = pd.DataFrame([
        {"manager": manager, "gameweek": week, "adjusted_gw_points": points, "cumulative_points": points * week}
        for manager, base in [("A", 60), ("B", 55)]
        for week, points in [(1, base), (2, base + 2)]
    ])
    result = simulate_season(scores, simulations=500, seed=7)

    assert abs(result["title_probability"].sum() - 100) < 1e-9
    assert (result["top_three_probability"] == 100).all()


def test_simulated_tied_title_is_shared():
    scores = pd.DataFrame([
        {"manager": manager, "gameweek": 38, "adjusted_gw_points": 50, "cumulative_points": 100}
        for manager in ["A", "B"]
    ])
    result = simulate_season(scores, simulations=20, seed=3).set_index("manager")

    assert result.loc["A", "title_probability"] == 50
    assert result.loc["B", "title_probability"] == 50


def _load_with_chips(tmp_path, monkeypatch, points, chips):
    points_path = tmp_path / "points.xlsx"
    chips_path = tmp_path / "chips.xlsx"
    points_path.touch()
    chips_path.touch()
    monkeypatch.setattr(pd, "read_excel", lambda path, engine=None: points if "points.xlsx" in str(path) else chips)
    return load_dashboard_data(points_path, chips_path)


def _chip_frame(**overrides):
    base = {
        "Manager": ["A", "B"],
        "Triple Cap 1 Used": ["N/A", "N/A"],
        "Triple Cap GW Actual Points": ["N/A", "N/A"],
        "Bench Boost 1 Used": ["N/A", "N/A"],
        "Bench Boost 1 Points": ["N/A", "N/A"],
        "Triple Cap 2 Used": ["N/A", "N/A"],
        "Triple Cap 2 Points": ["N/A", "N/A"],
        "Bench Boost 2 Used": ["N/A", "N/A"],
        "Bench Boost 2 Points": ["N/A", "N/A"],
    }
    base.update(overrides)
    return pd.DataFrame(base)


def test_chip_points_are_extra_points_excluded_from_podium(tmp_path, monkeypatch):
    points = pd.DataFrame({"Manager": ["A", "B"], "GW 1": [75, 60], "GW 2": [70, 50], "Total": [145, 110]})
    chips = _chip_frame(**{
        "Triple Cap 1 Used": ["GW1", "N/A"], "Triple Cap GW Actual Points": [25, "N/A"],
        "Bench Boost 1 Used": ["GW2", "N/A"], "Bench Boost 1 Points": [8, "N/A"],
    })

    data = _load_with_chips(tmp_path, monkeypatch, points, chips)

    assert not data.validation
    gw1 = data.scores.query("manager == 'A' and gameweek == 1").iloc[0]
    assert (gw1["podium_points"], gw1["chip_bonus"], gw1["adjusted_gw_points"]) == (50, 25, 75)
    gw2 = data.scores.query("manager == 'A' and gameweek == 2").iloc[0]
    assert (gw2["podium_points"], gw2["chip_bonus"], gw2["adjusted_gw_points"]) == (62, 8, 70)
    assert data.scores.query("manager == 'A'")["cumulative_points"].max() == 145


def test_missing_chip_points_are_flagged(tmp_path, monkeypatch):
    points = pd.DataFrame({"Manager": ["A", "B"], "GW 1": [50, 60], "Total": [50, 60]})
    chips = _chip_frame(**{"Bench Boost 1 Used": ["GW1", "N/A"], "Bench Boost 1 Points": ["N/A", "N/A"]})

    data = _load_with_chips(tmp_path, monkeypatch, points, chips)

    assert any("missing its extra chip points" in notice for notice in data.validation)
    unresolved = data.scores.query("manager == 'A' and gameweek == 1").iloc[0]
    assert pd.isna(unresolved["podium_points"])
    assert unresolved["adjusted_gw_points"] == 50

