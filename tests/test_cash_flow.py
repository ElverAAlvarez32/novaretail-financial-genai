"""Pruebas automáticas del flujo de efectivo sintético."""

from __future__ import annotations

import pandas as pd
import pytest

from novaretail.config import load_data_generation_config
from novaretail.generation.balance_sheet import (
    generate_balance_sheet,
)
from novaretail.generation.cash_flow import (
    CASH_FLOW_COLUMNS,
    INITIAL_OPENING_CASH_COP,
    generate_cash_flow,
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


def test_cash_flow_has_expected_columns(
    cash_flow: pd.DataFrame,
) -> None:
    """Comprueba el nombre y orden de las columnas."""
    assert cash_flow.columns.tolist() == CASH_FLOW_COLUMNS


def test_cash_flow_has_expected_dimensions(
    cash_flow: pd.DataFrame,
) -> None:
    """Comprueba la cantidad de periodos y columnas."""
    configuration = load_data_generation_config()

    expected_months = pd.date_range(
        start=configuration["period"]["start_date"],
        end=configuration["period"]["end_date"],
        freq="MS",
    ).size

    assert cash_flow.shape == (
        expected_months,
        len(CASH_FLOW_COLUMNS),
    )


def test_cash_flow_contains_expected_periods(
    cash_flow: pd.DataFrame,
) -> None:
    """Comprueba la cobertura temporal completa."""
    configuration = load_data_generation_config()

    expected_periods = pd.date_range(
        start=configuration["period"]["start_date"],
        end=configuration["period"]["end_date"],
        freq="MS",
    ).strftime("%Y-%m")

    assert cash_flow["periodo"].tolist() == (
        expected_periods.tolist()
    )


def test_cash_flow_periods_are_unique(
    cash_flow: pd.DataFrame,
) -> None:
    """Comprueba que no existan periodos duplicados."""
    assert cash_flow["periodo"].is_unique


def test_cash_flow_year_matches_period(
    cash_flow: pd.DataFrame,
) -> None:
    """Comprueba el año correspondiente a cada periodo."""
    expected_year = pd.to_datetime(
        cash_flow["periodo"] + "-01"
    ).dt.year

    pd.testing.assert_series_equal(
        cash_flow["anio"],
        expected_year,
        check_names=False,
        check_dtype=False,
    )


def test_cash_flow_month_matches_period(
    cash_flow: pd.DataFrame,
) -> None:
    """Comprueba el mes correspondiente a cada periodo."""
    expected_month = pd.to_datetime(
        cash_flow["periodo"] + "-01"
    ).dt.month

    pd.testing.assert_series_equal(
        cash_flow["mes"],
        expected_month,
        check_names=False,
        check_dtype=False,
    )


def test_net_profit_matches_income_statement(
    cash_flow: pd.DataFrame,
    income_statement: pd.DataFrame,
) -> None:
    """Comprueba la utilidad neta tomada del estado de resultados."""
    comparison = cash_flow.merge(
        income_statement[
            [
                "periodo",
                "utilidad_neta_cop",
            ]
        ].rename(
            columns={
                "utilidad_neta_cop":
                    "utilidad_neta_esperada_cop",
            }
        ),
        on="periodo",
        how="left",
        validate="one_to_one",
    )

    assert (
        comparison["utilidad_neta_cop"]
        == comparison["utilidad_neta_esperada_cop"]
    ).all()


def test_depreciation_matches_income_statement(
    cash_flow: pd.DataFrame,
    income_statement: pd.DataFrame,
) -> None:
    """Comprueba la depreciación tomada del estado de resultados."""
    comparison = cash_flow.merge(
        income_statement[
            [
                "periodo",
                "depreciacion_cop",
            ]
        ].rename(
            columns={
                "depreciacion_cop":
                    "depreciacion_esperada_cop",
            }
        ),
        on="periodo",
        how="left",
        validate="one_to_one",
    )

    assert (
        comparison["depreciacion_cop"]
        == comparison["depreciacion_esperada_cop"]
    ).all()


def test_operating_cash_flow_equation_is_correct(
    cash_flow: pd.DataFrame,
) -> None:
    """Comprueba la ecuación del flujo de operación."""
    expected_operating_cash_flow = (
        cash_flow["utilidad_neta_cop"]
        + cash_flow["depreciacion_cop"]
        - cash_flow[
            "variacion_cuentas_por_cobrar_cop"
        ]
        - cash_flow["variacion_inventarios_cop"]
        - cash_flow[
            "variacion_otros_activos_corrientes_cop"
        ]
        + cash_flow["variacion_proveedores_cop"]
        + cash_flow[
            "variacion_impuestos_por_pagar_cop"
        ]
        + cash_flow[
            "variacion_otros_pasivos_corrientes_cop"
        ]
        + cash_flow["otros_ajustes_operativos_cop"]
    )

    pd.testing.assert_series_equal(
        cash_flow["flujo_operacion_cop"],
        expected_operating_cash_flow,
        check_names=False,
    )


def test_investing_cash_flow_equation_is_correct(
    cash_flow: pd.DataFrame,
) -> None:
    """Comprueba la ecuación del flujo de inversión."""
    expected_investing_cash_flow = (
        -cash_flow["compras_activos_fijos_cop"]
        + cash_flow["venta_activos_cop"]
        - cash_flow[
            "variacion_otros_activos_no_corrientes_cop"
        ]
    )

    pd.testing.assert_series_equal(
        cash_flow["flujo_inversion_cop"],
        expected_investing_cash_flow,
        check_names=False,
    )


def test_financing_cash_flow_equation_is_correct(
    cash_flow: pd.DataFrame,
) -> None:
    """Comprueba la ecuación del flujo de financiación."""
    expected_financing_cash_flow = (
        cash_flow["nuevos_prestamos_cop"]
        - cash_flow["pago_capital_deuda_cop"]
        + cash_flow["aportes_capital_cop"]
        - cash_flow["dividendos_cop"]
        + cash_flow[
            "variacion_otros_pasivos_no_corrientes_cop"
        ]
    )

    pd.testing.assert_series_equal(
        cash_flow["flujo_financiacion_cop"],
        expected_financing_cash_flow,
        check_names=False,
    )


def test_net_cash_change_equation_is_correct(
    cash_flow: pd.DataFrame,
) -> None:
    """Comprueba la variación neta del efectivo."""
    expected_net_cash_change = (
        cash_flow["flujo_operacion_cop"]
        + cash_flow["flujo_inversion_cop"]
        + cash_flow["flujo_financiacion_cop"]
        + cash_flow["ajuste_conciliacion_cop"]
    )

    pd.testing.assert_series_equal(
        cash_flow["variacion_neta_efectivo_cop"],
        expected_net_cash_change,
        check_names=False,
    )


def test_opening_cash_starts_with_configured_value(
    cash_flow: pd.DataFrame,
) -> None:
    """Comprueba el efectivo inicial del primer periodo."""
    assert (
        cash_flow.iloc[0]["efectivo_inicial_cop"]
        == INITIAL_OPENING_CASH_COP
    )


def test_closing_cash_equation_is_correct(
    cash_flow: pd.DataFrame,
) -> None:
    """Comprueba efectivo inicial más variación neta."""
    expected_closing_cash = (
        cash_flow["efectivo_inicial_cop"]
        + cash_flow["variacion_neta_efectivo_cop"]
    )

    pd.testing.assert_series_equal(
        cash_flow["efectivo_final_cop"],
        expected_closing_cash,
        check_names=False,
    )


def test_closing_cash_matches_balance_sheet(
    cash_flow: pd.DataFrame,
    balance_sheet: pd.DataFrame,
) -> None:
    """Comprueba el efectivo final frente al balance."""
    comparison = cash_flow.merge(
        balance_sheet[
            [
                "periodo",
                "efectivo_cop",
            ]
        ].rename(
            columns={
                "efectivo_cop":
                    "efectivo_balance_cop",
            }
        ),
        on="periodo",
        how="left",
        validate="one_to_one",
    )

    assert (
        comparison["efectivo_final_cop"]
        == comparison["efectivo_balance_cop"]
    ).all()


def test_cash_continuity_between_periods(
    cash_flow: pd.DataFrame,
) -> None:
    """Comprueba cierre de un mes frente a apertura del siguiente."""
    previous_closing_cash = (
        cash_flow["efectivo_final_cop"]
        .shift(1)
    )

    comparable_rows = previous_closing_cash.notna()

    assert (
        cash_flow.loc[
            comparable_rows,
            "efectivo_inicial_cop",
        ].to_numpy()
        == previous_closing_cash.loc[
            comparable_rows
        ].to_numpy()
    ).all()


def test_reconciliation_difference_is_zero(
    cash_flow: pd.DataFrame,
) -> None:
    """Comprueba que no existan diferencias de conciliación."""
    assert (
        cash_flow["diferencia_conciliacion_cop"] == 0
    ).all()


def test_asset_purchases_are_non_negative(
    cash_flow: pd.DataFrame,
) -> None:
    """Comprueba que las compras de activos sean no negativas."""
    assert (
        cash_flow["compras_activos_fijos_cop"] >= 0
    ).all()


def test_asset_sales_are_non_negative(
    cash_flow: pd.DataFrame,
) -> None:
    """Comprueba que las ventas de activos sean no negativas."""
    assert (
        cash_flow["venta_activos_cop"] >= 0
    ).all()


def test_new_debt_is_non_negative(
    cash_flow: pd.DataFrame,
) -> None:
    """Comprueba que los nuevos préstamos sean no negativos."""
    assert (
        cash_flow["nuevos_prestamos_cop"] >= 0
    ).all()


def test_debt_payments_are_non_negative(
    cash_flow: pd.DataFrame,
) -> None:
    """Comprueba que los pagos de deuda sean no negativos."""
    assert (
        cash_flow["pago_capital_deuda_cop"] >= 0
    ).all()


def test_capital_contributions_are_non_negative(
    cash_flow: pd.DataFrame,
) -> None:
    """Comprueba que los aportes de capital sean no negativos."""
    assert (
        cash_flow["aportes_capital_cop"] >= 0
    ).all()


def test_dividends_are_non_negative(
    cash_flow: pd.DataFrame,
) -> None:
    """Comprueba que los dividendos sean no negativos."""
    assert (
        cash_flow["dividendos_cop"] >= 0
    ).all()


def test_opening_and_closing_cash_are_non_negative(
    cash_flow: pd.DataFrame,
) -> None:
    """Comprueba que los saldos de efectivo sean no negativos."""
    assert (
        cash_flow["efectivo_inicial_cop"] >= 0
    ).all()

    assert (
        cash_flow["efectivo_final_cop"] >= 0
    ).all()


def test_all_cash_flow_records_are_synthetic(
    cash_flow: pd.DataFrame,
) -> None:
    """Comprueba la identificación como datos sintéticos."""
    assert cash_flow["datos_sinteticos"].all()


def test_cash_flow_is_reproducible(
    income_statement: pd.DataFrame,
    balance_sheet: pd.DataFrame,
    cash_flow: pd.DataFrame,
) -> None:
    """Comprueba que las mismas entradas produzcan el mismo flujo."""
    second_cash_flow = generate_cash_flow(
        income_statement=income_statement,
        balance_sheet=balance_sheet,
    )

    pd.testing.assert_frame_equal(
        cash_flow,
        second_cash_flow,
    )
    