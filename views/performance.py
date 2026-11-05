from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from views.common import heading, render_chart, run_standalone_page
from utils.calculations import streaks
from utils.chart_helpers import COLORS
from utils.data_loader import DashboardData


def render(data: DashboardData) -> None:
    heading("Performance analytics", "Compare actual Gameweek scores, consistency and recent scoring patterns.")
    stats = data.stats.sort_values("average_points", ascending=False)
    league_avg = data.scores["podium_points"].mean()
    left, right = st.columns(2)
    with left:
        fig = px.bar(stats.sort_values("average_points"), x="average_points", y="manager", orientation="h",
                     color="average_points", color_continuous_scale=["#e90052", "#00ff85"],
                     title="Average actual points per Gameweek")
        fig.add_vline(x=league_avg, line_dash="dash", line_color="#04f5ff", annotation_text=f"League avg {league_avg:.1f}")
        render_chart(fig)
    with right:
        consistency = stats.sort_values("coefficient_of_variation", ascending=True)
        fig = px.bar(consistency, x="coefficient_of_variation", y="manager", orientation="h",
                     color="coefficient_of_variation", color_continuous_scale=["#00ff85", "#e90052"],
                     title="Consistency ranking (lower CV is steadier)")
        render_chart(fig)

    weekly = data.scores.copy()
    weekly["performance"] = weekly["podium_points"]
    left, right = st.columns(2)
    with left:
        fig = px.box(weekly, x="manager", y="performance", color="manager", points="outliers",
                     title="Weekly score distribution")
        fig.update_layout(showlegend=False)
        render_chart(fig)
    with right:
        bounds = weekly.groupby("manager").agg(best=("podium_points", "max"), worst=("podium_points", "min")).reset_index()
        best_gw = weekly.loc[weekly.groupby("manager")["podium_points"].idxmax(), ["manager", "gameweek"]].rename(columns={"gameweek": "best_gw"})
        worst_gw = weekly.loc[weekly.groupby("manager")["podium_points"].idxmin(), ["manager", "gameweek"]].rename(columns={"gameweek": "worst_gw"})
        bounds = bounds.merge(best_gw, on="manager").merge(worst_gw, on="manager")
        bounds["range"] = bounds["best"] - bounds["worst"]
        st.markdown("**Best and worst Gameweeks**")
        st.dataframe(bounds.sort_values("best", ascending=False).rename(columns={
            "manager": "Manager", "best": "Best score", "best_gw": "Best GW",
            "worst": "Lowest score", "worst_gw": "Lowest GW", "range": "Range",
        }), use_container_width=True, hide_index=True)

    avg = data.scores.groupby("gameweek")["podium_points"].mean().reset_index(name="league_average")
    render_chart(px.line(avg, x="gameweek", y="league_average", markers=True, title="Weekly league average"))
    heat = data.scores.pivot(index="manager", columns="gameweek", values="podium_points").reindex(data.managers)
    weekly_means = data.scores.groupby("gameweek")["podium_points"].mean()
    relative = heat.subtract(weekly_means, axis="columns")
    fig = go.Figure(go.Heatmap(
        x=heat.columns,
        y=heat.index,
        z=relative.to_numpy(),
        customdata=heat.to_numpy(),
        colorscale="RdYlGn",
        colorbar={"title": "vs GW avg"},
        hovertemplate="Manager: %{y}<br>GW%{x}<br>Actual points: %{customdata}<br>Vs GW average: %{z:+.1f}<extra></extra>",
    ))
    fig.update_layout(title="Actual points heatmap · colour shows performance vs weekly average")
    render_chart(fig, "points-heatmap")
    st.markdown("#### Above-average frequency and streaks")
    streak = streaks(data.scores)
    combined = data.stats[["manager", "above_average_weeks", "above_average_pct"]].merge(streak, on="manager")
    st.dataframe(combined.sort_values("above_average_pct", ascending=False).rename(columns={
        "manager": "Manager", "above_average_weeks": "Weeks above average", "above_average_pct": "Above average %",
        "longest_above": "Longest above streak", "longest_below": "Longest below streak",
        "current_streak_type": "Current streak", "current_streak": "Current streak length",
    }), use_container_width=True, hide_index=True)


if __name__ == "__main__":
    run_standalone_page(render)
