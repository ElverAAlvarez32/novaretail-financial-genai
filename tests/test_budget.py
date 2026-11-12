"""Pruebas automáticas del presupuesto mensual sintético."""

from __future__ import annotations

import pandas as pd
import pytest

from novaretail.config import load_data_generation_config
from novaretail.generation.balance_sheet import (
    generate_balance_sheet,
)
from novaretail.generation.budget import (
    ACCEPTABLE_DEVIATION_RATE,
    BUDGET_COLUMNS,
    CATEGORY_DEFINITIONS,
    MODERATE_DEVIATION_RATE,
    generate_budget,
)
from novaretail.generation.cash_flow import generate_cash_flow
from novaretail.generation.customers import generate_customers
from novaretail.generation.financial_statements import (
    generate_income_statement,
)
from novaretail.generation.inventory import generate_inventory
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
    return generate_returns(
        orders=orders,
    )


@pytest.fixture(scope="module")
def marketing() -> pd.DataFrame:
    """Genera una sola vez los datos de marketing."""
    return generate_marketing()


@pytest.fixture(scope="module")
def inventory(
    products: pd.DataFrame,
    orders: pd.DataFrame,
) -> pd.DataFrame:
    """Genera una sola vez el inventario mensual."""
    return generate_inventory(
        products=products,
        orders=orders,
    )


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


@pytest.fixture(scope="module")
def balance_sheet(
    income_statement: pd.DataFrame,
    inventory: pd.DataFrame,
) -> pd.DataFrame:
    """Genera una sola vez el balance general."""
    return generate_balance_sheet(
        income_statement=income_statement,
        inventory=inventory,
    )


@pytest.fixture(scope="module")
def cash_flow(
    income_statement: pd.DataFrame,
    balance_sheet: pd.DataFrame,
) -> pd.DataFrame:
    """Genera una sola vez el flujo de efectivo."""
    return generate_cash_flow(
        income_statement=income_statement,
        balance_sheet=balance_sheet,
    )


@pytest.fixture(scope="module")
def budget(
    income_statement: pd.DataFrame,
    cash_flow: pd.DataFrame,
) -> pd.DataFrame:
    """Genera una sola vez el presupuesto mensual."""
    return generate_budget(
        income_statement=income_statement,
        cash_flow=cash_flow,
    )


def test_budget_has_expected_columns(
    budget: pd.DataFrame,
) -> None:
    """Comprueba el nombre y orden de las columnas."""
    assert budget.columns.tolist() == BUDGET_COLUMNS


def test_budget_has_expected_dimensions(
    budget: pd.DataFrame,
) -> None:
    """Comprueba la cantidad de registros presupuestales."""
    configuration = load_data_generation_config()

    expected_months = pd.date_range(
        start=configuration["period"]["start_date"],
        end=configuration["period"]["end_date"],
        freq="MS",
    ).size

    expected_categories = len(CATEGORY_DEFINITIONS)

    assert budget.shape == (
        expected_months * expected_categories,
        len(BUDGET_COLUMNS),
    )


def test_budget_contains_expected_periods(
    budget: pd.DataFrame,
) -> None:
    """Comprueba la cobertura temporal completa."""
    configuration = load_data_generation_config()

    expected_periods = set(
        pd.date_range(
            start=configuration["period"]["start_date"],
            end=configuration["period"]["end_date"],
            freq="MS",
        ).strftime("%Y-%m")
    )

    generated_periods = set(
        budget["periodo"].unique()
    )

    assert generated_periods == expected_periods


def test_budget_contains_expected_categories(
    budget: pd.DataFrame,
) -> None:
    """Comprueba las categorías presupuestales."""
    expected_categories = set(CATEGORY_DEFINITIONS)

    generated_categories = set(
        budget["categoria"].unique()
    )

    assert generated_categories == expected_categories


def test_each_period_contains_all_categories(
    budget: pd.DataFrame,
) -> None:
    """Comprueba la cantidad de categorías por periodo."""
    expected_categories = len(CATEGORY_DEFINITIONS)

    categories_per_period = budget.groupby(
        "periodo"
    )["categoria"].nunique()

    assert (
        categories_per_period == expected_categories
    ).all()


def test_budget_identifiers_are_unique(
    budget: pd.DataFrame,
) -> None:
    """Comprueba la integridad de los identificadores."""
    assert budget["presupuesto_id"].notna().all()
    assert budget["presupuesto_id"].is_unique
    assert budget["presupuesto_id"].str.match(
        r"^PRE-\d{5}$"
    ).all()


def test_budget_has_one_record_per_period_and_category(
    budget: pd.DataFrame,
) -> None:
    """Comprueba la unicidad de periodo y categoría."""
    duplicated_records = budget.duplicated(
        subset=["periodo", "categoria"]
    )

    assert not duplicated_records.any()


def test_budget_year_matches_period(
    budget: pd.DataFrame,
) -> None:
    """Comprueba el año correspondiente a cada periodo."""
    expected_year = pd.to_datetime(
        budget["periodo"] + "-01"
    ).dt.year

    pd.testing.assert_series_equal(
        budget["anio"],
        expected_year,
        check_names=False,
        check_dtype=False,
    )


def test_budget_month_matches_period(
    budget: pd.DataFrame,
) -> None:
    """Comprueba el mes correspondiente a cada periodo."""
    expected_month = pd.to_datetime(
        budget["periodo"] + "-01"
    ).dt.month

    pd.testing.assert_series_equal(
        budget["mes"],
        expected_month,
        check_names=False,
        check_dtype=False,
    )


def test_budgeted_values_are_positive(
    budget: pd.DataFrame,
) -> None:
    """Comprueba que los valores presupuestados sean positivos."""
    assert (
        budget["valor_presupuestado_cop"] > 0
    ).all()


def test_executed_values_are_non_negative(
    budget: pd.DataFrame,
) -> None:
    """Comprueba que los valores ejecutados no sean negativos."""
    assert (
        budget["valor_ejecutado_cop"] >= 0
    ).all()


def test_absolute_variation_is_correct(
    budget: pd.DataFrame,
) -> None:
    """Comprueba la variación absoluta."""
    expected_variation = (
        budget["valor_ejecutado_cop"]
        - budget["valor_presupuestado_cop"]
    )

    pd.testing.assert_series_equal(
        budget["variacion_absoluta_cop"],
        expected_variation,
        check_names=False,
    )


def test_percentage_variation_is_correct(
    budget: pd.DataFrame,
) -> None:
    """Comprueba la variación porcentual."""
    expected_variation = (
        budget["variacion_absoluta_cop"]
        / budget["valor_presupuestado_cop"]
    ).round(4)

    pd.testing.assert_series_equal(
        budget["variacion_porcentual"],
        expected_variation,
        check_names=False,
    )


def test_deviation_status_is_correct(
    budget: pd.DataFrame,
) -> None:
    """Comprueba la clasificación de las desviaciones."""
    absolute_variation = (
        budget["variacion_porcentual"].abs()
    )

    expected_status = pd.Series(
        "Desviación significativa",
        index=budget.index,
        dtype="object",
    )

    expected_status.loc[
        absolute_variation <= MODERATE_DEVIATION_RATE
    ] = "Desviación moderada"

    expected_status.loc[
        absolute_variation <= ACCEPTABLE_DEVIATION_RATE
    ] = "Dentro del rango"

    pd.testing.assert_series_equal(
        budget["estado_desviacion"],
        expected_status,
        check_names=False,
    )


def test_budget_natures_are_authorized(
    budget: pd.DataFrame,
) -> None:
    """Comprueba las naturalezas presupuestales."""
    allowed_natures = {
        "Ingreso",
        "Egreso",
    }

    generated_natures = set(
        budget["naturaleza"].unique()
    )

    assert generated_natures.issubset(
        allowed_natures
    )


def test_budget_impacts_are_authorized(
    budget: pd.DataFrame,
) -> None:
    """Comprueba los impactos presupuestales."""
    allowed_impacts = {
        "Favorable",
        "Desfavorable",
        "Neutral",
    }

    generated_impacts = set(
        budget["impacto_presupuestal"].unique()
    )

    assert generated_impacts.issubset(
        allowed_impacts
    )


def test_income_favorable_impact_is_correct(
    budget: pd.DataFrame,
) -> None:
    """Comprueba el impacto favorable en ingresos."""
    favorable_income = budget[
        (budget["naturaleza"] == "Ingreso")
        & (budget["variacion_absoluta_cop"] > 0)
    ]

    if not favorable_income.empty:
        assert (
            favorable_income["impacto_presupuestal"]
            == "Favorable"
        ).all()


def test_income_unfavorable_impact_is_correct(
    budget: pd.DataFrame,
) -> None:
    """Comprueba el impacto desfavorable en ingresos."""
    unfavorable_income = budget[
        (budget["naturaleza"] == "Ingreso")
        & (budget["variacion_absoluta_cop"] < 0)
    ]

    if not unfavorable_income.empty:
        assert (
            unfavorable_income["impacto_presupuestal"]
            == "Desfavorable"
        ).all()


def test_expense_favorable_impact_is_correct(
    budget: pd.DataFrame,
) -> None:
    """Comprueba el impacto favorable en egresos."""
    favorable_expense = budget[
        (budget["naturaleza"] == "Egreso")
        & (budget["variacion_absoluta_cop"] < 0)
    ]

    if not favorable_expense.empty:
        assert (
            favorable_expense["impacto_presupuestal"]
            == "Favorable"
        ).all()


def test_expense_unfavorable_impact_is_correct(
    budget: pd.DataFrame,
) -> None:
    """Comprueba el impacto desfavorable en egresos."""
    unfavorable_expense = budget[
        (budget["naturaleza"] == "Egreso")
        & (budget["variacion_absoluta_cop"] > 0)
    ]

    if not unfavorable_expense.empty:
        assert (
            unfavorable_expense["impacto_presupuestal"]
            == "Desfavorable"
        ).all()


def test_executed_values_match_income_statement(
    budget: pd.DataFrame,
    income_statement: pd.DataFrame,
) -> None:
    """Comprueba las categorías provenientes del estado de resultados."""
    income_categories = {
        category: definition
        for category, definition in CATEGORY_DEFINITIONS.items()
        if definition["source"]
        != "compras_activos_fijos_cop"
    }

    for category, definition in income_categories.items():
        source_column = definition["source"]

        category_budget = (
            budget[
                budget["categoria"] == category
            ][
                [
                    "periodo",
                    "valor_ejecutado_cop",
                ]
            ]
        )

        reference = income_statement[
            [
                "periodo",
                source_column,
            ]
        ].rename(
            columns={
                source_column:
                    "valor_esperado_cop",
            }
        )

        comparison = category_budget.merge(
            reference,
            on="periodo",
            how="left",
            validate="one_to_one",
        )

        assert (
            comparison["valor_ejecutado_cop"]
            == comparison["valor_esperado_cop"]
        ).all()


def test_investment_values_match_cash_flow(
    budget: pd.DataFrame,
    cash_flow: pd.DataFrame,
) -> None:
    """Comprueba la categoría de inversiones."""
    investment_budget = budget[
        budget["categoria"] == "Inversiones"
    ][
        [
            "periodo",
            "valor_ejecutado_cop",
        ]
    ]

    reference = cash_flow[
        [
            "periodo",
            "compras_activos_fijos_cop",
        ]
    ].rename(
        columns={
            "compras_activos_fijos_cop":
                "valor_esperado_cop",
        }
    )

    comparison = investment_budget.merge(
        reference,
        on="periodo",
        how="left",
        validate="one_to_one",
    )

    assert (
        comparison["valor_ejecutado_cop"]
        == comparison["valor_esperado_cop"]
    ).all()


def test_cost_centers_match_category_definitions(
    budget: pd.DataFrame,
) -> None:
    """Comprueba el centro de costo de cada categoría."""
    for category, definition in CATEGORY_DEFINITIONS.items():
        category_records = budget[
            budget["categoria"] == category
        ]

        assert (
            category_records["centro_costo"]
            == definition["cost_center"]
        ).all()


def test_responsibles_match_category_definitions(
    budget: pd.DataFrame,
) -> None:
    """Comprueba el responsable simulado de cada categoría."""
    for category, definition in CATEGORY_DEFINITIONS.items():
        category_records = budget[
            budget["categoria"] == category
        ]

        assert (
            category_records["responsable_simulado"]
            == definition["responsible"]
        ).all()


def test_all_budget_records_are_synthetic(
    budget: pd.DataFrame,
) -> None:
    """Comprueba la identificación como datos sintéticos."""
    assert budget["datos_sinteticos"].all()


def test_budget_is_reproducible(
    income_statement: pd.DataFrame,
    cash_flow: pd.DataFrame,
    budget: pd.DataFrame,
) -> None:
    """Comprueba que la misma semilla produzca el mismo presupuesto."""
    second_budget = generate_budget(
        income_statement=income_statement,
        cash_flow=cash_flow,
    )

    pd.testing.assert_frame_equal(
        budget,
        second_budget,
    )


def test_different_seed_changes_budget(
    income_statement: pd.DataFrame,
    cash_flow: pd.DataFrame,
    budget: pd.DataFrame,
) -> None:
    """Comprueba que otra semilla cambie el presupuesto."""
    alternative_budget = generate_budget(
        income_statement=income_statement,
        cash_flow=cash_flow,
        random_seed=20261905,
    )

    assert not budget.equals(
        alternative_budget
    )