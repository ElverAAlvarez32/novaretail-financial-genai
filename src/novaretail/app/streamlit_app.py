"""Tablero ejecutivo interactivo de NovaRetail Financial GenAI.

Presenta información financiera y operativa construida con datos
completamente sintéticos de uso exclusivamente académico.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from novaretail.app.dashboard_theme import (
    CHART_COLORS,
    COLOR_BLUE,
    COLOR_PRIMARY,
    COLOR_PURPLE,
    apply_plotly_layout,
    inject_global_css,
    render_hero,
    render_kpi_card,
    render_section_header,
    render_status_card,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_WORKBOOK = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "NovaRetail_Datos_RAW_v01.xlsx"
)

PAGES = {
    "Resumen ejecutivo": "🏠",
    "Estado de resultados": "📈",
    "Inventario de datos": "🗂️",
}


st.set_page_config(
    page_title="NovaRetail Financial GenAI",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_global_css()


@st.cache_data(show_spinner=False)
def load_workbook(
    workbook_path: Path,
) -> dict[str, pd.DataFrame]:
    """Carga todas las hojas del libro Excel.

    Args:
        workbook_path: Ruta del libro generado.

    Returns:
        Diccionario con las hojas del libro.

    Raises:
        FileNotFoundError: Si el archivo no existe.
        ValueError: Si falta una hoja indispensable.
    """
    if not workbook_path.exists():
        raise FileNotFoundError(
            f"No se encontró el libro: {workbook_path}"
        )

    tables = pd.read_excel(
        workbook_path,
        sheet_name=None,
        engine="openpyxl",
    )

    returns_table = tables.get(
        "06_Devoluciones"
    )

    if returns_table is not None:
        if (
            "periodo" not in returns_table.columns
            and "periodo_devolucion"
            in returns_table.columns
        ):
            returns_table = returns_table.copy()

            returns_table["periodo"] = (
                returns_table[
                    "periodo_devolucion"
                ].astype(str)
            )

            tables["06_Devoluciones"] = (
                returns_table
            )

    required_sheets = {
        "02_Productos",
        "03_Clientes",
        "04_Pedidos",
        "05_Inventario",
        "06_Devoluciones",
        "07_Marketing",
        "08_Estado_Resultados",
        "09_Balance_General",
        "10_Flujo_Efectivo",
        "11_Presupuesto",
    }

    missing_sheets = required_sheets.difference(
        tables.keys()
    )

    if missing_sheets:
        missing_text = ", ".join(
            sorted(missing_sheets)
        )

        raise ValueError(
            "Faltan las siguientes hojas: "
            f"{missing_text}"
        )

    return tables


def format_integer(
    value: int | float,
) -> str:
    """Formatea un número con puntos de miles."""
    return f"{value:,.0f}".replace(
        ",",
        ".",
    )


def format_cop(
    value: int | float,
) -> str:
    """Formatea un valor monetario en millones de pesos."""
    millions = float(value) / 1_000_000

    formatted = (
        f"{millions:,.1f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )

    return f"$ {formatted} millones"


def format_percentage(
    value: float,
) -> str:
    """Formatea una proporción como porcentaje."""
    formatted = (
        f"{value * 100:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )

    return f"{formatted} %"


def prepare_periods(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """Normaliza la columna periodo."""
    prepared = dataframe.copy()

    prepared["periodo"] = (
        prepared["periodo"].astype(str)
    )

    return (
        prepared.sort_values("periodo")
        .reset_index(drop=True)
    )


def filter_periods(
    dataframe: pd.DataFrame,
    start_period: str,
    end_period: str,
) -> pd.DataFrame:
    """Filtra una tabla entre dos periodos."""
    prepared = prepare_periods(dataframe)

    mask = (
        (prepared["periodo"] >= start_period)
        & (prepared["periodo"] <= end_period)
    )

    return prepared.loc[mask].copy()


def render_cards(
    cards: list[dict[str, str]],
    count: int = 4,
) -> None:
    """Presenta tarjetas KPI en filas."""
    for position in range(
        0,
        len(cards),
        count,
    ):
        row_cards = cards[
            position:position + count
        ]

        columns = st.columns(
            len(row_cards)
        )

        for column, card in zip(
            columns,
            row_cards,
            strict=True,
        ):
            with column:
                render_kpi_card(
                    label=card["label"],
                    value=card["value"],
                    icon=card["icon"],
                    color=card["color"],
                    caption=card["caption"],
                )


def render_sidebar(
    tables: dict[str, pd.DataFrame],
) -> tuple[str, str, str]:
    """Presenta navegación y filtros globales."""
    st.sidebar.markdown(
        "## 📊 NovaRetail"
    )

    st.sidebar.caption(
        "Financial GenAI · Panel ejecutivo"
    )

    render_status_card(
        title="Libro cargado",
        text=(
            f"{len(tables)} hojas disponibles."
        ),
    )

    st.sidebar.markdown(
        "### Navegación"
    )

    page = st.sidebar.radio(
        "Página",
        options=list(PAGES.keys()),
        format_func=lambda option: (
            f"{PAGES[option]}  {option}"
        ),
        label_visibility="collapsed",
    )

    income = prepare_periods(
        tables["08_Estado_Resultados"]
    )

    periods = (
        income["periodo"]
        .drop_duplicates()
        .tolist()
    )

    st.sidebar.divider()

    st.sidebar.markdown(
        "### Filtros globales"
    )

    start_period = st.sidebar.selectbox(
        "Periodo inicial",
        options=periods,
        index=0,
    )

    end_options = [
        period
        for period in periods
        if period >= start_period
    ]

    end_period = st.sidebar.selectbox(
        "Periodo final",
        options=end_options,
        index=len(end_options) - 1,
    )

    st.sidebar.divider()

    st.sidebar.markdown(
        f"**Cobertura activa**  \n"
        f"{start_period} a {end_period}"
    )

    st.sidebar.markdown(
        "**Moneda**  \n"
        "Pesos colombianos"
    )

    st.sidebar.divider()


    return page, start_period, end_period


def style_figure(
    figure: Any,
    height: int = 420,
) -> Any:
    """Aplica el diseño corporativo a un gráfico."""
    return apply_plotly_layout(
        figure,
        height=height,
        legend_title="Indicador",
    )


def financial_chart(
    income: pd.DataFrame,
) -> Any:
    """Crea el gráfico financiero principal."""
    data = income[
        [
            "periodo",
            "ingresos_netos_cop",
            "utilidad_bruta_cop",
            "utilidad_neta_cop",
        ]
    ].rename(
        columns={
            "periodo": "Periodo",
            "ingresos_netos_cop":
                "Ingresos netos",
            "utilidad_bruta_cop":
                "Utilidad bruta",
            "utilidad_neta_cop":
                "Utilidad neta",
        }
    )

    long_data = data.melt(
        id_vars="Periodo",
        var_name="Indicador",
        value_name="Valor",
    )

    figure = px.area(
        long_data,
        x="Periodo",
        y="Valor",
        color="Indicador",
        color_discrete_sequence=[
            COLOR_BLUE,
            COLOR_PRIMARY,
            COLOR_PURPLE,
        ],
        title="Evolución de ingresos y utilidades",
    )

    figure.update_traces(
        opacity=0.40,
        line={
            "width": 2.5,
        },
    )

    return style_figure(
        figure,
        height=450,
    )


def category_chart(
    orders: pd.DataFrame,
) -> Any:
    """Crea el gráfico de ventas por categoría."""
    data = (
        orders.groupby(
            "categoria",
            as_index=False,
        )["valor_neto_cop"]
        .sum()
        .sort_values(
            "valor_neto_cop",
            ascending=True,
        )
        .rename(
            columns={
                "categoria": "Categoría",
                "valor_neto_cop": "Ventas",
            }
        )
    )

    figure = px.bar(
        data,
        x="Ventas",
        y="Categoría",
        orientation="h",
        color="Ventas",
        color_continuous_scale=[
            "#164E63",
            COLOR_BLUE,
            COLOR_PRIMARY,
        ],
        text_auto=".2s",
        title="Ventas netas por categoría",
    )

    figure.update_layout(
        coloraxis_showscale=False,
    )

    return style_figure(
        figure,
        height=410,
    )


def channel_chart(
    orders: pd.DataFrame,
) -> Any:
    """Crea el gráfico de participación por canal."""
    data = (
        orders.groupby(
            "canal",
            as_index=False,
        )["valor_neto_cop"]
        .sum()
        .rename(
            columns={
                "canal": "Canal",
                "valor_neto_cop": "Ventas",
            }
        )
    )

    figure = px.pie(
        data,
        names="Canal",
        values="Ventas",
        hole=0.62,
        color_discrete_sequence=CHART_COLORS,
        title="Participación de ventas por canal",
    )

    figure.update_traces(
        textposition="inside",
        textinfo="percent",
    )

    return style_figure(
        figure,
        height=410,
    )


def margin_chart(
    income: pd.DataFrame,
) -> Any:
    """Crea el gráfico mensual de márgenes."""
    data = income[
        [
            "periodo",
            "margen_bruto",
            "margen_operacional",
            "margen_neto",
        ]
    ].rename(
        columns={
            "periodo": "Periodo",
            "margen_bruto": "Margen bruto",
            "margen_operacional":
                "Margen operacional",
            "margen_neto": "Margen neto",
        }
    )

    long_data = data.melt(
        id_vars="Periodo",
        var_name="Indicador",
        value_name="Porcentaje",
    )

    long_data["Porcentaje"] = (
        long_data["Porcentaje"] * 100
    )

    figure = px.line(
        long_data,
        x="Periodo",
        y="Porcentaje",
        color="Indicador",
        markers=True,
        color_discrete_sequence=[
            COLOR_BLUE,
            COLOR_PRIMARY,
            COLOR_PURPLE,
        ],
        title="Evolución mensual de márgenes",
    )

    figure.update_yaxes(
        ticksuffix=" %",
    )

    return style_figure(
        figure,
        height=410,
    )


def render_summary(
    tables: dict[str, pd.DataFrame],
    start_period: str,
    end_period: str,
) -> None:
    """Presenta el resumen ejecutivo."""
    products = tables["02_Productos"]
    customers = tables["03_Clientes"]

    orders = filter_periods(
        tables["04_Pedidos"],
        start_period,
        end_period,
    )

    returns = filter_periods(
        tables["06_Devoluciones"],
        start_period,
        end_period,
    )

    income = filter_periods(
        tables["08_Estado_Resultados"],
        start_period,
        end_period,
    )

    render_hero(
        title="NovaRetail Financial GenAI",
        subtitle=(
            "Visión ejecutiva de ventas, rentabilidad "
            "y operación para una empresa ficticia de "
            "comercio electrónico."
        ),
        chips=(
            f"📅 {start_period} a {end_period}",
            "💱 Pesos colombianos",
            "🧪 Datos sintéticos",
            "✓ Validaciones aprobadas",
        ),
    )

    render_section_header(
        title="Pulso del negocio",
        description=(
            "Indicadores principales del periodo activo."
        ),
        icon="⚡",
    )

    order_count = int(
        orders["pedido_id"].nunique()
    )

    order_lines = len(orders)

    revenue = float(
        income["ingresos_netos_cop"].sum()
    )

    profit = float(
        income["utilidad_neta_cop"].sum()
    )

    margin = float(
        income["margen_neto"].mean()
    )

    return_rate = (
        len(returns) / order_lines
        if order_lines
        else 0.0
    )

    cards = [
        {
            "label": "Ingresos netos",
            "value": format_cop(revenue),
            "icon": "💰",
            "color": "blue",
            "caption": "Acumulado del periodo",
        },
        {
            "label": "Utilidad neta",
            "value": format_cop(profit),
            "icon": "📈",
            "color": "green",
            "caption": "Resultado neto acumulado",
        },
        {
            "label": "Margen neto",
            "value": format_percentage(margin),
            "icon": "🎯",
            "color": "purple",
            "caption": "Promedio mensual",
        },
        {
            "label": "Pedidos únicos",
            "value": format_integer(order_count),
            "icon": "🛒",
            "color": "amber",
            "caption": (
                f"{format_integer(order_lines)} "
                "líneas procesadas"
            ),
        },
        {
            "label": "Productos",
            "value": format_integer(
                products["producto_id"].nunique()
            ),
            "icon": "📦",
            "color": "blue",
            "caption": "Catálogo sintético",
        },
        {
            "label": "Clientes",
            "value": format_integer(
                customers["cliente_id"].nunique()
            ),
            "icon": "👥",
            "color": "purple",
            "caption": "Base simulada",
        },
        {
            "label": "Devoluciones",
            "value": format_integer(len(returns)),
            "icon": "↩️",
            "color": "red",
            "caption": "Registros del periodo",
        },
        {
            "label": "Tasa de devolución",
            "value": format_percentage(return_rate),
            "icon": "🔄",
            "color": "amber",
            "caption": "Sobre líneas procesadas",
        },
    ]

    render_cards(cards)

    render_section_header(
        title="Tendencia financiera",
        description=(
            "Comportamiento mensual de ingresos "
            "y resultados."
        ),
        icon="📈",
    )

    st.plotly_chart(
        financial_chart(income),
        use_container_width=True,
        config={
            "displaylogo": False,
        },
    )

    render_section_header(
        title="Composición comercial",
        description=(
            "Ventas por categoría y canal."
        ),
        icon="🧭",
    )

    category_column, channel_column = (
        st.columns([1.2, 1])
    )

    with category_column:
        st.plotly_chart(
            category_chart(orders),
            use_container_width=True,
            config={
                "displaylogo": False,
            },
        )

    with channel_column:
        st.plotly_chart(
            channel_chart(orders),
            use_container_width=True,
            config={
                "displaylogo": False,
            },
        )


def render_income_statement(
    tables: dict[str, pd.DataFrame],
    start_period: str,
    end_period: str,
) -> None:
    """Presenta el estado de resultados."""
    income = filter_periods(
        tables["08_Estado_Resultados"],
        start_period,
        end_period,
    )

    render_hero(
        title="Estado de resultados",
        subtitle=(
            "Análisis de ingresos, costos, utilidades "
            "y márgenes financieros."
        ),
        eyebrow="Desempeño financiero",
        chips=(
            f"📅 {start_period} a {end_period}",
            f"📊 {len(income)} periodos",
        ),
    )

    cards = [
        {
            "label": "Ingresos netos",
            "value": format_cop(
                income[
                    "ingresos_netos_cop"
                ].sum()
            ),
            "icon": "💰",
            "color": "blue",
            "caption": "Ventas netas acumuladas",
        },
        {
            "label": "Utilidad bruta",
            "value": format_cop(
                income[
                    "utilidad_bruta_cop"
                ].sum()
            ),
            "icon": "📊",
            "color": "green",
            "caption": (
                "Margen "
                f"{format_percentage(income['margen_bruto'].mean())}"
            ),
        },
        {
            "label": "Utilidad operacional",
            "value": format_cop(
                income[
                    "utilidad_operacional_cop"
                ].sum()
            ),
            "icon": "⚙️",
            "color": "purple",
            "caption": (
                "Margen "
                f"{format_percentage(income['margen_operacional'].mean())}"
            ),
        },
        {
            "label": "Utilidad neta",
            "value": format_cop(
                income[
                    "utilidad_neta_cop"
                ].sum()
            ),
            "icon": "🎯",
            "color": "amber",
            "caption": (
                "Margen "
                f"{format_percentage(income['margen_neto'].mean())}"
            ),
        },
    ]

    render_section_header(
        title="Resultados acumulados",
        description=(
            "Cifras del periodo seleccionado."
        ),
        icon="💼",
    )

    render_cards(cards)

    render_section_header(
        title="Evolución financiera",
        description=(
            "Ingresos, utilidades y márgenes mensuales."
        ),
        icon="📉",
    )

    st.plotly_chart(
        financial_chart(income),
        use_container_width=True,
        config={
            "displaylogo": False,
        },
    )

    st.plotly_chart(
        margin_chart(income),
        use_container_width=True,
        config={
            "displaylogo": False,
        },
    )

    render_section_header(
        title="Detalle mensual",
        description=(
            "Consulta mensual del estado de resultados."
        ),
        icon="🧾",
    )

    detail = income[
        [
            "periodo",
            "ingresos_brutos_cop",
            "ingresos_netos_cop",
            "utilidad_bruta_cop",
            "utilidad_operacional_cop",
            "utilidad_neta_cop",
            "margen_bruto",
            "margen_operacional",
            "margen_neto",
        ]
    ].copy()

    detail.columns = [
        "Periodo",
        "Ingresos brutos",
        "Ingresos netos",
        "Utilidad bruta",
        "Utilidad operacional",
        "Utilidad neta",
        "Margen bruto",
        "Margen operacional",
        "Margen neto",
    ]

    margin_columns = [
        "Margen bruto",
        "Margen operacional",
        "Margen neto",
    ]

    for column_name in margin_columns:
        detail[column_name] = (
            detail[column_name] * 100
        )

    st.dataframe(
        detail,
        use_container_width=True,
        hide_index=True,
        height=430,
    )


def render_inventory(
    tables: dict[str, pd.DataFrame],
) -> None:
    """Presenta el inventario técnico de hojas."""
    render_hero(
        title="Inventario de datos",
        subtitle=(
            "Estructura y volumen del conjunto "
            "sintético NovaRetail."
        ),
        eyebrow="Gobierno y trazabilidad",
        chips=(
            f"📚 {len(tables)} hojas",
            "✓ Libro estructurado",
        ),
    )

    records = [
        {
            "Hoja": sheet_name,
            "Filas": len(dataframe),
            "Columnas": len(
                dataframe.columns
            ),
            "Celdas": (
                len(dataframe)
                * len(dataframe.columns)
            ),
        }
        for sheet_name, dataframe
        in tables.items()
    ]

    inventory = pd.DataFrame(records)

    cards = [
        {
            "label": "Hojas disponibles",
            "value": format_integer(
                len(inventory)
            ),
            "icon": "📚",
            "color": "blue",
            "caption": "Estructura integral",
        },
        {
            "label": "Registros totales",
            "value": format_integer(
                inventory["Filas"].sum()
            ),
            "icon": "🧮",
            "color": "green",
            "caption": "Filas del libro",
        },
        {
            "label": "Celdas de datos",
            "value": format_integer(
                inventory["Celdas"].sum()
            ),
            "icon": "🗃️",
            "color": "purple",
            "caption": "Volumen aproximado",
        },
    ]

    render_cards(
        cards,
        count=3,
    )

    figure = px.bar(
        inventory.sort_values(
            "Filas",
            ascending=True,
        ),
        x="Filas",
        y="Hoja",
        orientation="h",
        color="Filas",
        color_continuous_scale=[
            "#164E63",
            COLOR_BLUE,
            COLOR_PRIMARY,
        ],
        text_auto=True,
        title="Registros por hoja",
    )

    figure.update_layout(
        coloraxis_showscale=False,
    )

    st.plotly_chart(
        style_figure(
            figure,
            height=480,
        ),
        use_container_width=True,
        config={
            "displaylogo": False,
        },
    )

    st.dataframe(
        inventory,
        use_container_width=True,
        hide_index=True,
        height=430,
    )


def main() -> None:
    """Ejecuta la aplicación Streamlit."""
    try:
        tables = load_workbook(
            DEFAULT_WORKBOOK
        )

    except FileNotFoundError as exc:
        st.error(str(exc))

        st.info(
            "Ejecuta primero: "
            "`python scripts\\generate_data.py`"
        )

        st.stop()

    except Exception as exc:
        st.error(
            "No fue posible cargar el libro."
        )

        st.exception(exc)
        st.stop()

    page, start_period, end_period = (
        render_sidebar(tables)
    )

    if page == "Resumen ejecutivo":
        render_summary(
            tables,
            start_period,
            end_period,
        )

    elif page == "Estado de resultados":
        render_income_statement(
            tables,
            start_period,
            end_period,
        )

    else:
        render_inventory(tables)


if __name__ == "__main__":
    main()
