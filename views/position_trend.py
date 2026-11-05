from __future__ import annotations

import plotly.express as px
import streamlit as st

from views.common import heading, manager_filter, render_chart, run_standalone_page
from utils.chart_helpers import COLORS
from utils.data_loader import DashboardData


def render(data: DashboardData) -> None:
    heading("Historical position trend", "Track each manager’s overall rank after every completed Gameweek.")
    selected = manager_filter(data, "position")
    frame = data.scores[data.scores["manager"].isin(selected)]
    fig = px.line(frame, x="gameweek", y="league_position", color="manager",
                  color_discrete_sequence=COLORS, markers=True,
                  hover_data={"cumulative_points": ":.0f", "league_position": True},
                  labels={"gameweek": "Gameweek", "league_position": "Overall position"},
                  title="Overall league position after each Gameweek")
    fig.update_yaxes(autorange="reversed", dtick=1, range=[len(data.managers) + .5, .5])
    fig.update_xaxes(dtick=1, tickmode="linear")
    render_chart(fig)
    st.caption("Positions are ranked from cumulative chip-adjusted points. Equal totals share a competition rank; ties are broken alphabetically only in tables.")


if __name__ == "__main__":
    run_standalone_page(render)
