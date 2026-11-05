from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from views.common import heading, render_chart, run_standalone_page
from utils.chart_helpers import COLORS
from utils.data_loader import DashboardData
from utils.calculations import simulate_season


def render(data: DashboardData) -> None:
    heading("Season projections", "Illustrative estimates based on observed scores — not guaranteed outcomes.")
    latest = max(data.completed_gameweeks)
    remaining = max(0, 38 - latest)
    last_scores = data.scores[data.scores["gameweek"] == latest].set_index("manager")["cumulative_points"]
    adjusted = data.scores.pivot(index="gameweek", columns="manager", values="adjusted_gw_points").sort_index()
    projection = data.stats.set_index("manager")[["average_points"]].copy()
    projection["adjusted_average"] = data.scores.groupby("manager")["adjusted_gw_points"].mean()
    projection["current_points"] = last_scores
    projection["projected_final_points"] = projection["current_points"] + projection["adjusted_average"] * remaining
    projection["rolling_3"] = adjusted.tail(3).mean()
    projection["rolling_5"] = adjusted.tail(5).mean()
    st.caption(f"Observed through GW{latest}; {remaining} Gameweeks remain. Linear projection uses mean adjusted points per completed GW.")
    st.dataframe(projection.sort_values("projected_final_points", ascending=False).reset_index().rename(columns={
        "manager": "Manager", "current_points": "Current points", "adjusted_average": "Season adjusted avg",
        "projected_final_points": "Projected final points", "rolling_3": "Last 3 GW avg", "rolling_5": "Last 5 GW avg",
    }).round(1), use_container_width=True, hide_index=True)
    fig = px.bar(projection.reset_index(), x="manager", y="projected_final_points", color="projected_final_points",
                 color_continuous_scale=["#8f6bb3", "#00ff85"], title="Basic projected final points")
    render_chart(fig)
    with st.expander("Monte Carlo assumptions and limitations"):
        st.write(
            "The simulation resamples each manager’s observed adjusted Gameweek scores independently with replacement "
            "for every remaining week (10,000 seasons, fixed seed). This assumes future scoring resembles the short "
            "observed history and does not model fixtures, transfers, score correlations, injuries, or unknown chip use. "
            "Remaining chip effects are excluded because they cannot be estimated reliably from this workbook. "
            "With only a small sample of completed weeks, probabilities should be treated as highly uncertain."
        )
    with st.spinner("Simulating 10,000 possible finishes…"):
        simulation = simulate_season(data.scores, simulations=10_000)
    st.markdown("#### Simulated final positions")
    display = simulation.rename(columns={
        "manager": "Manager", "projected_mean": "Mean final points",
        "projected_median": "Median final points", "title_probability": "Title probability %",
        "top_three_probability": "Top-three probability %",
    }).round(1)
    st.dataframe(display, use_container_width=True, hide_index=True)
    fig = px.bar(simulation, x="manager", y=["title_probability", "top_three_probability"],
                 barmode="group", color_discrete_sequence=COLORS,
                 title="Estimated title and top-three probability")
    render_chart(fig)


if __name__ == "__main__":
    run_standalone_page(render)
