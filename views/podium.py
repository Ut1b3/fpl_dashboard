from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from views.common import heading, render_chart, run_standalone_page
from utils.data_loader import DashboardData


def render(data: DashboardData) -> None:
    heading("Podium analytics", "A separate mini-competition based on actual Gameweek scores.")
    table = data.podium_table.copy()
    table["podium_frequency_pct"] = table["appearances"] / max(1, len(data.completed_gameweeks)) * 100
    display = table.rename(columns={
        "manager": "Manager", "podium_points": "Podium points", "wins": "GW wins",
        "seconds": "Second-place shares", "thirds": "Third-place shares",
        "appearances": "Podium appearances", "podium_frequency_pct": "Podium frequency %",
    })
    st.dataframe(display.round(2), use_container_width=True, hide_index=True)
    fig = px.bar(table.sort_values("podium_points"), x="podium_points", y="manager", orientation="h",
                 color="podium_points", color_continuous_scale=["#8f6bb3", "#04f5ff"],
                 title="Total podium points")
    render_chart(fig)
    ranked = data.scores.copy()
    ranked["podium_rank"] = ranked.groupby("gameweek")["podium_points"].rank(method="min", ascending=False)
    ranked["podium_result"] = ranked["podium_rank"].map({1: "1st", 2: "2nd", 3: "3rd"})
    ranked.loc[ranked["podium_rank"] > 3, "podium_result"] = "—"
    history = ranked.pivot(index="manager", columns="gameweek", values="podium_rank")
    fig = px.imshow(history, aspect="auto", color_continuous_scale=["#00c853", "#ffd23f", "#e90052"],
                    labels={"x": "Gameweek", "y": "Manager", "color": "Actual rank"},
                    title="Gameweek-by-Gameweek podium history")
    render_chart(fig, "podium-history")
    st.caption("Tie rule: shared rank; tied managers split the points for the podium places occupied. A tie beyond third receives no podium award.")


if __name__ == "__main__":
    run_standalone_page(render)
