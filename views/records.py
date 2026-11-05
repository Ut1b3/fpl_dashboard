from __future__ import annotations

import pandas as pd
import streamlit as st

from views.common import heading, run_standalone_page
from utils.calculations import comeback_table, longest_winning_streaks, streaks
from utils.data_loader import DashboardData


def render(data: DashboardData) -> None:
    heading("Records and achievements", "Competition records update automatically as new Gameweeks are added.")
    scores = data.scores
    high = scores.loc[scores["podium_points"].idxmax()]
    low = scores.loc[scores["podium_points"].idxmin()]
    current = scores[scores["gameweek"] == max(data.completed_gameweeks)].sort_values("cumulative_points", ascending=False).iloc[0]
    consistency = data.stats.sort_values("coefficient_of_variation")
    volatility = data.stats.sort_values("coefficient_of_variation", ascending=False)
    streak = streaks(scores)
    winning_streak = longest_winning_streaks(scores)
    comeback = comeback_table(scores)
    records = [
        ("Highest single-GW score", f"{high['manager']} · {high['podium_points']:.0f} (GW{int(high['gameweek'])})"),
        ("Lowest single-GW score", f"{low['manager']} · {low['podium_points']:.0f} (GW{int(low['gameweek'])})"),
        ("Highest cumulative total", f"{current['manager']} · {current['cumulative_points']:.0f} pts"),
        ("Most Gameweek wins", _record_holder(data.stats, "gameweek_wins", "wins")),
        ("Most podium appearances", _record_holder(data.podium_table, "appearances", "podiums")),
        ("Most consistent", f"{consistency.iloc[0]['manager']} · lowest CV"),
        ("Most volatile", f"{volatility.iloc[0]['manager']} · highest CV"),
        ("Longest above-average run", _streak_holder(streak, "longest_above", "weeks")),
        ("Most above-average weeks", _record_holder(data.stats, "above_average_weeks", "weeks")),
        ("Longest time in 1st place", _longest_run(scores, "first")),
        ("Longest time in last place", _longest_run(scores, "last")),
        ("Longest winning streak", _record_holder(winning_streak, "longest_winning_streak", "GWs")),
        ("Biggest improvement between GWs", _biggest_improvement(scores)),
        ("Biggest drop between GWs", _biggest_drop(scores)),
        ("Biggest points comeback", f"{comeback.iloc[0]['manager']} · recovered {comeback.iloc[0]['points_recovered']:.0f} pts"),
        ("Largest first-second gap", f"{_max_first_second_gap(scores):.0f} pts"),
        ("Most GWs in weekly top 3", _top_n_record(scores, "podium_points", 3, "count")),
        ("Most consecutive GWs in weekly top 3", _top_n_record(scores, "podium_points", 3, "run")),
        ("Most GWs in cumulative top 3", _top_n_record(scores, "cumulative_points", 3, "count")),
        ("Most consecutive GWs in cumulative top 3", _top_n_record(scores, "cumulative_points", 3, "run")),
        ("Most GWs in cumulative 1st place", _top_n_record(scores, "cumulative_points", 1, "count")),
    ]
    st.dataframe(pd.DataFrame(records, columns=["Record", "Holder"]), use_container_width=True, hide_index=True)
    st.markdown("#### Manager achievements")
    achievements = []
    for _, row in data.stats.iterrows():
        name = row["manager"]
        if row["coefficient_of_variation"] == consistency.iloc[0]["coefficient_of_variation"]:
            achievements.append((name, "The Consistent One"))
        if name == comeback.iloc[0]["manager"]:
            achievements.append((name, "The Comeback King/Queen"))
        if row["gameweek_wins"] == data.stats["gameweek_wins"].max():
            achievements.append((name, "The GW Specialist"))
        if row["coefficient_of_variation"] == volatility.iloc[0]["coefficient_of_variation"]:
            achievements.append((name, "The Most Volatile"))
        if row["appearances"] == data.stats["appearances"].max():
            achievements.append((name, "The Podium Specialist"))
    for label, column, n, mode in [
        ("Most GWs in Weekly Top 3", "podium_points", 3, "count"),
        ("Longest Weekly Top 3 Run", "podium_points", 3, "run"),
        ("Most GWs in Cumulative Top 3", "cumulative_points", 3, "count"),
        ("Longest Cumulative Top 3 Run", "cumulative_points", 3, "run"),
        ("Most GWs in Cumulative 1st Place", "cumulative_points", 1, "count"),
    ]:
        values = _top_n_values(scores, column, n, mode)
        if values.max() > 0:
            achievements.extend((name, label) for name in values[values == values.max()].index)
    st.dataframe(pd.DataFrame(achievements, columns=["Manager", "Achievement"]), use_container_width=True, hide_index=True)


def _top_n_values(scores: pd.DataFrame, column: str, n: int, mode: str) -> pd.Series:
    ranked = scores.sort_values(["manager", "gameweek"]).copy()
    ranked["in_top"] = ranked.groupby("gameweek")[column].rank(method="min", ascending=False) <= n
    if mode == "count":
        return ranked.groupby("manager")["in_top"].sum().astype(int)

    def longest(flags: pd.Series) -> int:
        best = run = 0
        for flag in flags:
            run = run + 1 if flag else 0
            best = max(best, run)
        return best

    return ranked.groupby("manager")["in_top"].apply(longest)


def _top_n_record(scores: pd.DataFrame, column: str, n: int, mode: str) -> str:
    values = _top_n_values(scores, column, n, mode)
    best = values.max()
    if best == 0:
        return "—"
    return f"{', '.join(values[values == best].index)} · {best} GWs"


def _record_holder(frame, column: str, suffix: str) -> str:
    highest = frame[column].max()
    names = ", ".join(frame.loc[frame[column] == highest, "manager"].tolist())
    return f"{names} · {highest:g} {suffix}"


def _streak_holder(frame, column: str, suffix: str) -> str:
    highest = frame[column].max()
    names = ", ".join(frame.loc[frame[column] == highest, "manager"].tolist())
    return f"{names} · {highest} {suffix}"


def _biggest_improvement(scores: pd.DataFrame) -> str:
    ordered = scores.sort_values(["manager", "gameweek"]).copy()
    ordered["change"] = ordered.groupby("manager")["podium_points"].diff()
    row = ordered.loc[ordered["change"].idxmax()]
    return f"{row['manager']} · +{row['change']:.0f} pts (GW{int(row['gameweek'])})"


def _biggest_drop(scores: pd.DataFrame) -> str:
    ordered = scores.sort_values(["manager", "gameweek"]).copy()
    ordered["change"] = ordered.groupby("manager")["podium_points"].diff()
    row = ordered.loc[ordered["change"].idxmin()]
    return f"{row['manager']} · {row['change']:.0f} pts (GW{int(row['gameweek'])})"


def _longest_run(scores: pd.DataFrame, place: str) -> str:
    best_length, holders = 0, []
    for manager, frame in scores.sort_values("gameweek").groupby("manager"):
        run = longest = 0
        start = best_start = None
        for _, row in frame.iterrows():
            week_scores = scores[scores["gameweek"] == row["gameweek"]]["cumulative_points"]
            target = week_scores.max() if place == "first" else week_scores.min()
            if row["cumulative_points"] == target:
                run += 1
                start = row["gameweek"] if run == 1 else start
                if run > longest:
                    longest, best_start = run, start
            else:
                run = 0
        if longest and longest >= best_length:
            if longest > best_length:
                holders = []
            best_length = longest
            holders.append(f"{manager} (GW{int(best_start)}–GW{int(best_start) + longest - 1})")
    if not holders:
        return "—"
    return f"{', '.join(holders)} · {best_length} weeks"


def _max_first_second_gap(scores: pd.DataFrame) -> float:
    gaps = []
    for _, group in scores.groupby("gameweek"):
        totals = group["cumulative_points"].nlargest(2).tolist()
        if len(totals) > 1:
            gaps.append(totals[0] - totals[1])
    return max(gaps, default=0.0)


if __name__ == "__main__":
    run_standalone_page(render)
