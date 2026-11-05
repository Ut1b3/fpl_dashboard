from __future__ import annotations

import html
from pathlib import Path

import pandas as pd
import streamlit as st

from utils.calculations import gameweek_leaderboard, leaderboard
from utils.chart_helpers import style_figure
from utils.data_loader import DashboardData, load_dashboard_data


def heading(title: str, subtitle: str) -> None:
    st.markdown(f'<div class="page-title">{title}</div><div class="page-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def metric_cards(items: list[tuple[str, str, str | None]]) -> None:
    per_row = 5
    for start in range(0, len(items), per_row):
        chunk = items[start:start + per_row]
        cols = st.columns(per_row)
        for column, (label, value, delta) in zip(cols, chunk):
            delta_html = f'<div class="kpi-delta">{html.escape(delta)}</div>' if delta else ""
            column.markdown(
                f'<div class="kpi-card"><div class="kpi-label">{html.escape(label)}</div>'
                f'<div class="kpi-value">{html.escape(value)}</div>{delta_html}</div>',
                unsafe_allow_html=True,
            )


def render_chart(fig, key: str | None = None) -> None:
    st.plotly_chart(style_figure(fig), use_container_width=True, config={"displaylogo": False, "responsive": True}, key=key)


def manager_filter(data: DashboardData, key: str, default_count: int = 5) -> list[str]:
    choice = st.radio(
        "Managers",
        ["All managers", "Top five", "Choose managers"],
        horizontal=True,
        key=f"{key}_mode",
        label_visibility="collapsed",
    )
    if choice == "All managers":
        return data.managers
    if choice == "Top five":
        latest = leaderboard(data.scores)
        return latest.head(default_count)["manager"].tolist()
    return st.multiselect("Select managers", data.managers, default=data.managers[:2], key=f"{key}_selected")


def selected_week(data: DashboardData, key: str = "selected_week") -> int:
    return st.selectbox(
        "Gameweek",
        data.completed_gameweeks,
        index=len(data.completed_gameweeks) - 1,
        format_func=lambda value: f"GW{value}",
        key=key,
    )


def latest_leaderboard(data: DashboardData) -> pd.DataFrame:
    return leaderboard(data.scores)


def weekly_leaderboard(data: DashboardData, week: int) -> pd.DataFrame:
    return gameweek_leaderboard(data.scores, week)


def run_standalone_page(renderer) -> None:
    root = Path(__file__).resolve().parents[1]
    points_path = root / "data" / "FPL Points.xlsx"
    chips_path = root / "data" / "FPL Chips.xlsx"
    data = load_dashboard_data(points_path, chips_path)
    renderer(data)


if __name__ == "__main__":
    st.info("This module provides shared helpers for the dashboard pages.")
