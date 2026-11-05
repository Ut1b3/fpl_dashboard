from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from views.common import heading, metric_cards, render_chart, run_standalone_page
from utils.calculations import leaderboard
from utils.chart_helpers import COLORS
from utils.data_loader import DashboardData


def render(data: DashboardData) -> None:
    heading("League overview", "The season at a glance — standings, form and the latest Gameweek.")
    if not data.completed_gameweeks:
        st.info("No fully populated Gameweeks are available yet.")
        return
    latest = max(data.completed_gameweeks)
    board = leaderboard(data.scores)
    top = board.iloc[0]
    second = board.iloc[1] if len(board) > 1 else None
    latest_week = data.scores[data.scores["gameweek"] == latest]
    winner = latest_week.sort_values(["podium_points", "manager"], ascending=[False, True]).iloc[0]
    winner_score = float(winner["podium_points"])
    weekly_average = float(latest_week["podium_points"].mean())
    movement = board.dropna(subset=["movement"])
    riser = movement.sort_values("movement", ascending=False).iloc[0] if not movement.empty else None
    faller = movement.sort_values("movement", ascending=True).iloc[0] if not movement.empty else None
    metric_cards([
        ("League leader", str(top["manager"]), f"{top['cumulative_points']:.0f} pts"),
        ("Second place", str(second["manager"]) if second is not None else "—", None),
        ("Points gap", f"{top['cumulative_points'] - second['cumulative_points']:.0f}" if second is not None else "—", "leader advantage"),
        ("Completed GWs", str(len(data.completed_gameweeks)), f"latest GW{latest}"),
        ("Managers", str(len(data.managers)), None),
        ("Latest GW winner", str(winner["manager"]), f"{winner_score:.0f} pts · GW{latest}"),
        ("League average", f"{data.scores['podium_points'].mean():.1f}", "actual GW points"),
        ("Highest GW score", f"{data.scores['podium_points'].max():.0f}", "chip-free points"),
        ("Biggest riser", str(riser["manager"]) if riser is not None and riser["movement"] > 0 else "—",
         f"+{int(riser['movement'])} places" if riser is not None and riser["movement"] > 0 else None),
        ("Biggest faller", str(faller["manager"]) if faller is not None and faller["movement"] < 0 else "—",
         f"{int(faller['movement'])} places" if faller is not None and faller["movement"] < 0 else None),
    ])
    podium = board.head(3)
    podium_columns = st.columns(3)
    for column, (_, row) in zip(podium_columns, podium.iterrows()):
        column.markdown(
            f'<div class="page-subtitle">TOP {int(row["league_position"])}</div>'
            f'<div style="font-size:1.35rem;font-weight:700;            color:#00ff85">{row["manager"]}</div>'
                        f'<div style="color:#ffffff">{row["cumulative_points"]:.0f} points</div>',
            unsafe_allow_html=True,
        )
    st.markdown("#### Current standings")
    shown = board.merge(data.stats[["manager", "average_points"]], on="manager")
    shown = shown[[
        "league_position", "manager", "cumulative_points", "average_points",
        "adjusted_gw_points", "points_behind_leader", "movement",
    ]]
    shown.columns = ["Rank", "Manager", "Total points", "Average points", "Latest GW", "Behind leader", "Movement"]
    styled = shown.style.map(_movement_style, subset=["Movement"]).format({"Movement": lambda v: "" if pd.isna(v) else f"{int(v):+d}"})
    st.dataframe(styled, use_container_width=True, hide_index=True)
    csv = shown.to_csv(index=False).encode("utf-8")
    st.download_button("Download standings CSV", csv, "fpl_leaderboard.csv", "text/csv")
    st.markdown("#### Title race")
    left, right = st.columns(2)
    with left:
        fig = px.line(data.scores, x="gameweek", y="league_position", color="manager", color_discrete_sequence=COLORS,
                      markers=True, hover_data=["cumulative_points"], title="Historical overall league position")
        fig.update_yaxes(autorange="reversed", dtick=1, title="League position")
        render_chart(fig)
    with right:
        fig = px.line(data.scores, x="gameweek", y="cumulative_points", color="manager",
                      color_discrete_sequence=COLORS, markers=True, title="Cumulative adjusted points")
        render_chart(fig)
    st.markdown(f"#### GW{latest} snapshot")
    high, low = latest_week["podium_points"].max(), latest_week["podium_points"].min()
    st.caption(f"Average {weekly_average:.1f} · high {high:.0f} · low {low:.0f} · league rank ties share the same position.")


def _movement_style(value) -> str:
    if pd.isna(value) or value == 0:
        return ""
    if value > 0:
        return "background-color: #00ff85; color: #37003c; font-weight: 700"
    return "background-color: #e90052; color: #ffffff; font-weight: 700"


if __name__ == "__main__":
    run_standalone_page(render)
