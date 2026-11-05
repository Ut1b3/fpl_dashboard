from __future__ import annotations

import plotly.express as px
import plotly.graph_objects as go


COLORS = [
    "#00ff85", "#ff2882", "#04f5ff", "#ffd23f", "#b388ff", "#ff8a3d",
    "#ffffff", "#7dff4f", "#ff7ac8", "#5ec8ff", "#c6ff00", "#ff6b6b",
    "#9be7ff", "#e0b3ff",
]


def style_figure(fig: go.Figure, height: int = 420) -> go.Figure:
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter, Segoe UI, sans-serif", "color": "#ffffff"},
        height=height,
        margin={"l": 10, "r": 10, "t": 55, "b": 24},
        title={"font": {"size": 16}},
        legend={"orientation": "h", "y": -0.22, "x": 0},
        hoverlabel={"bgcolor": "#37003c", "font_size": 13},
    )
    fig.update_xaxes(showgrid=True, automargin=True, gridcolor="rgba(255,255,255,.16)", zerolinecolor="rgba(255,255,255,.25)")
    fig.update_yaxes(showgrid=True, automargin=True, gridcolor="rgba(255,255,255,.16)", zerolinecolor="rgba(255,255,255,.25)")
    return fig


def line_chart(data, x: str, y: str, color: str = "manager", title: str = "", **kwargs):
    fig = px.line(data, x=x, y=y, color=color, color_discrete_sequence=COLORS, markers=True, title=title, **kwargs)
    return style_figure(fig)


def bar_chart(data, x: str, y: str, title: str = "", horizontal: bool = False, **kwargs):
    if horizontal:
        fig = px.bar(data, x=x, y=y, orientation="h", color=y, color_discrete_sequence=COLORS, title=title, **kwargs)
    else:
        fig = px.bar(data, x=x, y=y, color=y, color_discrete_sequence=COLORS, title=title, **kwargs)
    return style_figure(fig)
