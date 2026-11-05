from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from views.common import heading, render_chart, run_standalone_page
from utils.chart_helpers import COLORS
from utils.data_loader import DashboardData


def render(data: DashboardData) -> None:
    heading("Manager comparison", "Compare two or three managers across weekly and season-long metrics.")
    managers = st.multiselect("Choose two or three managers", data.managers, default=data.managers[:2], max_selections=3)
    if len(managers) < 2:
        st.info("Select at least two managers.")
        return
    stats = data.stats.set_index("manager").loc[managers].reset_index()
    st.dataframe(stats[[
        "manager", "total_points", "average_points", "median_points", "highest_gw", "lowest_gw",
        "standard_deviation", "coefficient_of_variation", "gameweek_wins", "appearances",
        "above_average_pct", "best_league_position",
    ]].rename(columns={
        "manager": "Manager", "total_points": "Total", "average_points": "Average",
        "median_points": "Median", "highest_gw": "Best GW score", "lowest_gw": "Lowest GW score",
        "standard_deviation": "Std dev", "coefficient_of_variation": "CV",
        "gameweek_wins": "GW wins", "appearances": "Podiums",
        "above_average_pct": "Above avg %", "best_league_position": "Best rank",
    }).round(2), use_container_width=True, hide_index=True)
    subset = data.scores[data.scores["manager"].isin(managers)]
    left, right = st.columns(2)
    with left:
        fig = px.line(subset, x="gameweek", y="podium_points", color="manager",
                      color_discrete_sequence=COLORS, markers=True, title="Actual weekly points")
        render_chart(fig)
    with right:
        fig = px.line(subset, x="gameweek", y="cumulative_points", color="manager",
                      color_discrete_sequence=COLORS, markers=True, title="Cumulative adjusted points")
        render_chart(fig)
    left, right = st.columns(2)
    with left:
        fig = px.bar(stats, x="manager", y="average_points", color="manager",
                     color_discrete_sequence=COLORS, title="Average points")
        render_chart(fig)
    with right:
        dimensions = {
            "Average points": stats["average_points"].to_numpy(dtype=float),
            "Consistency": -stats["coefficient_of_variation"].fillna(0).to_numpy(dtype=float),
            "GW wins": stats["gameweek_wins"].to_numpy(dtype=float),
            "Podium finishes": stats["appearances"].to_numpy(dtype=float),
            "Above-average frequency": stats["above_average_pct"].to_numpy(dtype=float),
        }
        radar = go.Figure()
        for _, row in stats.iterrows():
            idx = stats.index.get_loc(row.name)
            raw = [values[idx] for values in dimensions.values()]
            normalized = []
            for value, key in zip(raw, dimensions):
                values = dimensions[key]
                if key == "Consistency":
                    normalized.append(100.0 if np.ptp(values) == 0 else (value - values.min()) / np.ptp(values) * 100)
                else:
                    normalized.append(0.0 if np.max(values) == 0 else value / np.max(values) * 100)
            radar.add_trace(go.Scatterpolar(r=normalized + [normalized[0]], theta=list(dimensions) + [list(dimensions)[0]],
                                            fill="toself", name=row["manager"]))
        radar.update_layout(title="Normalised comparison (0–100)")
        render_chart(radar)
    fig = px.bar(subset, x="gameweek", y="podium_points", color="manager", barmode="group",
                 color_discrete_sequence=COLORS, title="Gameweek-by-Gameweek score comparison")
    render_chart(fig)


if __name__ == "__main__":
    run_standalone_page(render)
