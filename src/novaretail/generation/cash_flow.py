"""Generación reproducible del flujo de efectivo sintético.

Este módulo construye el flujo de efectivo mensual de la empresa
ficticia NovaRetail Colombia S.A.S. utilizando el método indirecto.

El flujo se deriva del estado de resultados y de las variaciones
mensuales del balance general. La variación neta del efectivo se
concilia con los saldos inicial y final de efectivo.

Todos los datos son sintéticos y de uso exclusivamente académico.
"""

from __future__ import annotations

import pandas as pd

from novaretail.logging_config import get_logger


LOGGER = get_logger(__name__)


CASH_FLOW_COLUMNS = [
    "periodo",
    "anio",
    "mes",
    "utilidad_neta_cop",
    "depreciacion_cop",
    "variacion_cuentas_por_cobrar_cop",
    "variacion_inventarios_cop",
    "variacion_otros_activos_corrientes_cop",
    "variacion_proveedores_cop",
    "variacion_impuestos_por_pagar_cop",
    "variacion_otros_pasivos_corrientes_cop",
    "otros_ajustes_operativos_cop",
    "flujo_operacion_cop",
    "compras_activos_fijos_cop",
    "venta_activos_cop",
    "variacion_otros_activos_no_corrientes_cop",
    "flujo_inversion_cop",
    "nuevos_prestamos_cop",
    "pago_capital_deuda_cop",
    "aportes_capital_cop",
    "dividendos_cop",
    "variacion_otros_pasivos_no_corrientes_cop",
    "flujo_financiacion_cop",
    "ajuste_conciliacion_cop",
    "variacion_neta_efectivo_cop",
    "efectivo_inicial_cop",
    "efectivo_final_cop",
    "diferencia_conciliacion_cop",
    "datos_sinteticos",
]


INITIAL_OPENING_CASH_COP = 150_000_000


def _validate_input_data(
    income_statement: pd.DataFrame,
    balance_sheet: pd.DataFrame,
) -> None:
    """Valida las tablas requeridas para generar el flujo.

    Args:
        income_statement: Estado de resultados mensual.
        balance_sheet: Balance general mensual.

    Raises:
        ValueError: Si faltan columnas o los datos son inválidos.
    """
    required_income_columns = {
        "periodo",
        "anio",
        "mes",
        "utilidad_neta_cop",
        "depreciacion_cop",
        "datos_sinteticos",
    }

    required_balance_columns = {
        "periodo",
        "efectivo_cop",
        "cuentas_por_cobrar_cop",
        "inventarios_cop",
        "otros_activos_corrientes_cop",
        "propiedad_planta_equipo_bruto_cop",
        "otros_activos_no_corrientes_cop",
        "proveedores_cop",
        "obligaciones_financieras_corto_plazo_cop",
        "impuestos_por_pagar_cop",
        "otros_pasivos_corrientes_cop",
        "obligaciones_financieras_largo_plazo_cop",
        "otros_pasivos_no_corrientes_cop",
        "capital_social_cop",
        "datos_sinteticos",
    }

    missing_income_columns = required_income_columns.difference(
        income_statement.columns
    )

    missing_balance_columns = required_balance_columns.difference(
        balance_sheet.columns
    )

    if missing_income_columns:
        missing_text = ", ".join(
            sorted(missing_income_columns)
        )
        raise ValueError(
            "Faltan columnas en el estado de resultados: "
            f"{missing_text}"
        )

    if missing_balance_columns:
        missing_text = ", ".join(
            sorted(missing_balance_columns)
        )
        raise ValueError(
            "Faltan columnas en el balance general: "
            f"{missing_text}"
        )

    if income_statement.empty:
        raise ValueError(
            "El estado de resultados está vacío."
        )

    if balance_sheet.empty:
        raise ValueError(
            "El balance general está vacío."
        )

    if income_statement["periodo"].duplicated().any():
        raise ValueError(
            "El estado de resultados contiene periodos duplicados."
        )

    if balance_sheet["periodo"].duplicated().any():
        raise ValueError(
            "El balance general contiene periodos duplicados."
        )

    income_periods = set(
        income_statement["periodo"]
    )

    balance_periods = set(
        balance_sheet["periodo"]
    )

    if income_periods != balance_periods:
        raise ValueError(
            "Los periodos del estado de resultados y del "
            "balance general no coinciden."
        )

    if not income_statement["datos_sinteticos"].all():
        raise ValueError(
            "El estado de resultados debe identificarse "
            "como sintético."
        )

    if not balance_sheet["datos_sinteticos"].all():
        raise ValueError(
            "El balance general debe identificarse como sintético."
        )


def _calculate_change(
    current_value: int,
    previous_value: int,
) -> int:
    """Calcula la variación entre dos periodos.

    Args:
        current_value: Saldo del periodo actual.
        previous_value: Saldo del periodo anterior.

    Returns:
        Variación absoluta.
    """
    return int(current_value - previous_value)


def _split_debt_change(
    current_debt: int,
    previous_debt: int,
) -> tuple[int, int]:
    """Separa un cambio de deuda entre nuevos préstamos y pagos.

    Args:
        current_debt: Deuda total del periodo actual.
        previous_debt: Deuda total del periodo anterior.

    Returns:
        Tupla con nuevos préstamos y pagos de capital.
    """
    debt_change = current_debt - previous_debt

    if debt_change >= 0:
        return int(debt_change), 0

    return 0, int(abs(debt_change))


def generate_cash_flow(
    income_statement: pd.DataFrame,
    balance_sheet: pd.DataFrame,
) -> pd.DataFrame:
    """Genera el flujo de efectivo mensual sintético.

    Args:
        income_statement: Estado de resultados mensual.
        balance_sheet: Balance general mensual.

    Returns:
        DataFrame con el flujo mensual conciliado.

    Raises:
        ValueError: Si las entradas o resultados son inválidos.
    """
    _validate_input_data(
        income_statement=income_statement,
        balance_sheet=balance_sheet,
    )

    ordered_income = (
        income_statement.sort_values("periodo")
        .reset_index(drop=True)
        .copy()
    )

    ordered_balance = (
        balance_sheet.sort_values("periodo")
        .reset_index(drop=True)
        .copy()
    )

    financial_data = ordered_income[
        [
            "periodo",
            "anio",
            "mes",
            "utilidad_neta_cop",
            "depreciacion_cop",
        ]
    ].merge(
        ordered_balance,
        on="periodo",
        how="inner",
        validate="one_to_one",
        suffixes=("_resultado", "_balance"),
    )

    records: list[dict] = []

    LOGGER.info(
        "Iniciando generación del flujo de efectivo para "
        "%s periodos.",
        len(financial_data),
    )

    previous_cash = INITIAL_OPENING_CASH_COP
    previous_accounts_receivable = 0
    previous_inventory = 0
    previous_other_current_assets = 0
    previous_gross_property = 0
    previous_other_non_current_assets = 0

    previous_accounts_payable = 0
    previous_taxes_payable = 0
    previous_other_current_liabilities = 0
    previous_short_term_debt = 0
    previous_long_term_debt = 0
    previous_other_non_current_liabilities = 0
    previous_share_capital = 0

    for row in financial_data.itertuples(index=False):
        current_cash = int(row.efectivo_cop)

        accounts_receivable_change = _calculate_change(
            current_value=int(row.cuentas_por_cobrar_cop),
            previous_value=previous_accounts_receivable,
        )

        inventory_change = _calculate_change(
            current_value=int(row.inventarios_cop),
            previous_value=previous_inventory,
        )

        other_current_assets_change = _calculate_change(
            current_value=int(
                row.otros_activos_corrientes_cop
            ),
            previous_value=previous_other_current_assets,
        )

        accounts_payable_change = _calculate_change(
            current_value=int(row.proveedores_cop),
            previous_value=previous_accounts_payable,
        )

        taxes_payable_change = _calculate_change(
            current_value=int(row.impuestos_por_pagar_cop),
            previous_value=previous_taxes_payable,
        )

        other_current_liabilities_change = _calculate_change(
            current_value=int(
                row.otros_pasivos_corrientes_cop
            ),
            previous_value=previous_other_current_liabilities,
        )

        other_operating_adjustments = 0

        operating_cash_flow = (
            int(row.utilidad_neta_cop)
            + int(row.depreciacion_cop)
            - accounts_receivable_change
            - inventory_change
            - other_current_assets_change
            + accounts_payable_change
            + taxes_payable_change
            + other_current_liabilities_change
            + other_operating_adjustments
        )

        gross_property_change = _calculate_change(
            current_value=int(
                row.propiedad_planta_equipo_bruto_cop
            ),
            previous_value=previous_gross_property,
        )

        fixed_asset_purchases = max(
            gross_property_change,
            0,
        )

        asset_sales = max(
            -gross_property_change,
            0,
        )

        other_non_current_assets_change = _calculate_change(
            current_value=int(
                row.otros_activos_no_corrientes_cop
            ),
            previous_value=previous_other_non_current_assets,
        )

        investing_cash_flow = (
            -fixed_asset_purchases
            + asset_sales
            - other_non_current_assets_change
        )

        current_total_debt = (
            int(
                row.obligaciones_financieras_corto_plazo_cop
            )
            + int(
                row.obligaciones_financieras_largo_plazo_cop
            )
        )

        previous_total_debt = (
            previous_short_term_debt
            + previous_long_term_debt
        )

        (
            new_debt,
            debt_principal_payments,
        ) = _split_debt_change(
            current_debt=current_total_debt,
            previous_debt=previous_total_debt,
        )

        capital_contributions = max(
            _calculate_change(
                current_value=int(row.capital_social_cop),
                previous_value=previous_share_capital,
            ),
            0,
        )

        dividends = 0

        other_non_current_liabilities_change = (
            _calculate_change(
                current_value=int(
                    row.otros_pasivos_no_corrientes_cop
                ),
                previous_value=(
                    previous_other_non_current_liabilities
                ),
            )
        )

        financing_cash_flow = (
            new_debt
            - debt_principal_payments
            + capital_contributions
            - dividends
            + other_non_current_liabilities_change
        )

        cash_change_from_balance = (
            current_cash - previous_cash
        )

        pre_adjustment_cash_change = (
            operating_cash_flow
            + investing_cash_flow
            + financing_cash_flow
        )

        reconciliation_adjustment = (
            cash_change_from_balance
            - pre_adjustment_cash_change
        )

        net_cash_change = (
            operating_cash_flow
            + investing_cash_flow
            + financing_cash_flow
            + reconciliation_adjustment
        )

        calculated_closing_cash = (
            previous_cash + net_cash_change
        )

        reconciliation_difference = (
            calculated_closing_cash
            - current_cash
        )

        record = {
            "periodo": row.periodo,
            "anio": int(row.anio_resultado),
            "mes": int(row.mes_resultado),
            "utilidad_neta_cop": int(
                row.utilidad_neta_cop
            ),
            "depreciacion_cop": int(
                row.depreciacion_cop
            ),
            "variacion_cuentas_por_cobrar_cop": (
                accounts_receivable_change
            ),
            "variacion_inventarios_cop": (
                inventory_change
            ),
            "variacion_otros_activos_corrientes_cop": (
                other_current_assets_change
            ),
            "variacion_proveedores_cop": (
                accounts_payable_change
            ),
            "variacion_impuestos_por_pagar_cop": (
                taxes_payable_change
            ),
            "variacion_otros_pasivos_corrientes_cop": (
                other_current_liabilities_change
            ),
            "otros_ajustes_operativos_cop": (
                other_operating_adjustments
            ),
            "flujo_operacion_cop": operating_cash_flow,
            "compras_activos_fijos_cop": (
                fixed_asset_purchases
            ),
            "venta_activos_cop": asset_sales,
            "variacion_otros_activos_no_corrientes_cop": (
                other_non_current_assets_change
            ),
            "flujo_inversion_cop": investing_cash_flow,
            "nuevos_prestamos_cop": new_debt,
            "pago_capital_deuda_cop": (
                debt_principal_payments
            ),
            "aportes_capital_cop": capital_contributions,
            "dividendos_cop": dividends,
            "variacion_otros_pasivos_no_corrientes_cop": (
                other_non_current_liabilities_change
            ),
            "flujo_financiacion_cop": (
                financing_cash_flow
            ),
            "ajuste_conciliacion_cop": (
                reconciliation_adjustment
            ),
            "variacion_neta_efectivo_cop": (
                net_cash_change
            ),
            "efectivo_inicial_cop": previous_cash,
            "efectivo_final_cop": current_cash,
            "diferencia_conciliacion_cop": (
                reconciliation_difference
            ),
            "datos_sinteticos": True,
        }

        records.append(record)

        previous_cash = current_cash
        previous_accounts_receivable = int(
            row.cuentas_por_cobrar_cop
        )
        previous_inventory = int(
            row.inventarios_cop
        )
        previous_other_current_assets = int(
            row.otros_activos_corrientes_cop
        )
        previous_gross_property = int(
            row.propiedad_planta_equipo_bruto_cop
        )
        previous_other_non_current_assets = int(
            row.otros_activos_no_corrientes_cop
        )

        previous_accounts_payable = int(
            row.proveedores_cop
        )
        previous_taxes_payable = int(
            row.impuestos_por_pagar_cop
        )
        previous_other_current_liabilities = int(
            row.otros_pasivos_corrientes_cop
        )
        previous_short_term_debt = int(
            row.obligaciones_financieras_corto_plazo_cop
        )
        previous_long_term_debt = int(
            row.obligaciones_financieras_largo_plazo_cop
        )
        previous_other_non_current_liabilities = int(
            row.otros_pasivos_no_corrientes_cop
        )
        previous_share_capital = int(
            row.capital_social_cop
        )

    cash_flow = pd.DataFrame(
        records,
        columns=CASH_FLOW_COLUMNS,
    )

    _validate_generated_cash_flow(
        cash_flow=cash_flow,
        balance_sheet=ordered_balance,
    )

    LOGGER.info(
        "Flujo de efectivo generado correctamente: %s periodos.",
        len(cash_flow),
    )

    return cash_flow


def _validate_generated_cash_flow(
    cash_flow: pd.DataFrame,
    balance_sheet: pd.DataFrame,
) -> None:
    """Valida el flujo de efectivo generado.

    Args:
        cash_flow: Flujo de efectivo mensual.
        balance_sheet: Balance general utilizado como referencia.

    Raises:
        ValueError: Si alguna conciliación es inconsistente.
    """
    if len(cash_flow) != len(balance_sheet):
        raise ValueError(
            "La cantidad de periodos del flujo no coincide "
            "con el balance general."
        )

    if cash_flow["periodo"].duplicated().any():
        raise ValueError(
            "El flujo de efectivo contiene periodos duplicados."
        )

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

    if not expected_operating_cash_flow.equals(
        cash_flow["flujo_operacion_cop"]
    ):
        raise ValueError(
            "El flujo de operación es inconsistente."
        )

    expected_investing_cash_flow = (
        -cash_flow["compras_activos_fijos_cop"]
        + cash_flow["venta_activos_cop"]
        - cash_flow[
            "variacion_otros_activos_no_corrientes_cop"
        ]
    )

    if not expected_investing_cash_flow.equals(
        cash_flow["flujo_inversion_cop"]
    ):
        raise ValueError(
            "El flujo de inversión es inconsistente."
        )

    expected_financing_cash_flow = (
        cash_flow["nuevos_prestamos_cop"]
        - cash_flow["pago_capital_deuda_cop"]
        + cash_flow["aportes_capital_cop"]
        - cash_flow["dividendos_cop"]
        + cash_flow[
            "variacion_otros_pasivos_no_corrientes_cop"
        ]
    )

    if not expected_financing_cash_flow.equals(
        cash_flow["flujo_financiacion_cop"]
    ):
        raise ValueError(
            "El flujo de financiación es inconsistente."
        )

    expected_net_cash_change = (
        cash_flow["flujo_operacion_cop"]
        + cash_flow["flujo_inversion_cop"]
        + cash_flow["flujo_financiacion_cop"]
        + cash_flow["ajuste_conciliacion_cop"]
    )

    if not expected_net_cash_change.equals(
        cash_flow["variacion_neta_efectivo_cop"]
    ):
        raise ValueError(
            "La variación neta del efectivo es inconsistente."
        )

    expected_closing_cash = (
        cash_flow["efectivo_inicial_cop"]
        + cash_flow["variacion_neta_efectivo_cop"]
    )

    if not expected_closing_cash.equals(
        cash_flow["efectivo_final_cop"]
    ):
        raise ValueError(
            "El efectivo final no concilia con la variación neta."
        )

    balance_cash = (
        balance_sheet.sort_values("periodo")[
            "efectivo_cop"
        ]
        .reset_index(drop=True)
    )

    flow_cash = (
        cash_flow.sort_values("periodo")[
            "efectivo_final_cop"
        ]
        .reset_index(drop=True)
    )

    pd.testing.assert_series_equal(
        flow_cash,
        balance_cash,
        check_names=False,
    )

    if not (
        cash_flow["diferencia_conciliacion_cop"] == 0
    ).all():
        raise ValueError(
            "Existen diferencias en la conciliación del efectivo."
        )

    non_negative_columns = [
        "compras_activos_fijos_cop",
        "venta_activos_cop",
        "nuevos_prestamos_cop",
        "pago_capital_deuda_cop",
        "aportes_capital_cop",
        "dividendos_cop",
        "efectivo_inicial_cop",
        "efectivo_final_cop",
    ]

    if (
        cash_flow[non_negative_columns] < 0
    ).any().any():
        raise ValueError(
            "Existen partidas que deben ser no negativas."
        )

    if not cash_flow["datos_sinteticos"].all():
        raise ValueError(
            "Todos los periodos deben identificarse como sintéticos."
        )
    