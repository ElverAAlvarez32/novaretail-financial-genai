"""Pruebas automáticas del balance general sintético."""

from __future__ import annotations

import pandas as pd
import pytest

from novaretail.config import load_data_generation_config
from novaretail.generation.balance_sheet import (
    BALANCE_SHEET_COLUMNS,
    generate_balance_sheet,
)
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
    return generate_returns(orders=orders)


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


def test_balance_sheet_has_expected_columns(
    balance_sheet: pd.DataFrame,
) -> None:
    """Comprueba el nombre y orden de las columnas."""
    assert (
        balance_sheet.columns.tolist()
        == BALANCE_SHEET_COLUMNS
    )


def test_balance_sheet_has_expected_dimensions(
    balance_sheet: pd.DataFrame,
) -> None:
    """Comprueba la cantidad de periodos y columnas."""
    configuration = load_data_generation_config()

    expected_months = pd.date_range(
        start=configuration["period"]["start_date"],
        end=configuration["period"]["end_date"],
        freq="MS",
    ).size

    assert balance_sheet.shape == (
        expected_months,
        len(BALANCE_SHEET_COLUMNS),
    )


def test_balance_sheet_contains_expected_periods(
    balance_sheet: pd.DataFrame,
) -> None:
    """Comprueba la cobertura temporal completa."""
    configuration = load_data_generation_config()

    expected_periods = pd.date_range(
        start=configuration["period"]["start_date"],
        end=configuration["period"]["end_date"],
        freq="MS",
    ).strftime("%Y-%m")

    assert balance_sheet["periodo"].tolist() == (
        expected_periods.tolist()
    )


def test_balance_sheet_periods_are_unique(
    balance_sheet: pd.DataFrame,
) -> None:
    """Comprueba que no existan periodos duplicados."""
    assert balance_sheet["periodo"].is_unique


def test_balance_year_matches_period(
    balance_sheet: pd.DataFrame,
) -> None:
    """Comprueba el año de cada periodo."""
    expected_year = pd.to_datetime(
        balance_sheet["periodo"] + "-01"
    ).dt.year

    pd.testing.assert_series_equal(
        balance_sheet["anio"],
        expected_year,
        check_names=False,
        check_dtype=False,
    )


def test_balance_month_matches_period(
    balance_sheet: pd.DataFrame,
) -> None:
    """Comprueba el mes de cada periodo."""
    expected_month = pd.to_datetime(
        balance_sheet["periodo"] + "-01"
    ).dt.month

    pd.testing.assert_series_equal(
        balance_sheet["mes"],
        expected_month,
        check_names=False,
        check_dtype=False,
    )


def test_cash_meets_configured_minimum(
    balance_sheet: pd.DataFrame,
) -> None:
    """Comprueba el saldo mínimo de efectivo."""
    configuration = load_data_generation_config()

    minimum_cash = configuration["finance"][
        "minimum_cash_balance_cop"
    ]

    assert (
        balance_sheet["efectivo_cop"]
        >= minimum_cash
    ).all()


def test_inventory_matches_monthly_inventory_data(
    balance_sheet: pd.DataFrame,
    inventory: pd.DataFrame,
) -> None:
    """Comprueba el valor mensual de inventarios."""
    expected_inventory = (
        inventory.groupby(
            "periodo",
            as_index=False,
        )["valor_inventario_final_cop"]
        .sum()
        .rename(
            columns={
                "valor_inventario_final_cop":
                "inventario_esperado_cop"
            }
        )
    )

    comparison = balance_sheet.merge(
        expected_inventory,
        on="periodo",
        how="left",
        validate="one_to_one",
    )

    assert (
        comparison["inventarios_cop"]
        == comparison["inventario_esperado_cop"]
    ).all()


def test_current_assets_equation_is_correct(
    balance_sheet: pd.DataFrame,
) -> None:
    """Comprueba el total de activos corrientes."""
    expected_total = (
        balance_sheet["efectivo_cop"]
        + balance_sheet["cuentas_por_cobrar_cop"]
        + balance_sheet["inventarios_cop"]
        + balance_sheet[
            "otros_activos_corrientes_cop"
        ]
    )

    pd.testing.assert_series_equal(
        balance_sheet["total_activo_corriente_cop"],
        expected_total,
        check_names=False,
    )


def test_accumulated_depreciation_is_non_decreasing(
    balance_sheet: pd.DataFrame,
) -> None:
    """Comprueba la evolución de la depreciación acumulada."""
    differences = balance_sheet[
        "depreciacion_acumulada_cop"
    ].diff().dropna()

    assert (differences >= 0).all()


def test_gross_property_is_non_decreasing(
    balance_sheet: pd.DataFrame,
) -> None:
    """Comprueba la evolución del activo fijo bruto."""
    differences = balance_sheet[
        "propiedad_planta_equipo_bruto_cop"
    ].diff().dropna()

    assert (differences >= 0).all()


def test_net_property_equation_is_correct(
    balance_sheet: pd.DataFrame,
) -> None:
    """Comprueba la propiedad, planta y equipo neta."""
    expected_net_property = (
        balance_sheet[
            "propiedad_planta_equipo_bruto_cop"
        ]
        - balance_sheet[
            "depreciacion_acumulada_cop"
        ]
    )

    pd.testing.assert_series_equal(
        balance_sheet[
            "propiedad_planta_equipo_neto_cop"
        ],
        expected_net_property,
        check_names=False,
    )


def test_non_current_assets_equation_is_correct(
    balance_sheet: pd.DataFrame,
) -> None:
    """Comprueba el total de activos no corrientes."""
    expected_total = (
        balance_sheet[
            "propiedad_planta_equipo_neto_cop"
        ]
        + balance_sheet[
            "otros_activos_no_corrientes_cop"
        ]
    )

    pd.testing.assert_series_equal(
        balance_sheet[
            "total_activo_no_corriente_cop"
        ],
        expected_total,
        check_names=False,
    )


def test_total_assets_equation_is_correct(
    balance_sheet: pd.DataFrame,
) -> None:
    """Comprueba el total de activos."""
    expected_total = (
        balance_sheet["total_activo_corriente_cop"]
        + balance_sheet[
            "total_activo_no_corriente_cop"
        ]
    )

    pd.testing.assert_series_equal(
        balance_sheet["total_activos_cop"],
        expected_total,
        check_names=False,
    )


def test_current_liabilities_equation_is_correct(
    balance_sheet: pd.DataFrame,
) -> None:
    """Comprueba el total de pasivos corrientes."""
    expected_total = (
        balance_sheet["proveedores_cop"]
        + balance_sheet[
            "obligaciones_financieras_corto_plazo_cop"
        ]
        + balance_sheet["impuestos_por_pagar_cop"]
        + balance_sheet[
            "otros_pasivos_corrientes_cop"
        ]
    )

    pd.testing.assert_series_equal(
        balance_sheet["total_pasivo_corriente_cop"],
        expected_total,
        check_names=False,
    )


def test_non_current_liabilities_equation_is_correct(
    balance_sheet: pd.DataFrame,
) -> None:
    """Comprueba el total de pasivos no corrientes."""
    expected_total = (
        balance_sheet[
            "obligaciones_financieras_largo_plazo_cop"
        ]
        + balance_sheet[
            "otros_pasivos_no_corrientes_cop"
        ]
    )

    pd.testing.assert_series_equal(
        balance_sheet[
            "total_pasivo_no_corriente_cop"
        ],
        expected_total,
        check_names=False,
    )


def test_total_liabilities_equation_is_correct(
    balance_sheet: pd.DataFrame,
) -> None:
    """Comprueba el total de pasivos."""
    expected_total = (
        balance_sheet["total_pasivo_corriente_cop"]
        + balance_sheet[
            "total_pasivo_no_corriente_cop"
        ]
    )

    pd.testing.assert_series_equal(
        balance_sheet["total_pasivos_cop"],
        expected_total,
        check_names=False,
    )


def test_share_capital_matches_configuration(
    balance_sheet: pd.DataFrame,
) -> None:
    """Comprueba el capital social configurado."""
    configuration = load_data_generation_config()

    expected_capital = configuration["finance"][
        "initial_equity_cop"
    ]

    assert (
        balance_sheet["capital_social_cop"]
        == expected_capital
    ).all()


def test_period_result_matches_net_profit(
    balance_sheet: pd.DataFrame,
    income_statement: pd.DataFrame,
) -> None:
    """Comprueba el resultado del periodo."""
    comparison = balance_sheet.merge(
        income_statement[
            ["periodo", "utilidad_neta_cop"]
        ],
        on="periodo",
        how="left",
        validate="one_to_one",
    )

    assert (
        comparison["resultado_periodo_cop"]
        == comparison["utilidad_neta_cop"]
    ).all()


def test_retained_earnings_are_correct(
    balance_sheet: pd.DataFrame,
    income_statement: pd.DataFrame,
) -> None:
    """Comprueba la utilidad acumulada anterior."""
    ordered_income = income_statement.sort_values(
        "periodo"
    )

    expected_retained_earnings = (
        ordered_income["utilidad_neta_cop"]
        .cumsum()
        .shift(1)
        .fillna(0)
        .astype(int)
        .reset_index(drop=True)
    )

    actual_retained_earnings = (
        balance_sheet.sort_values("periodo")[
            "utilidades_retenidas_cop"
        ]
        .reset_index(drop=True)
    )

    pd.testing.assert_series_equal(
        actual_retained_earnings,
        expected_retained_earnings,
        check_names=False,
    )


def test_equity_equation_is_correct(
    balance_sheet: pd.DataFrame,
) -> None:
    """Comprueba el total de patrimonio."""
    expected_equity = (
        balance_sheet["capital_social_cop"]
        + balance_sheet[
            "utilidades_retenidas_cop"
        ]
        + balance_sheet["resultado_periodo_cop"]
    )

    pd.testing.assert_series_equal(
        balance_sheet["total_patrimonio_cop"],
        expected_equity,
        check_names=False,
    )


def test_liabilities_and_equity_equation_is_correct(
    balance_sheet: pd.DataFrame,
) -> None:
    """Comprueba pasivos más patrimonio."""
    expected_total = (
        balance_sheet["total_pasivos_cop"]
        + balance_sheet["total_patrimonio_cop"]
    )

    pd.testing.assert_series_equal(
        balance_sheet[
            "total_pasivo_patrimonio_cop"
        ],
        expected_total,
        check_names=False,
    )


def test_accounting_equation_is_balanced(
    balance_sheet: pd.DataFrame,
) -> None:
    """Comprueba activos igual a pasivos más patrimonio."""
    assert (
        balance_sheet["total_activos_cop"]
        == balance_sheet[
            "total_pasivo_patrimonio_cop"
        ]
    ).all()


def test_balance_difference_is_zero(
    balance_sheet: pd.DataFrame,
) -> None:
    """Comprueba que no existan diferencias contables."""
    assert (
        balance_sheet["diferencia_balance_cop"] == 0
    ).all()


def test_balance_monetary_values_are_non_negative(
    balance_sheet: pd.DataFrame,
) -> None:
    """Comprueba que las partidas monetarias sean no negativas."""
    monetary_columns = [
        column
        for column in BALANCE_SHEET_COLUMNS
        if column.endswith("_cop")
        and column != "diferencia_balance_cop"
    ]

    assert not (
        balance_sheet[monetary_columns] < 0
    ).any().any()


def test_all_balance_records_are_synthetic(
    balance_sheet: pd.DataFrame,
) -> None:
    """Comprueba la identificación como datos sintéticos."""
    assert balance_sheet["datos_sinteticos"].all()


def test_balance_sheet_is_reproducible(
    income_statement: pd.DataFrame,
    inventory: pd.DataFrame,
    balance_sheet: pd.DataFrame,
) -> None:
    """Comprueba que la misma semilla produzca el mismo balance."""
    second_balance = generate_balance_sheet(
        income_statement=income_statement,
        inventory=inventory,
    )

    pd.testing.assert_frame_equal(
        balance_sheet,
        second_balance,
    )


def test_different_seed_changes_balance_sheet(
    income_statement: pd.DataFrame,
    inventory: pd.DataFrame,
    balance_sheet: pd.DataFrame,
) -> None:
    """Comprueba que otra semilla cambie partidas simuladas."""
    alternative_balance = generate_balance_sheet(
        income_statement=income_statement,
        inventory=inventory,
        random_seed=20261805,
    )

    assert not balance_sheet.equals(
        alternative_balance
    )