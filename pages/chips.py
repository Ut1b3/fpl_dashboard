from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from pages.common import heading, render_chart, run_standalone_page
from utils.chart_helpers import COLORS
from utils.data_loader import DashboardData


def render(data: DashboardData) -> None:
    heading("Chip analytics", "Chip deployments and adjustments are shown independently from actual weekly performance.")
    chips = data.chips.copy()
    chips["chip_label"] = chips["chip_type"].map({"triple_cap": "Triple Captain", "bench_boost": "Bench Boost"}) + " " + chips["chip_number"].astype(str)
    matrix = chips.pivot(index="manager", columns="chip_label", values="usage_status").reindex(data.managers)
    st.markdown("#### Chip usage matrix")
    styled_matrix = matrix.style.map(_status_style).set_properties(**{"color": "#ffffff"})
    st.dataframe(styled_matrix, use_container_width=True)
    st.markdown("#### Deployment and scoring details")
    details = chips[["manager", "chip_type", "chip_number", "gameweek", "actual_points", "chip_bonus", "usage_status"]].rename(columns={
        "manager": "Manager", "chip_type": "Chip", "chip_number": "Chip number",
        "gameweek": "Gameweek", "actual_points": "Recorded points",
        "chip_bonus": "Adjustment", "usage_status": "Status",
    })
    st.dataframe(details, use_container_width=True, hide_index=True)
    review = chips[chips["usage_status"].str.startswith("review")]
    if not review.empty:
        st.warning("Some chip records need administrator review. Unverified chip adjustments are not guessed.")
        st.dataframe(review[["manager", "chip_label", "gameweek", "actual_points", "usage_status"]], use_container_width=True, hide_index=True)
    used = chips[chips["usage_status"].eq("used")].dropna(subset=["gameweek"])
    if used.empty:
        st.info("No validated chip deployments have been recorded.")
    else:
        fig = px.scatter(used, x="gameweek", y="manager", color="chip_type", symbol="chip_type",
                         color_discrete_sequence=["#ff2882", "#00ff85"], hover_data=["chip_number", "actual_points"],
                         title="Validated chip deployment timeline")
        render_chart(fig)
    measured = chips.dropna(subset=["actual_points"])
    if not measured.empty:
        fig = px.box(measured, x="chip_type", y="actual_points", color="chip_type",
                     color_discrete_sequence=COLORS, points="all", title="Recorded chip point values")
        render_chart(fig)
        st.dataframe(measured.groupby("chip_type")["actual_points"].agg(
            deployments="count", average="mean", highest="max", lowest="min"
        ).reset_index().round(1), use_container_width=True, hide_index=True)
        st.caption("Recorded chip points are not automatically treated as an adjustment unless the chip scoring convention is verified.")
    unused = chips.assign(unused=chips["usage_status"].eq("unused")).groupby("manager").agg(
        unused=("unused", "sum"),
        used=("usage_status", lambda values: int((values == "used").sum())),
        review=("usage_status", lambda values: int(values.str.startswith("review").sum())),
    ).reindex(data.managers).reset_index()
    fig = px.bar(unused, x="manager", y=["unused", "used", "review"], barmode="stack",
                 color_discrete_map={"unused": "#8f6bb3", "used": "#00ff85", "review": "#ffd23f"},
                 title="Chip availability by manager")
    render_chart(fig)
    actual = data.scores.groupby("manager").agg(actual_total=("podium_points", "sum"),
                                                 adjusted_total=("adjusted_gw_points", "sum")).reset_index()
    actual = actual.melt(id_vars="manager", var_name="score_type", value_name="points")
    fig = px.bar(actual, x="manager", y="points", color="score_type", barmode="group",
                 color_discrete_sequence=["#04f5ff", "#00ff85"], title="Chip-adjusted standings impact")
    render_chart(fig)


def _status_style(value: str) -> str:
    if str(value).startswith("review"):
        return "background-color: #ffd23f; color: #37003c"
    if value == "used":
        return "background-color: #00ff85; color: #37003c"
    return "background-color: #5b2a86; color: #ffffff"


if __name__ == "__main__":
    run_standalone_page(render)
