from __future__ import annotations

import plotly.express as px
import streamlit as st

from views.common import heading, metric_cards, render_chart, run_standalone_page, selected_week
from utils.calculations import gameweek_leaderboard
from utils.chart_helpers import COLORS
from utils.data_loader import DashboardData


def render(data: DashboardData) -> None:
    heading("Gameweek centre", "Weekly results use chip-free scores; chip-adjusted totals remain separate.")
    week = selected_week(data, "centre_week")
    frame = gameweek_leaderboard(data.scores, week)
    if frame.empty:
        st.info("No score data for this Gameweek.")
        return
    leader = frame.iloc[0]
    median = frame["podium_points"].median()
    metric_cards([
        ("Gameweek winner", leader["manager"], f"{leader['podium_points']:.0f} actual pts"),
        ("Highest score", f"{frame['podium_points'].max():.0f}", None),
        ("Lowest score", f"{frame['podium_points'].min():.0f}", None),
        ("League average", f"{frame['podium_points'].mean():.1f}", None),
        ("League median", f"{median:.1f}", None),
    ])
    display = frame[["podium_rank", "manager", "podium_points", "chip_bonus", "adjusted_gw_points"]].copy()
    display.columns = ["Rank", "Manager", "Podium points", "Chip bonus", "Adjusted GW points"]
    st.dataframe(display, use_container_width=True, hide_index=True)
    left, right = st.columns(2)
    with left:
        fig = px.bar(frame.sort_values("podium_points"), x="podium_points", y="manager", orientation="h",
                     color="podium_points", color_continuous_scale=["#e90052", "#00ff85"],
                     title=f"GW{week} actual score leaderboard")
        fig.add_vline(x=frame["podium_points"].mean(), line_dash="dash", line_color="#04f5ff",
                      annotation_text=f"Avg {frame['podium_points'].mean():.1f}")
        render_chart(fig)
    with right:
        render_chart(px.histogram(frame, x="podium_points", nbins=8, title="Score distribution"))
    if week > 1:
        previous = data.scores[data.scores["gameweek"] == week - 1][["manager", "podium_points"]]
        compare = frame[["manager", "podium_points"]].merge(previous, on="manager", suffixes=(f"_gw{week}", f"_gw{week-1}"))
        compare["change"] = compare[f"podium_points_gw{week}"] - compare[f"podium_points_gw{week-1}"]
        st.markdown("#### Change from previous Gameweek")
        st.dataframe(compare.sort_values("change", ascending=False).rename(columns={
            "manager": "Manager", f"podium_points_gw{week}": f"GW{week}",
            f"podium_points_gw{week-1}": f"GW{week-1}", "change": "Score change",
        }), use_container_width=True, hide_index=True)
    st.markdown("#### Gameweek winners")
    winners = []
    for completed_week, group in data.scores.groupby("gameweek"):
        high = group["podium_points"].max()
        names = ", ".join(sorted(group.loc[group["podium_points"] == high, "manager"]))
        winners.append({"Gameweek": int(completed_week), "Winner(s)": names, "Winning score": high})
    st.dataframe(winners, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    run_standalone_page(render)
