"""Pruebas automáticas del estado de resultados sintético."""

from __future__ import annotations

import pandas as pd
import pytest

from novaretail.config import load_data_generation_config
from novaretail.generation.customers import generate_customers
from novaretail.generation.financial_statements import (
    INCOME_STATEMENT_COLUMNS,
    generate_income_statement,
)
from novaretail.generation.marketing import generate_marketing
from novaretail.generation.orders import generate_orders
from novaretail.generation.products import generate_products
from novaretail.generation.returns import generate_returns


@pytest.fixture(scope="module")
def products() -> pd.DataFrame:
    """Genera una sola vez el catálogo de productos."""
    return generate_products()


@pytest.fixture(scope="module")
def customers() -> pd.DataFrame:
    """Genera una sola vez el catálogo de clientes."""
    return generate_customers()


@pytest.fixture(scope="module")
def orders(
    products: pd.DataFrame,
    customers: pd.DataFrame,
) -> pd.DataFrame:
    """Genera una sola vez las líneas de pedido."""
    return generate_orders(
        products=products,
        customers=customers,
    )


@pytest.fixture(scope="module")
def returns(
    orders: pd.DataFrame,
) -> pd.DataFrame:
    """Genera una sola vez las devoluciones."""
    return generate_returns(orders=orders)


@pytest.fixture(scope="module")
def marketing() -> pd.DataFrame:
    """Genera una sola vez los datos de marketing."""
    return generate_marketing()


@pytest.fixture(scope="module")
def income_statement(
    orders: pd.DataFrame,
    returns: pd.DataFrame,
    marketing: pd.DataFrame,
) -> pd.DataFrame:
    """Genera una sola vez el estado de resultados."""
    return generate_income_statement(
        orders=orders,
        returns=returns,
        marketing=marketing,
    )


def test_income_statement_has_expected_columns(
    income_statement: pd.DataFrame,
) -> None:
    """Comprueba el nombre y orden de las columnas."""
    assert (
        income_statement.columns.tolist()
        == INCOME_STATEMENT_COLUMNS
    )


def test_income_statement_has_expected_dimensions(
    income_statement: pd.DataFrame,
) -> None:
    """Comprueba la cantidad de periodos y columnas."""
    configuration = load_data_generation_config()

    expected_months = pd.date_range(
        start=configuration["period"]["start_date"],
        end=configuration["period"]["end_date"],
        freq="MS",
    ).size

    assert income_statement.shape == (
        expected_months,
        len(INCOME_STATEMENT_COLUMNS),
    )


def test_income_statement_contains_expected_periods(
    income_statement: pd.DataFrame,
) -> None:
    """Comprueba la cobertura temporal completa."""
    configuration = load_data_generation_config()

    expected_periods = pd.date_range(
        start=configuration["period"]["start_date"],
        end=configuration["period"]["end_date"],
        freq="MS",
    ).strftime("%Y-%m")

    assert income_statement["periodo"].tolist() == (
        expected_periods.tolist()
    )


def test_income_statement_periods_are_unique(
    income_statement: pd.DataFrame,
) -> None:
    """Comprueba que no existan periodos duplicados."""
    assert income_statement["periodo"].is_unique


def test_year_matches_period(
    income_statement: pd.DataFrame,
) -> None:
    """Comprueba el año registrado para cada periodo."""
    expected_year = pd.to_datetime(
        income_statement["periodo"] + "-01"
    ).dt.year

    pd.testing.assert_series_equal(
        income_statement["anio"],
        expected_year,
        check_names=False,
    )


def test_month_matches_period(
    income_statement: pd.DataFrame,
) -> None:
    """Comprueba el número del mes para cada periodo."""
    expected_month = pd.to_datetime(
        income_statement["periodo"] + "-01"
    ).dt.month

    pd.testing.assert_series_equal(
        income_statement["mes"],
        expected_month,
        check_names=False,
    )


def test_gross_revenue_is_positive(
    income_statement: pd.DataFrame,
) -> None:
    """Comprueba que los ingresos brutos sean positivos."""
    assert (
        income_statement["ingresos_brutos_cop"] > 0
    ).all()


def test_discounts_are_non_negative(
    income_statement: pd.DataFrame,
) -> None:
    """Comprueba que los descuentos no sean negativos."""
    assert (
        income_statement["descuentos_cop"] >= 0
    ).all()


def test_sales_returns_are_non_negative(
    income_statement: pd.DataFrame,
) -> None:
    """Comprueba que las devoluciones no sean negativas."""
    assert (
        income_statement["devoluciones_ventas_cop"] >= 0
    ).all()


def test_net_revenue_equation_is_correct(
    income_statement: pd.DataFrame,
) -> None:
    """Comprueba la ecuación de ingresos netos."""
    expected_net_revenue = (
        income_statement["ingresos_brutos_cop"]
        - income_statement["descuentos_cop"]
        - income_statement["devoluciones_ventas_cop"]
    )

    pd.testing.assert_series_equal(
        income_statement["ingresos_netos_cop"],
        expected_net_revenue,
        check_names=False,
    )


def test_cost_of_goods_sold_is_non_negative(
    income_statement: pd.DataFrame,
) -> None:
    """Comprueba que el costo de ventas no sea negativo."""
    assert (
        income_statement[
            "costo_mercancia_vendida_cop"
        ] >= 0
    ).all()


def test_gross_profit_equation_is_correct(
    income_statement: pd.DataFrame,
) -> None:
    """Comprueba la ecuación de utilidad bruta."""
    expected_gross_profit = (
        income_statement["ingresos_netos_cop"]
        - income_statement[
            "costo_mercancia_vendida_cop"
        ]
    )

    pd.testing.assert_series_equal(
        income_statement["utilidad_bruta_cop"],
        expected_gross_profit,
        check_names=False,
    )


def test_marketing_expense_matches_marketing_data(
    income_statement: pd.DataFrame,
    marketing: pd.DataFrame,
) -> None:
    """Comprueba el gasto mensual de marketing."""
    expected_marketing = (
        marketing.groupby(
            "periodo",
            as_index=False,
        )["inversion_cop"]
        .sum()
        .rename(
            columns={
                "inversion_cop": (
                    "gastos_marketing_esperados"
                )
            }
        )
    )

    comparison = income_statement.merge(
        expected_marketing,
        on="periodo",
        how="left",
        validate="one_to_one",
    )

    assert (
        comparison["gastos_marketing_cop"]
        == comparison["gastos_marketing_esperados"]
    ).all()


def test_operating_expenses_equation_is_correct(
    income_statement: pd.DataFrame,
) -> None:
    """Comprueba la suma de gastos operacionales."""
    expected_operating_expenses = (
        income_statement["gastos_marketing_cop"]
        + income_statement["gastos_logistica_cop"]
        + income_statement["gastos_plataforma_cop"]
        + income_statement["gastos_personal_cop"]
        + income_statement[
            "gastos_administrativos_cop"
        ]
        + income_statement["depreciacion_cop"]
    )

    pd.testing.assert_series_equal(
        income_statement[
            "total_gastos_operacionales_cop"
        ],
        expected_operating_expenses,
        check_names=False,
    )


def test_operating_profit_equation_is_correct(
    income_statement: pd.DataFrame,
) -> None:
    """Comprueba la ecuación de utilidad operacional."""
    expected_operating_profit = (
        income_statement["utilidad_bruta_cop"]
        - income_statement[
            "total_gastos_operacionales_cop"
        ]
    )

    pd.testing.assert_series_equal(
        income_statement[
            "utilidad_operacional_cop"
        ],
        expected_operating_profit,
        check_names=False,
    )


def test_profit_before_tax_equation_is_correct(
    income_statement: pd.DataFrame,
) -> None:
    """Comprueba la utilidad antes de impuestos."""
    expected_profit_before_tax = (
        income_statement[
            "utilidad_operacional_cop"
        ]
        + income_statement[
            "ingresos_no_operacionales_cop"
        ]
        - income_statement[
            "gastos_financieros_cop"
        ]
    )

    pd.testing.assert_series_equal(
        income_statement[
            "utilidad_antes_impuestos_cop"
        ],
        expected_profit_before_tax,
        check_names=False,
    )


def test_income_tax_is_non_negative(
    income_statement: pd.DataFrame,
) -> None:
    """Comprueba que el impuesto no sea negativo."""
    assert (
        income_statement["impuesto_cop"] >= 0
    ).all()


def test_income_tax_is_zero_when_profit_is_not_positive(
    income_statement: pd.DataFrame,
) -> None:
    """Comprueba el impuesto en periodos sin utilidad positiva."""
    non_positive_profit = income_statement[
        income_statement[
            "utilidad_antes_impuestos_cop"
        ] <= 0
    ]

    if not non_positive_profit.empty:
        assert (
            non_positive_profit["impuesto_cop"] == 0
        ).all()


def test_income_tax_matches_configured_rate(
    income_statement: pd.DataFrame,
) -> None:
    """Comprueba la tasa configurada de impuesto."""
    configuration = load_data_generation_config()

    tax_rate = configuration["finance"][
        "income_tax_rate"
    ]

    expected_tax = (
        income_statement[
            "utilidad_antes_impuestos_cop"
        ]
        .clip(lower=0)
        .mul(tax_rate)
        .round()
        .astype(int)
    )

    pd.testing.assert_series_equal(
        income_statement["impuesto_cop"],
        expected_tax,
        check_names=False,
    )


def test_net_profit_equation_is_correct(
    income_statement: pd.DataFrame,
) -> None:
    """Comprueba la ecuación de utilidad neta."""
    expected_net_profit = (
        income_statement[
            "utilidad_antes_impuestos_cop"
        ]
        - income_statement["impuesto_cop"]
    )

    pd.testing.assert_series_equal(
        income_statement["utilidad_neta_cop"],
        expected_net_profit,
        check_names=False,
    )


def test_gross_margin_is_correct(
    income_statement: pd.DataFrame,
) -> None:
    """Comprueba el margen bruto."""
    expected_margin = (
        income_statement["utilidad_bruta_cop"]
        / income_statement["ingresos_netos_cop"]
    ).round(4)

    pd.testing.assert_series_equal(
        income_statement["margen_bruto"],
        expected_margin,
        check_names=False,
    )


def test_operating_margin_is_correct(
    income_statement: pd.DataFrame,
) -> None:
    """Comprueba el margen operacional."""
    expected_margin = (
        income_statement[
            "utilidad_operacional_cop"
        ]
        / income_statement["ingresos_netos_cop"]
    ).round(4)

    pd.testing.assert_series_equal(
        income_statement["margen_operacional"],
        expected_margin,
        check_names=False,
    )


def test_net_margin_is_correct(
    income_statement: pd.DataFrame,
) -> None:
    """Comprueba el margen neto."""
    expected_margin = (
        income_statement["utilidad_neta_cop"]
        / income_statement["ingresos_netos_cop"]
    ).round(4)

    pd.testing.assert_series_equal(
        income_statement["margen_neto"],
        expected_margin,
        check_names=False,
    )


def test_all_income_statement_records_are_synthetic(
    income_statement: pd.DataFrame,
) -> None:
    """Comprueba la identificación como datos sintéticos."""
    assert income_statement["datos_sinteticos"].all()


def test_income_statement_is_reproducible(
    orders: pd.DataFrame,
    returns: pd.DataFrame,
    marketing: pd.DataFrame,
    income_statement: pd.DataFrame,
) -> None:
    """Comprueba que la misma semilla produzca el mismo resultado."""
    second_statement = generate_income_statement(
        orders=orders,
        returns=returns,
        marketing=marketing,
    )

    pd.testing.assert_frame_equal(
        income_statement,
        second_statement,
    )


def test_different_seed_changes_income_statement(
    orders: pd.DataFrame,
    returns: pd.DataFrame,
    marketing: pd.DataFrame,
    income_statement: pd.DataFrame,
) -> None:
    """Comprueba que otra semilla cambie partidas simuladas."""
    alternative_statement = generate_income_statement(
        orders=orders,
        returns=returns,
        marketing=marketing,
        random_seed=20261705,
    )

    assert not income_statement.equals(
        alternative_statement
    )