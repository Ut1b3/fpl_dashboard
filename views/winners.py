from __future__ import annotations

import html

import pandas as pd
import plotly.express as px
import streamlit as st

from views.common import heading, metric_cards, render_chart, run_standalone_page, selected_week
from utils.calculations import gameweek_leaderboard
from utils.data_loader import DashboardData


def _winners(frame: pd.DataFrame) -> tuple[list[str], float | None]:
    valid = frame.dropna(subset=["podium_points"])
    if valid.empty:
        return [], None
    top = float(valid["podium_points"].max())
    return sorted(valid.loc[valid["podium_points"] == top, "manager"]), top


def render(data: DashboardData) -> None:
    heading("Gameweek winners", "Pick a Gameweek to see its winner, full table and statistics. Winners use chip-free scores.")
    if not data.completed_gameweeks:
        st.info("No fully populated Gameweeks are available yet.")
        return

    week = selected_week(data, "winners_week")
    frame = gameweek_leaderboard(data.scores, week)
    names, top = _winners(frame)

    if names:
        label = "Winners (tie)" if len(names) > 1 else "Winner"
        st.markdown(
            f'<div class="kpi-card" style="border-top-color:#00ff85;">'
            f'<div class="kpi-label">GW{week} {label}</div>'
            f'<div class="kpi-value" style="font-size:2rem;">🏆 {html.escape(", ".join(names))}</div>'
            f'<div class="kpi-delta">{top:.0f} pts</div></div>',
            unsafe_allow_html=True,
        )
    else:
        st.warning(f"GW{week} has no valid chip-free scores, so no winner can be determined.")

    scores = frame["podium_points"].dropna()
    ordered = frame.dropna(subset=["podium_points"])
    metric_cards([
        ("Highest score", f"{scores.max():.0f}" if not scores.empty else "—", None),
        ("Lowest score", f"{scores.min():.0f}" if not scores.empty else "—",
         ", ".join(ordered.loc[ordered["podium_points"] == scores.min(), "manager"]) if not scores.empty else None),
        ("League average", f"{scores.mean():.1f}" if not scores.empty else "—", None),
        ("League median", f"{scores.median():.1f}" if not scores.empty else "—", None),
        ("Winning margin", f"{_margin(scores):.0f}" if len(scores) > 1 else "—", "over 2nd place"),
        ("Chips used", str(int((frame["chip_bonus"] > 0).sum())), f"{frame['chip_bonus'].sum():.0f} bonus pts"),
        ("Above average", str(int((scores > scores.mean()).sum())), f"of {len(scores)} managers"),
        ("Score spread", f"{scores.max() - scores.min():.0f}" if not scores.empty else "—", "high − low"),
    ])

    st.markdown(f"#### GW{week} table")
    table = frame[[
        "podium_rank", "manager", "podium_points", "chip_bonus", "adjusted_gw_points", "cumulative_points", "league_position",
    ]].copy()
    table.columns = ["Rank", "Manager", "Podium points", "Chip bonus", "Total GW points", "Season total", "League position"]
    winning_margin = _margin(scores) if len(scores) > 1 else None
    table.insert(
        3,
        "Winning margin",
        table["Rank"].map(lambda rank: winning_margin if rank == 1 else None),
    )
    st.dataframe(table, use_container_width=True, hide_index=True)
    st.download_button("Download this table (CSV)", table.to_csv(index=False).encode("utf-8"),
                       f"fpl_gw{week}_table.csv", "text/csv")

    left, right = st.columns(2)
    with left:
        fig = px.bar(ordered.sort_values("podium_points"), x="podium_points", y="manager", orientation="h",
                     color="podium_points", color_continuous_scale=["#e90052", "#ffd23f", "#00ff85"],
                     title=f"GW{week} scores")
        if not scores.empty:
            fig.add_vline(x=scores.mean(), line_dash="dash", line_color="#04f5ff",
                          annotation_text=f"Avg {scores.mean():.1f}")
        render_chart(fig)
    with right:
        render_chart(px.histogram(ordered, x="podium_points", nbins=8, title="Score distribution",
                                  color_discrete_sequence=["#04f5ff"]))

    st.markdown("#### All Gameweek winners")
    rows = []
    for gw, group in data.scores.groupby("gameweek"):
        winner_names, winner_score = _winners(group)
        valid = group["podium_points"].dropna()
        rows.append({
            "Gameweek": f"GW{int(gw)}",
            "Winner(s)": ", ".join(winner_names) or "—",
            "Winning score": winner_score,
            "Winning margin": _margin(valid) if len(valid) > 1 else None,
            "League average": round(valid.mean(), 1) if not valid.empty else None,
            "Lowest score": valid.min() if not valid.empty else None,
        })
    history = pd.DataFrame(rows)
    st.dataframe(history, use_container_width=True, hide_index=True)

    wins = (
        history.assign(winner=history["Winner(s)"].str.split(", ")).explode("winner")
        .query("winner != '—'").groupby("winner").size().sort_values(ascending=False).reset_index(name="Wins")
    )
    if not wins.empty:
        wins = wins.rename(columns={"winner": "Manager"})
        render_chart(px.bar(wins, x="Manager", y="Wins", color="Wins",
                            color_continuous_scale=["#8f6bb3", "#00ff85"], title="Gameweek wins by manager"))


def _margin(scores: pd.Series) -> float:
    top_two = scores.nlargest(2).tolist()
    return top_two[0] - top_two[1]


if __name__ == "__main__":
    run_standalone_page(render)
