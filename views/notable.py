from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.calculations import longest_winning_streaks, streaks
from utils.data_loader import DashboardData
from views.common import heading, metric_cards, render_chart, run_standalone_page


def _notables(data: DashboardData) -> pd.DataFrame:
    scores = data.scores.sort_values(["manager", "gameweek"]).copy()
    scores["change"] = scores.groupby("manager")["podium_points"].diff()
    weekly_avg = scores.groupby("gameweek")["podium_points"].transform("mean")
    scores["vs_average"] = scores["podium_points"] - weekly_avg
    streak = streaks(data.scores).set_index("manager")
    win_streak = longest_winning_streaks(data.scores).set_index("manager")
    rows = []
    for manager in data.managers:
        frame = scores[scores["manager"] == manager].dropna(subset=["podium_points"])
        if frame.empty:
            continue
        best = frame.loc[frame["podium_points"].idxmax()]
        worst = frame.loc[frame["podium_points"].idxmin()]
        jumps = frame.dropna(subset=["change"])
        jump = jumps.loc[jumps["change"].idxmax()] if not jumps.empty else None
        drop = jumps.loc[jumps["change"].idxmin()] if not jumps.empty else None
        position = frame.loc[frame["league_position"].idxmin()]
        rows.append({
            "manager": manager,
            "best_score": best["podium_points"], "best_gw": int(best["gameweek"]),
            "worst_score": worst["podium_points"], "worst_gw": int(worst["gameweek"]),
            "biggest_jump": jump["change"] if jump is not None else None,
            "jump_gw": int(jump["gameweek"]) if jump is not None else None,
            "biggest_drop": drop["change"] if drop is not None else None,
            "drop_gw": int(drop["gameweek"]) if drop is not None else None,
            "best_position": int(position["league_position"]), "best_position_gw": int(position["gameweek"]),
            "best_vs_avg": frame["vs_average"].max(),
            "gw_wins": int(data.stats.set_index("manager").loc[manager, "gameweek_wins"]),
            "podiums": int(data.stats.set_index("manager").loc[manager, "appearances"]),
            "longest_above": int(streak.loc[manager, "longest_above"]),
            "longest_win_streak": int(win_streak.loc[manager, "longest_winning_streak"]),
        })
    return pd.DataFrame(rows)


def _fmt(value, signed: bool = False) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{value:+.0f}" if signed else f"{value:.0f}"


def render(data: DashboardData) -> None:
    heading("Notable performances", "Highlights, standout weeks and streaks for every manager in the league.")
    if not data.completed_gameweeks:
        st.info("No fully populated Gameweeks are available yet.")
        return

    notable = _notables(data)
    manager = st.selectbox("Manager", data.managers, key="notable_manager")
    row = notable[notable["manager"] == manager]
    if row.empty:
        st.warning(f"{manager} has no valid chip-free scores yet.")
        return
    row = row.iloc[0]
    history = data.scores[data.scores["manager"] == manager].sort_values("gameweek")
    weekly_avg = data.scores.groupby("gameweek")["podium_points"].mean()
    current = history.iloc[-1]

    metric_cards([
        ("Best Gameweek", _fmt(row["best_score"]), f"GW{row['best_gw']}"),
        ("Worst Gameweek", _fmt(row["worst_score"]), f"GW{row['worst_gw']}"),
        ("Biggest jump", _fmt(row["biggest_jump"], True), f"into GW{row['jump_gw']}" if row["jump_gw"] else None),
        ("Biggest drop", _fmt(row["biggest_drop"], True), f"into GW{row['drop_gw']}" if row["drop_gw"] else None),
        ("Best league position", f"{row['best_position']}", f"GW{row['best_position_gw']}"),
        ("Current position", f"{int(current['league_position'])}", f"{current['cumulative_points']:.0f} pts"),
        ("Gameweek wins", str(row["gw_wins"]), f"{row['podiums']} podium finishes"),
        ("Longest win streak", f"{row['longest_win_streak']}", "consecutive GW wins"),
        ("Longest above-average run", f"{row['longest_above']}", "weeks in a row"),
        ("Best vs league average", _fmt(row["best_vs_avg"], True), "pts in a single GW"),
    ])

    chips = data.chips[(data.chips["manager"] == manager) & (data.chips["usage_status"] == "used")]
    if not chips.empty:
        names = {"triple_cap": "Triple Captain", "bench_boost": "Bench Boost"}
        for _, chip in chips.iterrows():
            st.success(
                f"🃏 {names.get(chip['chip_type'], chip['chip_type'])} played in GW{int(chip['gameweek'])} "
                f"for {chip['chip_bonus']:.0f} extra points."
            )

    colors = ["#00ff85" if value >= weekly_avg.loc[gw] else "#e90052"
              for gw, value in zip(history["gameweek"], history["podium_points"])]
    fig = go.Figure()
    fig.add_bar(x=history["gameweek"], y=history["podium_points"], marker_color=colors, name=manager)
    fig.add_scatter(x=weekly_avg.index, y=weekly_avg.values, mode="lines+markers", name="League average",
                    line={"color": "#04f5ff", "dash": "dash"})
    fig.update_layout(title=f"{manager}: weekly score vs league average", xaxis_title="Gameweek", yaxis_title="Points")
    fig.update_xaxes(dtick=1)
    render_chart(fig, f"notable-{manager}")

    st.markdown("#### Every manager's highlights")
    table = notable.copy()
    table["Best week"] = table.apply(lambda r: f"{r['best_score']:.0f} (GW{r['best_gw']})", axis=1)
    table["Worst week"] = table.apply(lambda r: f"{r['worst_score']:.0f} (GW{r['worst_gw']})", axis=1)
    table["Biggest jump"] = table.apply(
        lambda r: "—" if pd.isna(r["biggest_jump"]) else f"{r['biggest_jump']:+.0f} (GW{r['jump_gw']})", axis=1)
    table["Biggest drop"] = table.apply(
        lambda r: "—" if pd.isna(r["biggest_drop"]) else f"{r['biggest_drop']:+.0f} (GW{r['drop_gw']})", axis=1)
    table["Best position"] = table.apply(lambda r: f"{r['best_position']} (GW{r['best_position_gw']})", axis=1)
    table["above_weeks"] = table["manager"].map(data.stats.set_index("manager")["above_average_weeks"]).astype(int)
    display = table[[
        "manager", "Best week", "Worst week", "Biggest jump", "Biggest drop", "Best position",
        "gw_wins", "podiums", "longest_win_streak", "longest_above", "above_weeks",
    ]].rename(columns={
        "manager": "Manager", "gw_wins": "GW wins", "podiums": "Podiums",
        "longest_win_streak": "Win streak", "longest_above": "Above-avg run",
        "above_weeks": "Above-avg weeks",
    })
    st.dataframe(display, use_container_width=True, hide_index=True)
    st.caption("Scores exclude chip bonus points. Jumps and drops compare each Gameweek with the previous one.")


if __name__ == "__main__":
    run_standalone_page(render)
