from __future__ import annotations

import plotly.express as px
import streamlit as st

from pages.common import heading, manager_filter, render_chart, run_standalone_page
from utils.calculations import comeback_table, title_race
from utils.chart_helpers import COLORS
from utils.data_loader import DashboardData


def render(data: DashboardData) -> None:
    heading("Cumulative points and title race", "Follow adjusted points, leader gaps and the managers closing in.")
    selected = manager_filter(data, "cumulative")
    pivot, first_second = title_race(data.scores)
    left, right = st.columns(2)
    with left:
        fig = px.line(data.scores[data.scores["manager"].isin(selected)], x="gameweek", y="cumulative_points",
                      color="manager", color_discrete_sequence=COLORS, markers=True, title="Cumulative adjusted points")
        render_chart(fig)
    with right:
        gap = pivot.max(axis=1).to_frame("leader_points") - pivot
        gap = gap.reset_index().melt(id_vars="gameweek", var_name="manager", value_name="points_behind_leader")
        fig = px.line(gap[gap["manager"].isin(selected)], x="gameweek", y="points_behind_leader",
                      color="manager", color_discrete_sequence=COLORS, markers=True, title="Points behind the leader")
        render_chart(fig)
    left, right = st.columns(2)
    with left:
        render_chart(px.line(first_second, x="gameweek", y="gap", markers=True,
                             title="Gap between first and second"))
    with right:
        comeback = comeback_table(data.scores).head(8)
        st.markdown("**Points recovered against the leader**")
        st.dataframe(comeback.rename(columns={
            "manager": "Manager", "initial_deficit": "Initial deficit",
            "latest_deficit": "Latest deficit", "points_recovered": "Points recovered",
        }).round(1), use_container_width=True, hide_index=True)
    st.markdown("#### Latest position movement")
    latest = data.scores["gameweek"].max()
    board = data.scores[data.scores["gameweek"] == latest][["manager", "league_position"]].copy()
    previous = data.scores[data.scores["gameweek"] == latest - 1].set_index("manager")["league_position"] if latest > 1 else None
    board["previous_position"] = board["manager"].map(previous) if previous is not None else None
    board["movement"] = board["previous_position"] - board["league_position"] if previous is not None else 0
    st.dataframe(board.sort_values("movement", ascending=False).rename(columns={
        "manager": "Manager", "league_position": "Current position",
        "previous_position": "Previous position", "movement": "Positions gained",
    }), use_container_width=True, hide_index=True)


if __name__ == "__main__":
    run_standalone_page(render)
