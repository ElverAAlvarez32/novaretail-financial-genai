"""Componentes visuales del tablero NovaRetail.

Este módulo centraliza los colores, estilos CSS, tarjetas,
encabezados y configuración gráfica de la aplicación Streamlit.

No contiene lógica financiera ni modifica los datos originales.
"""

from __future__ import annotations

from html import escape
from typing import Final

import plotly.graph_objects as go
import streamlit as st


COLOR_BACKGROUND: Final[str] = "#07111F"
COLOR_SURFACE: Final[str] = "#101D2E"
COLOR_SURFACE_LIGHT: Final[str] = "#16263A"
COLOR_BORDER: Final[str] = "#24344D"

COLOR_PRIMARY: Final[str] = "#2DD4BF"
COLOR_BLUE: Final[str] = "#38BDF8"
COLOR_PURPLE: Final[str] = "#A78BFA"
COLOR_AMBER: Final[str] = "#F59E0B"
COLOR_RED: Final[str] = "#FB7185"
COLOR_GREEN: Final[str] = "#22C55E"

COLOR_TEXT: Final[str] = "#F8FAFC"
COLOR_TEXT_MUTED: Final[str] = "#94A3B8"

CHART_COLORS: Final[list[str]] = [
    COLOR_BLUE,
    COLOR_PRIMARY,
    COLOR_PURPLE,
    COLOR_AMBER,
    COLOR_RED,
    COLOR_GREEN,
    "#60A5FA",
    "#E879F9",
]


def inject_global_css() -> None:
    """Inyecta los estilos CSS generales del tablero."""
    st.markdown(
        """
        <style>
        :root {
            --nr-background: #07111F;
            --nr-surface: #101D2E;
            --nr-surface-light: #16263A;
            --nr-border: #24344D;
            --nr-primary: #2DD4BF;
            --nr-blue: #38BDF8;
            --nr-purple: #A78BFA;
            --nr-amber: #F59E0B;
            --nr-red: #FB7185;
            --nr-green: #22C55E;
            --nr-text: #F8FAFC;
            --nr-muted: #94A3B8;
        }

        [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(
                    circle at 85% 5%,
                    rgba(56, 189, 248, 0.08),
                    transparent 28%
                ),
                radial-gradient(
                    circle at 15% 95%,
                    rgba(45, 212, 191, 0.06),
                    transparent 30%
                ),
                var(--nr-background);
        }

        [data-testid="stHeader"] {
            background: rgba(7, 17, 31, 0.80);
            backdrop-filter: blur(12px);
        }

        [data-testid="stSidebar"] {
            background:
                linear-gradient(
                    180deg,
                    #101D2E 0%,
                    #0B1727 100%
                );
            border-right: 1px solid var(--nr-border);
        }

        [data-testid="stSidebarContent"] {
            padding-top: 1.5rem;
        }

        .block-container {
            max-width: 1680px;
            padding-top: 2.2rem;
            padding-bottom: 4rem;
        }

        h1,
        h2,
        h3 {
            letter-spacing: -0.025em;
        }

        .nr-hero {
            position: relative;
            overflow: hidden;
            padding: 2rem 2.1rem;
            margin-bottom: 1.4rem;
            border: 1px solid rgba(56, 189, 248, 0.22);
            border-radius: 1.25rem;
            background:
                linear-gradient(
                    120deg,
                    rgba(16, 29, 46, 0.98) 0%,
                    rgba(16, 45, 67, 0.94) 55%,
                    rgba(13, 73, 77, 0.88) 100%
                );
            box-shadow:
                0 22px 50px rgba(0, 0, 0, 0.25),
                inset 0 1px 0 rgba(255, 255, 255, 0.04);
        }

        .nr-hero::after {
            content: "";
            position: absolute;
            width: 280px;
            height: 280px;
            right: -95px;
            top: -120px;
            border-radius: 50%;
            background: rgba(45, 212, 191, 0.13);
            filter: blur(3px);
        }

        .nr-hero-content {
            position: relative;
            z-index: 1;
        }

        .nr-hero-eyebrow {
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
            margin-bottom: 0.7rem;
            padding: 0.34rem 0.72rem;
            border: 1px solid rgba(45, 212, 191, 0.28);
            border-radius: 999px;
            color: #99F6E4;
            background: rgba(45, 212, 191, 0.10);
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }

        .nr-hero-title {
            margin: 0;
            color: var(--nr-text);
            font-size: clamp(2rem, 4vw, 3.45rem);
            line-height: 1.04;
            font-weight: 800;
        }

        .nr-hero-accent {
            color: var(--nr-primary);
        }

        .nr-hero-subtitle {
            max-width: 850px;
            margin: 0.85rem 0 0;
            color: #CBD5E1;
            font-size: 1.03rem;
            line-height: 1.65;
        }

        .nr-hero-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 0.7rem;
            margin-top: 1.2rem;
        }

        .nr-chip {
            padding: 0.43rem 0.75rem;
            border: 1px solid rgba(148, 163, 184, 0.20);
            border-radius: 999px;
            color: #CBD5E1;
            background: rgba(7, 17, 31, 0.32);
            font-size: 0.82rem;
            font-weight: 600;
        }

        .nr-section-header {
            display: flex;
            align-items: center;
            gap: 0.8rem;
            margin-top: 0.8rem;
            margin-bottom: 1rem;
        }

        .nr-section-icon {
            display: grid;
            place-items: center;
            width: 2.55rem;
            height: 2.55rem;
            flex: 0 0 2.55rem;
            border-radius: 0.8rem;
            background:
                linear-gradient(
                    135deg,
                    rgba(56, 189, 248, 0.22),
                    rgba(45, 212, 191, 0.18)
                );
            border: 1px solid rgba(56, 189, 248, 0.22);
            font-size: 1.25rem;
        }

        .nr-section-title {
            margin: 0;
            color: var(--nr-text);
            font-size: 1.42rem;
            font-weight: 750;
        }

        .nr-section-description {
            margin: 0.18rem 0 0;
            color: var(--nr-muted);
            font-size: 0.88rem;
        }

        .nr-kpi-card {
            min-height: 138px;
            height: 100%;
            padding: 1.08rem 1.12rem;
            border: 1px solid var(--nr-border);
            border-radius: 1rem;
            background:
                linear-gradient(
                    145deg,
                    rgba(16, 29, 46, 0.98),
                    rgba(12, 25, 42, 0.98)
                );
            box-shadow:
                0 12px 28px rgba(0, 0, 0, 0.18),
                inset 0 1px 0 rgba(255, 255, 255, 0.025);
            transition:
                transform 160ms ease,
                border-color 160ms ease,
                box-shadow 160ms ease;
        }

        .nr-kpi-card:hover {
            transform: translateY(-3px);
            border-color: rgba(45, 212, 191, 0.48);
            box-shadow:
                0 18px 34px rgba(0, 0, 0, 0.25),
                0 0 0 1px rgba(45, 212, 191, 0.05);
        }

        .nr-kpi-top {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 0.8rem;
        }

        .nr-kpi-label {
            color: var(--nr-muted);
            font-size: 0.82rem;
            font-weight: 650;
            line-height: 1.35;
        }

        .nr-kpi-icon {
            display: grid;
            place-items: center;
            width: 2.25rem;
            height: 2.25rem;
            flex: 0 0 2.25rem;
            border-radius: 0.75rem;
            font-size: 1.08rem;
        }

        .nr-kpi-value {
            margin-top: 0.65rem;
            color: var(--nr-text);
            font-size: clamp(1.22rem, 1.9vw, 1.82rem);
            line-height: 1.15;
            font-weight: 780;
            word-break: break-word;
        }

        .nr-kpi-caption {
            margin-top: 0.55rem;
            color: var(--nr-muted);
            font-size: 0.73rem;
            line-height: 1.35;
        }

        .nr-kpi-blue {
            border-top: 3px solid var(--nr-blue);
        }

        .nr-kpi-blue .nr-kpi-icon {
            color: #BAE6FD;
            background: rgba(56, 189, 248, 0.16);
        }

        .nr-kpi-green {
            border-top: 3px solid var(--nr-primary);
        }

        .nr-kpi-green .nr-kpi-icon {
            color: #99F6E4;
            background: rgba(45, 212, 191, 0.16);
        }

        .nr-kpi-purple {
            border-top: 3px solid var(--nr-purple);
        }

        .nr-kpi-purple .nr-kpi-icon {
            color: #DDD6FE;
            background: rgba(167, 139, 250, 0.16);
        }

        .nr-kpi-amber {
            border-top: 3px solid var(--nr-amber);
        }

        .nr-kpi-amber .nr-kpi-icon {
            color: #FDE68A;
            background: rgba(245, 158, 11, 0.16);
        }

        .nr-kpi-red {
            border-top: 3px solid var(--nr-red);
        }

        .nr-kpi-red .nr-kpi-icon {
            color: #FECDD3;
            background: rgba(251, 113, 133, 0.16);
        }

        .nr-panel {
            padding: 1rem 1.1rem;
            border: 1px solid var(--nr-border);
            border-radius: 1rem;
            background: rgba(16, 29, 46, 0.72);
            box-shadow: 0 12px 26px rgba(0, 0, 0, 0.14);
        }

        .nr-status-card {
            padding: 0.9rem 1rem;
            border: 1px solid rgba(34, 197, 94, 0.28);
            border-radius: 0.85rem;
            background: rgba(34, 197, 94, 0.10);
        }

        .nr-status-title {
            color: #86EFAC;
            font-weight: 750;
            font-size: 0.9rem;
        }

        .nr-status-text {
            margin-top: 0.2rem;
            color: #BBF7D0;
            font-size: 0.78rem;
            line-height: 1.4;
        }

        [data-testid="stMetric"] {
            padding: 1rem;
            border: 1px solid var(--nr-border);
            border-radius: 0.9rem;
            background: rgba(16, 29, 46, 0.78);
        }

        [data-testid="stMetricLabel"] {
            color: var(--nr-muted);
        }

        [data-testid="stMetricValue"] {
            color: var(--nr-text);
        }

        [data-baseweb="tab-list"] {
            gap: 0.45rem;
            padding: 0.3rem;
            border: 1px solid var(--nr-border);
            border-radius: 0.9rem;
            background: rgba(16, 29, 46, 0.58);
        }

        [data-baseweb="tab"] {
            height: 2.65rem;
            padding: 0 1rem;
            border-radius: 0.65rem;
            color: var(--nr-muted);
            font-weight: 650;
        }

        [aria-selected="true"][data-baseweb="tab"] {
            color: #CCFBF1;
            background: rgba(45, 212, 191, 0.14);
        }

        [data-testid="stDataFrame"] {
            border: 1px solid var(--nr-border);
            border-radius: 0.9rem;
            overflow: hidden;
        }

        [data-testid="stPlotlyChart"] {
            border: 1px solid var(--nr-border);
            border-radius: 1rem;
            background: rgba(16, 29, 46, 0.38);
            padding: 0.35rem;
            overflow: hidden;
        }

        [data-testid="stSelectbox"] > div > div {
            background: rgba(16, 29, 46, 0.92);
        }

        .stDownloadButton button,
        .stButton button {
            border: 1px solid rgba(45, 212, 191, 0.38);
            background:
                linear-gradient(
                    135deg,
                    rgba(45, 212, 191, 0.18),
                    rgba(56, 189, 248, 0.10)
                );
            color: #CCFBF1;
            font-weight: 700;
        }

        .stDownloadButton button:hover,
        .stButton button:hover {
            border-color: var(--nr-primary);
            color: #FFFFFF;
        }

        @media (max-width: 900px) {
            .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
            }

            .nr-hero {
                padding: 1.45rem;
            }

            .nr-hero-title {
                font-size: 2rem;
            }

            .nr-kpi-card {
                min-height: 125px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero(
    title: str,
    subtitle: str,
    eyebrow: str = "Inteligencia financiera sintética",
    chips: tuple[str, ...] = (),
) -> None:
    """Presenta el encabezado principal del tablero.

    Args:
        title: Título principal.
        subtitle: Descripción del tablero.
        eyebrow: Texto superior breve.
        chips: Etiquetas informativas.
    """
    safe_title = escape(title)
    safe_subtitle = escape(subtitle)
    safe_eyebrow = escape(eyebrow)

    chips_html = "".join(
        (
            '<span class="nr-chip">'
            f"{escape(chip)}"
            "</span>"
        )
        for chip in chips
    )

    st.markdown(
        f"""
        <section class="nr-hero">
            <div class="nr-hero-content">
                <div class="nr-hero-eyebrow">
                    ✦ {safe_eyebrow}
                </div>
                <h1 class="nr-hero-title">
                    NovaRetail
                    <span class="nr-hero-accent">
                        Financial GenAI
                    </span>
                </h1>
                <p class="nr-hero-subtitle">
                    {safe_subtitle}
                </p>
                <div class="nr-hero-meta">
                    {chips_html}
                </div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_section_header(
    title: str,
    description: str,
    icon: str,
) -> None:
    """Presenta un encabezado visual de sección.

    Args:
        title: Nombre de la sección.
        description: Explicación breve.
        icon: Emoji o símbolo representativo.
    """
    st.markdown(
        f"""
        <div class="nr-section-header">
            <div class="nr-section-icon">
                {escape(icon)}
            </div>
            <div>
                <h2 class="nr-section-title">
                    {escape(title)}
                </h2>
                <p class="nr-section-description">
                    {escape(description)}
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_card(
    label: str,
    value: str,
    icon: str,
    color: str = "blue",
    caption: str = "",
) -> None:
    """Presenta una tarjeta visual de indicador.

    Args:
        label: Nombre del indicador.
        value: Valor ya formateado.
        icon: Emoji o símbolo de la tarjeta.
        color: Variante visual.
        caption: Explicación inferior opcional.
    """
    allowed_colors = {
        "blue",
        "green",
        "purple",
        "amber",
        "red",
    }

    selected_color = (
        color
        if color in allowed_colors
        else "blue"
    )

    caption_html = ""

    if caption:
        caption_html = (
            '<div class="nr-kpi-caption">'
            f"{escape(caption)}"
            "</div>"
        )

    st.markdown(
        f"""
        <article
            class="nr-kpi-card nr-kpi-{selected_color}"
        >
            <div class="nr-kpi-top">
                <div class="nr-kpi-label">
                    {escape(label)}
                </div>
                <div class="nr-kpi-icon">
                    {escape(icon)}
                </div>
            </div>
            <div class="nr-kpi-value">
                {escape(value)}
            </div>
            {caption_html}
        </article>
        """,
        unsafe_allow_html=True,
    )


def render_status_card(
    title: str,
    text: str,
) -> None:
    """Presenta un mensaje positivo en la barra lateral.

    Args:
        title: Título del estado.
        text: Descripción del estado.
    """
    st.markdown(
        f"""
        <div class="nr-status-card">
            <div class="nr-status-title">
                ✓ {escape(title)}
            </div>
            <div class="nr-status-text">
                {escape(text)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def apply_plotly_layout(
    figure: go.Figure,
    *,
    height: int = 430,
    legend_title: str = "",
    hovermode: str = "x unified",
) -> go.Figure:
    """Aplica el estilo visual estándar a un gráfico Plotly.

    Args:
        figure: Gráfico original.
        height: Altura del gráfico.
        legend_title: Título de la leyenda.
        hovermode: Comportamiento de información emergente.

    Returns:
        Gráfico con el estilo corporativo.
    """
    figure.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={
            "color": COLOR_TEXT,
            "family": "Arial, sans-serif",
        },
        title={
            "font": {
                "size": 18,
                "color": COLOR_TEXT,
            },
            "x": 0.01,
            "xanchor": "left",
        },
        margin={
            "l": 28,
            "r": 24,
            "t": 65,
            "b": 38,
        },
        hovermode=hovermode,
        hoverlabel={
            "bgcolor": COLOR_SURFACE_LIGHT,
            "bordercolor": COLOR_BORDER,
            "font": {
                "color": COLOR_TEXT,
            },
        },
        legend={
            "title": {
                "text": legend_title,
            },
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
            "bgcolor": "rgba(0,0,0,0)",
        },
    )

    figure.update_xaxes(
        showgrid=False,
        linecolor=COLOR_BORDER,
        tickfont={
            "color": COLOR_TEXT_MUTED,
        },
        title_font={
            "color": COLOR_TEXT_MUTED,
        },
    )

    figure.update_yaxes(
        showgrid=True,
        gridcolor="rgba(148,163,184,0.11)",
        zerolinecolor="rgba(148,163,184,0.18)",
        linecolor=COLOR_BORDER,
        tickfont={
            "color": COLOR_TEXT_MUTED,
        },
        title_font={
            "color": COLOR_TEXT_MUTED,
        },
    )

    return figure