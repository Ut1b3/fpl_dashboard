from __future__ import annotations

import importlib
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
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: .8rem; margin-bottom: .6rem; }
.kpi-grid .kpi-card { margin-bottom: 0; }
@media (max-width: 700px) {
  .block-container { padding: 3.2rem .6rem 2rem; }
  .page-title { font-size: 1.6rem; border-left-width: 5px; }
  .page-subtitle { font-size: .9rem; margin-bottom: 1rem; }
  .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .5rem; }
  .kpi-card { min-height: 0; padding: .6rem .7rem; }
  .kpi-label { font-size: .65rem; }
  .kpi-value { font-size: 1.1rem; }
  .kpi-delta { font-size: .68rem; }
  h4 { font-size: 1.1rem; }
  div[data-testid="stVerticalBlock"] > div:has(> div > .stPlotlyChart) { padding: .2rem; }
  [data-testid="stHorizontalBlock"] { gap: .5rem; }
}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## ⚽ FPL Analytics")
    st.caption("Mini-league • Current season")

try:
    dashboard = load_data()
except (FileNotFoundError, ValueError, ImportError) as error:
    st.error(f"Unable to load league data: {error}")
    st.info("Check that both Excel workbooks exist in the data/ directory and match the documented columns.")
    st.stop()

with st.sidebar:
    st.caption(f"Updated {dashboard.updated_at.strftime('%d %b %Y, %H:%M')}")
    st.caption(f"{len(dashboard.managers)} managers · {len(dashboard.completed_gameweeks)} completed GWs")

PAGES = [
    ("League overview", "overview", "🏠"),
    ("Historical position trend", "position_trend", "📈"),
    ("Performance analytics", "performance", "📊"),
    ("Cumulative points & title race", "cumulative", "🏁"),
    ("Manager comparison", "comparison", "⚖️"),
    ("Gameweek centre", "gameweek", "📅"),
    ("Podium analytics", "podium", "🥇"),
    ("Gameweek winners", "winners", "🏆"),
    ("Notable performances", "notable", "⭐"),
    ("Chip analytics", "chips", "🃏"),
    ("Records & achievements", "records", "🎖️"),
    ("Season projections", "projections", "🔮"),
]


def _make_page(module_name: str):
    def run() -> None:
        if dashboard.validation:
            with st.expander(f"Data validation notices ({len(dashboard.validation)})", expanded=False):
                for notice in dashboard.validation:
                    st.warning(notice)
        importlib.import_module(f"views.{module_name}").render(dashboard)
    run.__name__ = f"page_{module_name}"
    return run


navigation = st.navigation([
    st.Page(_make_page(module), title=title, icon=icon,
            **({"default": True} if module == "overview" else {"url_path": module}))
    for title, module, icon in PAGES
])
navigation.run()

with st.sidebar:
    st.markdown("---")
    st.caption("League positions use cumulative adjusted points. Weekly podiums use chip-free scores.")
