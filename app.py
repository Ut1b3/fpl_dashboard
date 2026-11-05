from __future__ import annotations

from pathlib import Path

import streamlit as st

from utils.data_loader import DashboardData, load_dashboard_data

ROOT = Path(__file__).resolve().parent
POINTS_FILE = ROOT / "data" / "FPL Points.xlsx"
CHIPS_FILE = ROOT / "data" / "FPL Chips.xlsx"

st.set_page_config(
    page_title="FPL Mini-League Analytics",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(show_spinner="Loading and validating the league workbooks…")
def _load_cached(points_path: str, chips_path: str, file_signature: tuple[int, int, int, int]) -> DashboardData:
    del file_signature
    return load_dashboard_data(points_path, chips_path)


def load_data() -> DashboardData:
    for path in (POINTS_FILE, CHIPS_FILE):
        if not path.is_file():
            raise FileNotFoundError(f"Required workbook not found: {path}")
    signature = (
        POINTS_FILE.stat().st_mtime_ns, POINTS_FILE.stat().st_size,
        CHIPS_FILE.stat().st_mtime_ns, CHIPS_FILE.stat().st_size,
    )
    return _load_cached(str(POINTS_FILE), str(CHIPS_FILE), signature)


st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
:root { color-scheme: dark; }
.stApp { background: linear-gradient(160deg, #4b1d76 0%, #3d195b 45%, #37003c 100%); color: #ffffff; }
header[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] { background: #2a0030; border-right: 3px solid #00ff85; }
[data-testid="stSidebar"] * { font-family: 'DM Sans', sans-serif; color: #ffffff; }
.block-container { max-width: 1500px; padding-top: 2rem; padding-bottom: 3rem; }
.page-title { font-family: 'Space Grotesk', sans-serif; font-size: clamp(2rem,4vw,3rem); font-weight: 700; letter-spacing: -.04em; color: #ffffff; border-left: 8px solid #00ff85; padding-left: .8rem; }
.page-subtitle { color: #e6d6f5; margin: .35rem 0 1.5rem; font-size: 1rem; }
h1,h2,h3,h4 { font-family: 'Space Grotesk', sans-serif; letter-spacing: -.02em; color: #ffffff; }
.kpi-card { background: #ffffff; color: #37003c; border-radius: 14px; padding: .9rem 1rem; margin-bottom: .8rem; border-top: 5px solid #e90052; min-height: 118px; box-shadow: 0 6px 18px rgba(0,0,0,.25); }
.kpi-label { font-size: .8rem; font-weight: 600; text-transform: uppercase; letter-spacing: .04em; color: #7b4fa3; }
.kpi-value { font-family: 'Space Grotesk', sans-serif; font-size: 1.5rem; font-weight: 700; line-height: 1.2; color: #37003c; overflow-wrap: anywhere; word-break: break-word; margin: .25rem 0; }
.kpi-delta { display: inline-block; font-size: .8rem; font-weight: 600; background: #00ff85; color: #37003c; border-radius: 999px; padding: .1rem .6rem; }
[data-testid="stDataFrame"], [data-testid="stTable"] { border: 2px solid rgba(0,255,133,.5); border-radius: 12px; overflow: hidden; }
div[data-testid="stVerticalBlock"] > div:has(> div > .stPlotlyChart) { background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.2); border-radius: 14px; padding: .5rem; }
.stCaption, [data-testid="stCaptionContainer"] { color: #e6d6f5; }
button[kind="primary"], .stDownloadButton button { background: #00ff85; color: #37003c; border: 0; font-weight: 700; }
@media (max-width: 700px) { .block-container { padding: 1rem .7rem 2rem; } .kpi-card { min-height: 95px; } }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## ⚽ FPL Analytics")
    st.caption("Mini-league • Current season")
    page = st.radio(
        "Explore",
        [
            "League overview", "Historical position trend", "Performance analytics",
            "Cumulative points & title race", "Manager comparison", "Gameweek centre",
            "Podium analytics", "Chip analytics", "Records & achievements", "Season projections",
        ],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("Dark mode · Interactive charts")

try:
    dashboard = load_data()
except (FileNotFoundError, ValueError, ImportError) as error:
    st.error(f"Unable to load league data: {error}")
    st.info("Check that both Excel workbooks exist in the data/ directory and match the documented columns.")
    st.stop()

with st.sidebar:
    st.caption(f"Updated {dashboard.updated_at.strftime('%d %b %Y, %H:%M')}")
    st.caption(f"{len(dashboard.managers)} managers · {len(dashboard.completed_gameweeks)} completed GWs")

if dashboard.validation:
    with st.expander(f"Data validation notices ({len(dashboard.validation)})", expanded=False):
        for notice in dashboard.validation:
            st.warning(notice)

if page == "League overview":
    from pages.overview import render
elif page == "Historical position trend":
    from pages.position_trend import render
elif page == "Performance analytics":
    from pages.performance import render
elif page == "Cumulative points & title race":
    from pages.cumulative import render
elif page == "Manager comparison":
    from pages.comparison import render
elif page == "Gameweek centre":
    from pages.gameweek import render
elif page == "Podium analytics":
    from pages.podium import render
elif page == "Chip analytics":
    from pages.chips import render
elif page == "Records & achievements":
    from pages.records import render
else:
    from pages.projections import render

render(dashboard)

with st.sidebar:
    st.markdown("---")
    st.caption("League positions use cumulative adjusted points. Weekly podiums use chip-free scores.")
