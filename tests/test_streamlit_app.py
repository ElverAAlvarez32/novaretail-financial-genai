"""Pruebas automáticas del tablero Streamlit de NovaRetail.

Estas pruebas validan la carga del libro, la normalización de
periodos, los filtros, los formatos y la construcción de gráficos.

La suite no modifica el libro Excel ni inicia un servidor web.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import pytest

from novaretail.app.streamlit_app import (
    DEFAULT_WORKBOOK,
    category_chart,
    channel_chart,
    filter_periods,
    financial_chart,
    format_cop,
    format_integer,
    format_percentage,
    load_workbook,
    margin_chart,
    prepare_periods,
)


@pytest.fixture(scope="module")
def workbook_path() -> Path:
    """Obtiene la ruta del libro utilizado por el tablero."""
    assert DEFAULT_WORKBOOK.exists()
    assert DEFAULT_WORKBOOK.is_file()
    assert DEFAULT_WORKBOOK.suffix.lower() == ".xlsx"
    assert DEFAULT_WORKBOOK.stat().st_size > 0

    return DEFAULT_WORKBOOK


@pytest.fixture(scope="module")
def workbook_tables(
    workbook_path: Path,
) -> dict[str, pd.DataFrame]:
    """Carga una vez las tablas requeridas por el tablero."""
    return load_workbook(
        workbook_path=workbook_path
    )


def test_default_workbook_path_points_to_generated_file(
    workbook_path: Path,
) -> None:
    """Comprueba el nombre y ubicación del libro principal."""
    assert (
        workbook_path.name
        == "NovaRetail_Datos_RAW_v01.xlsx"
    )

    assert workbook_path.parent.name == "raw"
    assert workbook_path.parent.parent.name == "data"


def test_load_workbook_returns_expected_tables(
    workbook_tables: dict[str, pd.DataFrame],
) -> None:
    """Comprueba la carga de las doce hojas del libro."""
    expected_sheets = {
        "00_Control",
        "01_Parametros",
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

    assert isinstance(
        workbook_tables,
        dict,
    )

    assert set(
        workbook_tables.keys()
    ) == expected_sheets

    assert len(workbook_tables) == 12

    assert all(
        isinstance(table, pd.DataFrame)
        for table in workbook_tables.values()
    )


def test_load_workbook_rejects_missing_file(
    tmp_path: Path,
) -> None:
    """Comprueba el rechazo de un libro inexistente."""
    missing_workbook = (
        tmp_path / "libro_inexistente.xlsx"
    )

    with pytest.raises(
        FileNotFoundError,
        match="No se encontró el libro",
    ):
        load_workbook(
            workbook_path=missing_workbook
        )


def test_returns_receive_internal_period_alias(
    workbook_tables: dict[str, pd.DataFrame],
) -> None:
    """Comprueba la normalización del periodo de devoluciones."""
    returns = workbook_tables[
        "06_Devoluciones"
    ]

    assert "periodo_devolucion" in returns.columns
    assert "periodo" in returns.columns

    expected_periods = (
        returns["periodo_devolucion"]
        .astype(str)
        .reset_index(drop=True)
    )

    normalized_periods = (
        returns["periodo"]
        .astype(str)
        .reset_index(drop=True)
    )

    pd.testing.assert_series_equal(
        normalized_periods,
        expected_periods,
        check_names=False,
    )


def test_prepare_periods_returns_sorted_copy() -> None:
    """Comprueba el ordenamiento sin modificar la tabla original."""
    source = pd.DataFrame(
        {
            "periodo": [
                "2024-03",
                "2023-01",
                "2024-01",
            ],
            "valor": [
                30,
                10,
                20,
            ],
        }
    )

    original = source.copy(
        deep=True
    )

    prepared = prepare_periods(source)

    assert prepared["periodo"].tolist() == [
        "2023-01",
        "2024-01",
        "2024-03",
    ]

    assert prepared["periodo"].dtype == object

    pd.testing.assert_frame_equal(
        source,
        original,
    )


def test_filter_periods_includes_selected_boundaries() -> None:
    """Comprueba que el filtro incluya los periodos extremos."""
    source = pd.DataFrame(
        {
            "periodo": [
                "2023-01",
                "2023-02",
                "2023-03",
                "2023-04",
            ],
            "valor": [
                1,
                2,
                3,
                4,
            ],
        }
    )

    filtered = filter_periods(
        dataframe=source,
        start_period="2023-02",
        end_period="2023-03",
    )

    assert filtered["periodo"].tolist() == [
        "2023-02",
        "2023-03",
    ]

    assert filtered["valor"].tolist() == [
        2,
        3,
    ]


def test_filter_periods_reviews_complete_financial_range(
    workbook_tables: dict[str, pd.DataFrame],
) -> None:
    """Comprueba los 36 periodos financieros del proyecto."""
    income_statement = workbook_tables[
        "08_Estado_Resultados"
    ]

    filtered = filter_periods(
        dataframe=income_statement,
        start_period="2023-01",
        end_period="2025-12",
    )

    assert len(filtered) == 36
    assert filtered.iloc[0]["periodo"] == "2023-01"
    assert filtered.iloc[-1]["periodo"] == "2025-12"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, "0"),
        (120, "120"),
        (4000, "4.000"),
        (18072, "18.072"),
        (23706, "23.706"),
    ],
)
def test_format_integer(
    value: int,
    expected: str,
) -> None:
    """Comprueba el formato entero usado por las tarjetas."""
    assert format_integer(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.0, "0,00 %"),
        (0.0442, "4,42 %"),
        (0.2931, "29,31 %"),
        (1.0, "100,00 %"),
    ],
)
def test_format_percentage(
    value: float,
    expected: str,
) -> None:
    """Comprueba el formato porcentual del tablero."""
    assert format_percentage(value) == expected


def test_format_cop_uses_millions() -> None:
    """Comprueba el formato monetario abreviado."""
    assert format_cop(
        76_959_255_100
    ) == "$ 76.959,3 millones"

    assert format_cop(
        3_425_293_548
    ) == "$ 3.425,3 millones"


def test_financial_chart_returns_plotly_figure(
    workbook_tables: dict[str, pd.DataFrame],
) -> None:
    """Comprueba la construcción del gráfico financiero."""
    income_statement = filter_periods(
        dataframe=workbook_tables[
            "08_Estado_Resultados"
        ],
        start_period="2023-01",
        end_period="2025-12",
    )

    figure = financial_chart(
        income=income_statement
    )

    assert isinstance(
        figure,
        go.Figure,
    )

    assert len(figure.data) == 3

    trace_names = {
        trace.name
        for trace in figure.data
    }

    assert trace_names == {
        "Ingresos netos",
        "Utilidad bruta",
        "Utilidad neta",
    }


def test_margin_chart_returns_three_margin_series(
    workbook_tables: dict[str, pd.DataFrame],
) -> None:
    """Comprueba el gráfico de márgenes financieros."""
    income_statement = filter_periods(
        dataframe=workbook_tables[
            "08_Estado_Resultados"
        ],
        start_period="2024-01",
        end_period="2024-12",
    )

    figure = margin_chart(
        income=income_statement
    )

    assert isinstance(
        figure,
        go.Figure,
    )

    assert len(figure.data) == 3

    assert all(
        len(trace.x) == 12
        for trace in figure.data
    )


def test_category_chart_uses_real_order_categories(
    workbook_tables: dict[str, pd.DataFrame],
) -> None:
    """Comprueba las ventas agrupadas por categoría."""
    orders = filter_periods(
        dataframe=workbook_tables[
            "04_Pedidos"
        ],
        start_period="2023-01",
        end_period="2025-12",
    )

    figure = category_chart(
        orders=orders
    )

    assert isinstance(
        figure,
        go.Figure,
    )

    assert len(figure.data) == 1

    expected_categories = set(
        orders["categoria"]
        .dropna()
        .astype(str)
        .unique()
    )

    chart_categories = set(
        str(value)
        for value in figure.data[0].y
    )

    assert (
        chart_categories
        == expected_categories
    )


def test_channel_chart_uses_real_channel_column(
    workbook_tables: dict[str, pd.DataFrame],
) -> None:
    """Comprueba que el gráfico use la columna real canal."""
    orders = filter_periods(
        dataframe=workbook_tables[
            "04_Pedidos"
        ],
        start_period="2023-01",
        end_period="2025-12",
    )

    assert "canal" in orders.columns
    assert "canal_venta" not in orders.columns

    figure = channel_chart(
        orders=orders
    )

    assert isinstance(
        figure,
        go.Figure,
    )

    assert len(figure.data) == 1

    expected_channels = set(
        orders["canal"]
        .dropna()
        .astype(str)
        .unique()
    )

    chart_channels = set(
        str(value)
        for value in figure.data[0].labels
    )

    assert chart_channels == expected_channels


def test_dashboard_known_record_counts(
    workbook_tables: dict[str, pd.DataFrame],
) -> None:
    """Comprueba los volúmenes visibles en el tablero."""
    assert len(
        workbook_tables["02_Productos"]
    ) == 120

    assert len(
        workbook_tables["03_Clientes"]
    ) == 4000

    assert len(
        workbook_tables["04_Pedidos"]
    ) == 23706

    assert len(
        workbook_tables["05_Inventario"]
    ) == 3712

    assert len(
        workbook_tables["06_Devoluciones"]
    ) == 1511

    assert len(
        workbook_tables["07_Marketing"]
    ) == 216

    assert len(
        workbook_tables[
            "08_Estado_Resultados"
        ]
    ) == 36


def test_dashboard_totals_match_verified_values(
    workbook_tables: dict[str, pd.DataFrame],
) -> None:
    """Comprueba los indicadores financieros publicados."""
    income_statement = workbook_tables[
        "08_Estado_Resultados"
    ]

    total_net_revenue = float(
        income_statement[
            "ingresos_netos_cop"
        ].sum()
    )

    total_net_profit = float(
        income_statement[
            "utilidad_neta_cop"
        ].sum()
    )

    average_net_margin = float(
        income_statement[
            "margen_neto"
        ].mean()
    )

    assert total_net_revenue == pytest.approx(
        76_959_255_100,
        abs=1.0,
    )

    assert total_net_profit == pytest.approx(
        3_425_293_548,
        abs=1.0,
    )

    assert average_net_margin == pytest.approx(
        0.0442,
        abs=0.0001,
    )