"""Generación reproducible del balance general sintético.

Este módulo construye el balance general mensual de la empresa
ficticia NovaRetail Colombia S.A.S. a partir del estado de
resultados y del inventario previamente generados.

La ecuación contable se valida en cada periodo:

    Activos = Pasivos + Patrimonio

Todos los valores son sintéticos y de uso exclusivamente académico.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from novaretail.config import load_data_generation_config
from novaretail.logging_config import get_logger


LOGGER = get_logger(__name__)


BALANCE_SHEET_COLUMNS = [
    "periodo",
    "anio",
    "mes",
    "efectivo_cop",
    "cuentas_por_cobrar_cop",
    "inventarios_cop",
    "otros_activos_corrientes_cop",
    "total_activo_corriente_cop",
    "propiedad_planta_equipo_bruto_cop",
    "depreciacion_acumulada_cop",
    "propiedad_planta_equipo_neto_cop",
    "otros_activos_no_corrientes_cop",
    "total_activo_no_corriente_cop",
    "total_activos_cop",
    "proveedores_cop",
    "obligaciones_financieras_corto_plazo_cop",
    "impuestos_por_pagar_cop",
    "otros_pasivos_corrientes_cop",
    "total_pasivo_corriente_cop",
    "obligaciones_financieras_largo_plazo_cop",
    "otros_pasivos_no_corrientes_cop",
    "total_pasivo_no_corriente_cop",
    "total_pasivos_cop",
    "capital_social_cop",
    "utilidades_retenidas_cop",
    "resultado_periodo_cop",
    "total_patrimonio_cop",
    "total_pasivo_patrimonio_cop",
    "diferencia_balance_cop",
    "datos_sinteticos",
]


ACCOUNTS_RECEIVABLE_RATE = 0.20
OTHER_CURRENT_ASSETS_RATE = 0.025
ACCOUNTS_PAYABLE_RATE = 0.32
SHORT_TERM_DEBT_RATE = 0.055
TAXES_PAYABLE_RATE = 0.70
OTHER_CURRENT_LIABILITIES_RATE = 0.045

INITIAL_GROSS_PROPERTY_PLANT_EQUIPMENT_COP = 1_200_000_000
INITIAL_LONG_TERM_DEBT_COP = 1_350_000_000
INITIAL_OTHER_NON_CURRENT_ASSETS_COP = 75_000_000
INITIAL_OTHER_NON_CURRENT_LIABILITIES_COP = 45_000_000

MINIMUM_MONTHLY_CAPEX_COP = 20_000_000
MAXIMUM_MONTHLY_CAPEX_COP = 55_000_000

MINIMUM_LONG_TERM_DEBT_PAYMENT_COP = 8_000_000
MAXIMUM_LONG_TERM_DEBT_PAYMENT_COP = 20_000_000

WORKING_CAPITAL_VARIATION_MINIMUM = 0.94
WORKING_CAPITAL_VARIATION_MAXIMUM = 1.06


def _validate_input_data(
    income_statement: pd.DataFrame,
    inventory: pd.DataFrame,
) -> None:
    """Valida las tablas necesarias para generar el balance.

    Args:
        income_statement: Estado de resultados mensual.
        inventory: Inventario mensual por producto.

    Raises:
        ValueError: Si falta información requerida.
    """
    required_income_columns = {
        "periodo",
        "anio",
        "mes",
        "ingresos_netos_cop",
        "costo_mercancia_vendida_cop",
        "total_gastos_operacionales_cop",
        "depreciacion_cop",
        "impuesto_cop",
        "utilidad_neta_cop",
        "datos_sinteticos",
    }

    required_inventory_columns = {
        "periodo",
        "producto_id",
        "valor_inventario_final_cop",
        "datos_sinteticos",
    }

    missing_income_columns = required_income_columns.difference(
        income_statement.columns
    )

    missing_inventory_columns = required_inventory_columns.difference(
        inventory.columns
    )

    if missing_income_columns:
        missing_text = ", ".join(
            sorted(missing_income_columns)
        )
        raise ValueError(
            "Faltan columnas en el estado de resultados: "
            f"{missing_text}"
        )

    if missing_inventory_columns:
        missing_text = ", ".join(
            sorted(missing_inventory_columns)
        )
        raise ValueError(
            f"Faltan columnas en inventario: {missing_text}"
        )

    if income_statement.empty:
        raise ValueError(
            "El estado de resultados está vacío."
        )

    if inventory.empty:
        raise ValueError(
            "El inventario está vacío."
        )

    if income_statement["periodo"].duplicated().any():
        raise ValueError(
            "El estado de resultados contiene periodos duplicados."
        )

    if not income_statement["datos_sinteticos"].all():
        raise ValueError(
            "El estado de resultados debe identificarse "
            "como sintético."
        )

    if not inventory["datos_sinteticos"].all():
        raise ValueError(
            "El inventario debe identificarse como sintético."
        )


def _prepare_monthly_inventory(
    inventory: pd.DataFrame,
) -> pd.DataFrame:
    """Consolida el valor final mensual del inventario.

    Args:
        inventory: Inventario mensual por producto.

    Returns:
        DataFrame con un valor consolidado por periodo.
    """
    monthly_inventory = (
        inventory.groupby(
            "periodo",
            as_index=False,
        )
        .agg(
            inventarios_cop=(
                "valor_inventario_final_cop",
                "sum",
            )
        )
    )

    return monthly_inventory


def _calculate_retained_earnings(
    income_statement: pd.DataFrame,
) -> pd.Series:
    """Calcula las utilidades retenidas de periodos anteriores.

    Las utilidades retenidas de cada mes corresponden a la utilidad
    neta acumulada hasta el periodo inmediatamente anterior.

    Args:
        income_statement: Estado de resultados ordenado por periodo.

    Returns:
        Serie con las utilidades retenidas.
    """
    cumulative_profit = (
        income_statement["utilidad_neta_cop"]
        .cumsum()
    )

    retained_earnings = (
        cumulative_profit
        .shift(1)
        .fillna(0)
        .astype(int)
    )

    return retained_earnings


def _calculate_financing_balance(
    minimum_cash: int,
    non_cash_assets: int,
    current_liabilities: int,
    other_non_current_liabilities: int,
    base_long_term_debt: int,
    equity: int,
) -> tuple[int, int]:
    """Calcula deuda de largo plazo y efectivo conciliado.

    La deuda de largo plazo se incrementa únicamente cuando el
    financiamiento disponible no permite conservar el saldo mínimo
    de efectivo definido en la configuración.

    Args:
        minimum_cash: Saldo mínimo requerido de efectivo.
        non_cash_assets: Activos diferentes del efectivo.
        current_liabilities: Total de pasivos corrientes.
        other_non_current_liabilities: Otros pasivos no corrientes.
        base_long_term_debt: Deuda de largo plazo antes del ajuste.
        equity: Patrimonio total del periodo.

    Returns:
        Tupla con deuda de largo plazo y efectivo conciliado.
    """
    financing_before_adjustment = (
        current_liabilities
        + other_non_current_liabilities
        + base_long_term_debt
        + equity
    )

    calculated_cash = (
        financing_before_adjustment
        - non_cash_assets
    )

    additional_debt = max(
        minimum_cash - calculated_cash,
        0,
    )

    long_term_debt = (
        base_long_term_debt
        + additional_debt
    )

    total_financing = (
        current_liabilities
        + other_non_current_liabilities
        + long_term_debt
        + equity
    )

    reconciled_cash = (
        total_financing
        - non_cash_assets
    )

    return int(long_term_debt), int(reconciled_cash)


def generate_balance_sheet(
    income_statement: pd.DataFrame,
    inventory: pd.DataFrame,
    random_seed: int | None = None,
) -> pd.DataFrame:
    """Genera el balance general mensual sintético.

    Args:
        income_statement: Estado de resultados mensual.
        inventory: Inventario mensual por producto.
        random_seed: Semilla alternativa de generación.

    Returns:
        DataFrame con el balance general mensual.

    Raises:
        ValueError: Si las entradas o resultados son inválidos.
    """
    _validate_input_data(
        income_statement=income_statement,
        inventory=inventory,
    )

    configuration = load_data_generation_config()

    configured_seed = int(
        configuration["generation"]["random_seed"]
    )

    seed = (
        configured_seed + 700
        if random_seed is None
        else random_seed
    )

    rng = np.random.default_rng(seed)

    minimum_cash_balance = int(
        configuration["finance"][
            "minimum_cash_balance_cop"
        ]
    )

    initial_equity = int(
        configuration["finance"][
            "initial_equity_cop"
        ]
    )

    ordered_income_statement = (
        income_statement.sort_values(
            "periodo"
        )
        .reset_index(drop=True)
        .copy()
    )

    monthly_inventory = _prepare_monthly_inventory(
        inventory=inventory
    )

    balance_base = ordered_income_statement.merge(
        monthly_inventory,
        on="periodo",
        how="left",
        validate="one_to_one",
    )

    balance_base["inventarios_cop"] = (
        balance_base["inventarios_cop"]
        .fillna(0)
        .astype(int)
    )

    balance_base["utilidades_retenidas_cop"] = (
        _calculate_retained_earnings(
            ordered_income_statement
        )
    )

    records: list[dict] = []

    gross_property_plant_equipment = (
        INITIAL_GROSS_PROPERTY_PLANT_EQUIPMENT_COP
    )

    accumulated_depreciation = 0
    base_long_term_debt = INITIAL_LONG_TERM_DEBT_COP

    LOGGER.info(
        "Iniciando generación del balance general para "
        "%s periodos.",
        len(balance_base),
    )

    for position, row in enumerate(
        balance_base.itertuples(index=False),
        start=1,
    ):
        net_revenue = int(
            row.ingresos_netos_cop
        )

        cost_of_goods_sold = int(
            row.costo_mercancia_vendida_cop
        )

        operating_expenses = int(
            row.total_gastos_operacionales_cop
        )

        income_tax = int(
            row.impuesto_cop
        )

        net_profit = int(
            row.utilidad_neta_cop
        )

        inventory_value = int(
            row.inventarios_cop
        )

        working_capital_variation = float(
            rng.uniform(
                WORKING_CAPITAL_VARIATION_MINIMUM,
                WORKING_CAPITAL_VARIATION_MAXIMUM,
            )
        )

        accounts_receivable = int(
            round(
                net_revenue
                * ACCOUNTS_RECEIVABLE_RATE
                * working_capital_variation
            )
        )

        other_current_assets = int(
            round(
                net_revenue
                * OTHER_CURRENT_ASSETS_RATE
            )
        )

        monthly_capex = int(
            rng.integers(
                MINIMUM_MONTHLY_CAPEX_COP,
                MAXIMUM_MONTHLY_CAPEX_COP + 1,
            )
        )

        gross_property_plant_equipment += monthly_capex

        accumulated_depreciation += int(
            row.depreciacion_cop
        )

        accumulated_depreciation = min(
            accumulated_depreciation,
            gross_property_plant_equipment,
        )

        net_property_plant_equipment = (
            gross_property_plant_equipment
            - accumulated_depreciation
        )

        other_non_current_assets = int(
            round(
                INITIAL_OTHER_NON_CURRENT_ASSETS_COP
                * (
                    1
                    + (position - 1) * 0.002
                )
            )
        )

        accounts_payable = int(
            round(
                cost_of_goods_sold
                * ACCOUNTS_PAYABLE_RATE
                * working_capital_variation
            )
        )

        short_term_debt = int(
            round(
                net_revenue
                * SHORT_TERM_DEBT_RATE
            )
        )

        taxes_payable = int(
            round(
                income_tax
                * TAXES_PAYABLE_RATE
            )
        )

        other_current_liabilities = int(
            round(
                operating_expenses
                * OTHER_CURRENT_LIABILITIES_RATE
            )
        )

        total_current_liabilities = (
            accounts_payable
            + short_term_debt
            + taxes_payable
            + other_current_liabilities
        )

        monthly_debt_payment = int(
            rng.integers(
                MINIMUM_LONG_TERM_DEBT_PAYMENT_COP,
                MAXIMUM_LONG_TERM_DEBT_PAYMENT_COP + 1,
            )
        )

        base_long_term_debt = max(
            base_long_term_debt
            - monthly_debt_payment,
            0,
        )

        other_non_current_liabilities = int(
            round(
                INITIAL_OTHER_NON_CURRENT_LIABILITIES_COP
                * (
                    1
                    + (position - 1) * 0.001
                )
            )
        )

        share_capital = initial_equity
        retained_earnings = int(
            row.utilidades_retenidas_cop
        )
        current_period_result = net_profit

        total_equity = (
            share_capital
            + retained_earnings
            + current_period_result
        )

        non_cash_assets = (
            accounts_receivable
            + inventory_value
            + other_current_assets
            + net_property_plant_equipment
            + other_non_current_assets
        )

        (
            long_term_debt,
            cash,
        ) = _calculate_financing_balance(
            minimum_cash=minimum_cash_balance,
            non_cash_assets=non_cash_assets,
            current_liabilities=total_current_liabilities,
            other_non_current_liabilities=(
                other_non_current_liabilities
            ),
            base_long_term_debt=base_long_term_debt,
            equity=total_equity,
        )

        total_current_assets = (
            cash
            + accounts_receivable
            + inventory_value
            + other_current_assets
        )

        total_non_current_assets = (
            net_property_plant_equipment
            + other_non_current_assets
        )

        total_assets = (
            total_current_assets
            + total_non_current_assets
        )

        total_non_current_liabilities = (
            long_term_debt
            + other_non_current_liabilities
        )

        total_liabilities = (
            total_current_liabilities
            + total_non_current_liabilities
        )

        total_liabilities_and_equity = (
            total_liabilities
            + total_equity
        )

        balance_difference = (
            total_assets
            - total_liabilities_and_equity
        )

        record = {
            "periodo": row.periodo,
            "anio": int(row.anio),
            "mes": int(row.mes),
            "efectivo_cop": cash,
            "cuentas_por_cobrar_cop": accounts_receivable,
            "inventarios_cop": inventory_value,
            "otros_activos_corrientes_cop": (
                other_current_assets
            ),
            "total_activo_corriente_cop": (
                total_current_assets
            ),
            "propiedad_planta_equipo_bruto_cop": (
                gross_property_plant_equipment
            ),
            "depreciacion_acumulada_cop": (
                accumulated_depreciation
            ),
            "propiedad_planta_equipo_neto_cop": (
                net_property_plant_equipment
            ),
            "otros_activos_no_corrientes_cop": (
                other_non_current_assets
            ),
            "total_activo_no_corriente_cop": (
                total_non_current_assets
            ),
            "total_activos_cop": total_assets,
            "proveedores_cop": accounts_payable,
            "obligaciones_financieras_corto_plazo_cop": (
                short_term_debt
            ),
            "impuestos_por_pagar_cop": taxes_payable,
            "otros_pasivos_corrientes_cop": (
                other_current_liabilities
            ),
            "total_pasivo_corriente_cop": (
                total_current_liabilities
            ),
            "obligaciones_financieras_largo_plazo_cop": (
                long_term_debt
            ),
            "otros_pasivos_no_corrientes_cop": (
                other_non_current_liabilities
            ),
            "total_pasivo_no_corriente_cop": (
                total_non_current_liabilities
            ),
            "total_pasivos_cop": total_liabilities,
            "capital_social_cop": share_capital,
            "utilidades_retenidas_cop": retained_earnings,
            "resultado_periodo_cop": current_period_result,
            "total_patrimonio_cop": total_equity,
            "total_pasivo_patrimonio_cop": (
                total_liabilities_and_equity
            ),
            "diferencia_balance_cop": balance_difference,
            "datos_sinteticos": True,
        }

        records.append(record)

        base_long_term_debt = long_term_debt

    balance_sheet = pd.DataFrame(
        records,
        columns=BALANCE_SHEET_COLUMNS,
    )

    _validate_generated_balance_sheet(
        balance_sheet=balance_sheet,
        expected_periods=len(balance_base),
        minimum_cash_balance=minimum_cash_balance,
    )

    LOGGER.info(
        "Balance general generado correctamente: %s periodos.",
        len(balance_sheet),
    )

    return balance_sheet


def _validate_generated_balance_sheet(
    balance_sheet: pd.DataFrame,
    expected_periods: int,
    minimum_cash_balance: int,
) -> None:
    """Valida el balance general generado.

    Args:
        balance_sheet: Balance general mensual.
        expected_periods: Número esperado de periodos.
        minimum_cash_balance: Saldo mínimo de efectivo.

    Raises:
        ValueError: Si alguna ecuación financiera no se cumple.
    """
    if len(balance_sheet) != expected_periods:
        raise ValueError(
            "La cantidad de periodos del balance no coincide "
            "con la esperada."
        )

    if balance_sheet["periodo"].duplicated().any():
        raise ValueError(
            "El balance contiene periodos duplicados."
        )

    if (
        balance_sheet["efectivo_cop"]
        < minimum_cash_balance
    ).any():
        raise ValueError(
            "El efectivo es inferior al saldo mínimo configurado."
        )

    monetary_columns = [
        column
        for column in BALANCE_SHEET_COLUMNS
        if column.endswith("_cop")
        and column != "diferencia_balance_cop"
    ]

    if (
        balance_sheet[monetary_columns] < 0
    ).any().any():
        raise ValueError(
            "El balance contiene valores monetarios negativos."
        )

    expected_current_assets = (
        balance_sheet["efectivo_cop"]
        + balance_sheet["cuentas_por_cobrar_cop"]
        + balance_sheet["inventarios_cop"]
        + balance_sheet["otros_activos_corrientes_cop"]
    )

    if not expected_current_assets.equals(
        balance_sheet["total_activo_corriente_cop"]
    ):
        raise ValueError(
            "El total del activo corriente es inconsistente."
        )

    expected_net_property = (
        balance_sheet[
            "propiedad_planta_equipo_bruto_cop"
        ]
        - balance_sheet[
            "depreciacion_acumulada_cop"
        ]
    )

    if not expected_net_property.equals(
        balance_sheet[
            "propiedad_planta_equipo_neto_cop"
        ]
    ):
        raise ValueError(
            "La propiedad, planta y equipo neta es inconsistente."
        )

    expected_non_current_assets = (
        balance_sheet[
            "propiedad_planta_equipo_neto_cop"
        ]
        + balance_sheet[
            "otros_activos_no_corrientes_cop"
        ]
    )

    if not expected_non_current_assets.equals(
        balance_sheet[
            "total_activo_no_corriente_cop"
        ]
    ):
        raise ValueError(
            "El total de activos no corrientes es inconsistente."
        )

    expected_total_assets = (
        balance_sheet["total_activo_corriente_cop"]
        + balance_sheet[
            "total_activo_no_corriente_cop"
        ]
    )

    if not expected_total_assets.equals(
        balance_sheet["total_activos_cop"]
    ):
        raise ValueError(
            "El total de activos es inconsistente."
        )

    expected_current_liabilities = (
        balance_sheet["proveedores_cop"]
        + balance_sheet[
            "obligaciones_financieras_corto_plazo_cop"
        ]
        + balance_sheet["impuestos_por_pagar_cop"]
        + balance_sheet[
            "otros_pasivos_corrientes_cop"
        ]
    )

    if not expected_current_liabilities.equals(
        balance_sheet["total_pasivo_corriente_cop"]
    ):
        raise ValueError(
            "El total de pasivos corrientes es inconsistente."
        )

    expected_non_current_liabilities = (
        balance_sheet[
            "obligaciones_financieras_largo_plazo_cop"
        ]
        + balance_sheet[
            "otros_pasivos_no_corrientes_cop"
        ]
    )

    if not expected_non_current_liabilities.equals(
        balance_sheet[
            "total_pasivo_no_corriente_cop"
        ]
    ):
        raise ValueError(
            "El total de pasivos no corrientes es inconsistente."
        )

    expected_total_liabilities = (
        balance_sheet["total_pasivo_corriente_cop"]
        + balance_sheet[
            "total_pasivo_no_corriente_cop"
        ]
    )

    if not expected_total_liabilities.equals(
        balance_sheet["total_pasivos_cop"]
    ):
        raise ValueError(
            "El total de pasivos es inconsistente."
        )

    expected_equity = (
        balance_sheet["capital_social_cop"]
        + balance_sheet["utilidades_retenidas_cop"]
        + balance_sheet["resultado_periodo_cop"]
    )

    if not expected_equity.equals(
        balance_sheet["total_patrimonio_cop"]
    ):
        raise ValueError(
            "El total del patrimonio es inconsistente."
        )

    expected_liabilities_and_equity = (
        balance_sheet["total_pasivos_cop"]
        + balance_sheet["total_patrimonio_cop"]
    )

    if not expected_liabilities_and_equity.equals(
        balance_sheet[
            "total_pasivo_patrimonio_cop"
        ]
    ):
        raise ValueError(
            "El total de pasivo y patrimonio es inconsistente."
        )

    expected_difference = (
        balance_sheet["total_activos_cop"]
        - balance_sheet[
            "total_pasivo_patrimonio_cop"
        ]
    )

    if not expected_difference.equals(
        balance_sheet["diferencia_balance_cop"]
    ):
        raise ValueError(
            "La diferencia del balance es inconsistente."
        )

    if not (
        balance_sheet["diferencia_balance_cop"] == 0
    ).all():
        raise ValueError(
            "La ecuación contable no se cumple en todos los periodos."
        )

    if not balance_sheet["datos_sinteticos"].all():
        raise ValueError(
            "Todos los periodos deben identificarse como sintéticos."
        )