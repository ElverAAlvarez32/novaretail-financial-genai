"""Generación de estados financieros sintéticos de NovaRetail.

Esta primera versión genera el estado de resultados mensual a partir
de pedidos, devoluciones y marketing previamente generados.

Todos los valores corresponden a una empresa ficticia y se utilizan
exclusivamente con fines académicos.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from novaretail.config import load_data_generation_config
from novaretail.logging_config import get_logger


LOGGER = get_logger(__name__)


INCOME_STATEMENT_COLUMNS = [
    "periodo",
    "anio",
    "mes",
    "ingresos_brutos_cop",
    "descuentos_cop",
    "devoluciones_ventas_cop",
    "ingresos_netos_cop",
    "costo_mercancia_vendida_cop",
    "utilidad_bruta_cop",
    "gastos_marketing_cop",
    "gastos_logistica_cop",
    "gastos_plataforma_cop",
    "gastos_personal_cop",
    "gastos_administrativos_cop",
    "depreciacion_cop",
    "total_gastos_operacionales_cop",
    "utilidad_operacional_cop",
    "ingresos_no_operacionales_cop",
    "gastos_financieros_cop",
    "utilidad_antes_impuestos_cop",
    "impuesto_cop",
    "utilidad_neta_cop",
    "margen_bruto",
    "margen_operacional",
    "margen_neto",
    "datos_sinteticos",
]


LOGISTICS_EXPENSE_RATE = 0.055
PLATFORM_EXPENSE_RATE = 0.022
PERSONNEL_EXPENSE_RATE = 0.075
ADMINISTRATIVE_EXPENSE_RATE = 0.038

MONTHLY_FIXED_DEPRECIATION_COP = 18_000_000

NON_OPERATING_INCOME_MINIMUM_COP = 0
NON_OPERATING_INCOME_MAXIMUM_COP = 8_000_000

MONTHLY_FINANCIAL_EXPENSE_MINIMUM_COP = 8_000_000
MONTHLY_FINANCIAL_EXPENSE_MAXIMUM_COP = 22_000_000


def _validate_input_data(
    orders: pd.DataFrame,
    returns: pd.DataFrame,
    marketing: pd.DataFrame,
) -> None:
    """Valida las tablas necesarias para el estado de resultados.

    Args:
        orders: Líneas sintéticas de pedido.
        returns: Registros sintéticos de devoluciones.
        marketing: Métricas sintéticas de marketing.

    Raises:
        ValueError: Si faltan columnas o datos obligatorios.
    """
    required_order_columns = {
        "linea_pedido_id",
        "fecha_pedido",
        "periodo",
        "unidades",
        "valor_bruto_cop",
        "valor_descuento_cop",
        "valor_neto_cop",
        "costo_unitario_cop",
        "costo_total_cop",
        "estado_pedido",
        "datos_sinteticos",
    }

    required_return_columns = {
        "linea_pedido_id",
        "periodo_devolucion",
        "unidades_devueltas",
        "valor_reintegrado_cop",
        "costo_logistico_cop",
        "datos_sinteticos",
    }

    required_marketing_columns = {
        "periodo",
        "inversion_cop",
        "datos_sinteticos",
    }

    missing_order_columns = required_order_columns.difference(
        orders.columns
    )
    missing_return_columns = required_return_columns.difference(
        returns.columns
    )
    missing_marketing_columns = required_marketing_columns.difference(
        marketing.columns
    )

    if missing_order_columns:
        missing_text = ", ".join(
            sorted(missing_order_columns)
        )
        raise ValueError(
            f"Faltan columnas en pedidos: {missing_text}"
        )

    if missing_return_columns:
        missing_text = ", ".join(
            sorted(missing_return_columns)
        )
        raise ValueError(
            f"Faltan columnas en devoluciones: {missing_text}"
        )

    if missing_marketing_columns:
        missing_text = ", ".join(
            sorted(missing_marketing_columns)
        )
        raise ValueError(
            f"Faltan columnas en marketing: {missing_text}"
        )

    if orders.empty:
        raise ValueError(
            "El conjunto de pedidos está vacío."
        )

    if returns.empty:
        raise ValueError(
            "El conjunto de devoluciones está vacío."
        )

    if marketing.empty:
        raise ValueError(
            "El conjunto de marketing está vacío."
        )

    if not orders["datos_sinteticos"].all():
        raise ValueError(
            "Los pedidos deben identificarse como sintéticos."
        )

    if not returns["datos_sinteticos"].all():
        raise ValueError(
            "Las devoluciones deben identificarse como sintéticas."
        )

    if not marketing["datos_sinteticos"].all():
        raise ValueError(
            "Marketing debe identificarse como sintético."
        )


def _safe_ratio(
    numerator: int | float,
    denominator: int | float,
) -> float:
    """Calcula una razón evitando divisiones por cero.

    Args:
        numerator: Numerador.
        denominator: Denominador.

    Returns:
        Razón redondeada a cuatro decimales.
    """
    if denominator == 0:
        return 0.0

    return round(
        float(numerator) / float(denominator),
        4,
    )


def _prepare_monthly_orders(
    orders: pd.DataFrame,
) -> pd.DataFrame:
    """Consolida los pedidos no cancelados por periodo.

    Args:
        orders: Líneas de pedido sintéticas.

    Returns:
        Resumen mensual de ventas y costos iniciales.
    """
    recognized_orders = orders[
        orders["estado_pedido"] != "Cancelado"
    ].copy()

    monthly_orders = (
        recognized_orders.groupby(
            "periodo",
            as_index=False,
        )
        .agg(
            ingresos_brutos_cop=(
                "valor_bruto_cop",
                "sum",
            ),
            descuentos_cop=(
                "valor_descuento_cop",
                "sum",
            ),
            costo_inicial_ventas_cop=(
                "costo_total_cop",
                "sum",
            ),
        )
    )

    return monthly_orders


def _prepare_monthly_returns(
    orders: pd.DataFrame,
    returns: pd.DataFrame,
) -> pd.DataFrame:
    """Consolida devoluciones y reversión mensual del costo.

    El valor reintegrado reduce los ingresos del periodo de devolución.
    El costo de las unidades devueltas revierte parcialmente el costo
    de mercancía vendida.

    Args:
        orders: Líneas originales de pedido.
        returns: Registros de devoluciones.

    Returns:
        Resumen mensual de devoluciones y costo revertido.
    """
    order_cost_reference = orders[
        [
            "linea_pedido_id",
            "costo_unitario_cop",
        ]
    ]

    return_detail = returns.merge(
        order_cost_reference,
        on="linea_pedido_id",
        how="left",
        validate="one_to_one",
    )

    if return_detail["costo_unitario_cop"].isna().any():
        raise ValueError(
            "Existen devoluciones sin costo unitario asociado."
        )

    return_detail["costo_revertido_cop"] = (
        return_detail["unidades_devueltas"]
        * return_detail["costo_unitario_cop"]
    )

    monthly_returns = (
        return_detail.groupby(
            "periodo_devolucion",
            as_index=False,
        )
        .agg(
            devoluciones_ventas_cop=(
                "valor_reintegrado_cop",
                "sum",
            ),
            costo_revertido_cop=(
                "costo_revertido_cop",
                "sum",
            ),
            costo_logistico_devoluciones_cop=(
                "costo_logistico_cop",
                "sum",
            ),
        )
        .rename(
            columns={
                "periodo_devolucion": "periodo",
            }
        )
    )

    return monthly_returns


def _prepare_monthly_marketing(
    marketing: pd.DataFrame,
) -> pd.DataFrame:
    """Consolida la inversión mensual de marketing.

    Args:
        marketing: Métricas de marketing por canal.

    Returns:
        Inversión mensual consolidada.
    """
    return (
        marketing.groupby(
            "periodo",
            as_index=False,
        )
        .agg(
            gastos_marketing_cop=(
                "inversion_cop",
                "sum",
            )
        )
    )


def generate_income_statement(
    orders: pd.DataFrame,
    returns: pd.DataFrame,
    marketing: pd.DataFrame,
    random_seed: int | None = None,
) -> pd.DataFrame:
    """Genera el estado de resultados mensual sintético.

    Args:
        orders: Líneas sintéticas de pedido.
        returns: Devoluciones sintéticas.
        marketing: Información sintética de marketing.
        random_seed: Semilla alternativa de generación.

    Returns:
        Estado de resultados mensual.

    Raises:
        ValueError: Si los datos de entrada o resultados son inválidos.
    """
    _validate_input_data(
        orders=orders,
        returns=returns,
        marketing=marketing,
    )

    configuration = load_data_generation_config()

    configured_seed = int(
        configuration["generation"]["random_seed"]
    )

    seed = (
        configured_seed + 600
        if random_seed is None
        else random_seed
    )

    rng = np.random.default_rng(seed)

    start_date = pd.Timestamp(
        configuration["period"]["start_date"]
    )
    end_date = pd.Timestamp(
        configuration["period"]["end_date"]
    )

    income_tax_rate = float(
        configuration["finance"]["income_tax_rate"]
    )

    periods = pd.DataFrame(
        {
            "fecha_periodo": pd.date_range(
                start=start_date,
                end=end_date,
                freq="MS",
            )
        }
    )

    periods["periodo"] = periods[
        "fecha_periodo"
    ].dt.strftime("%Y-%m")

    periods["anio"] = periods[
        "fecha_periodo"
    ].dt.year

    periods["mes"] = periods[
        "fecha_periodo"
    ].dt.month

    monthly_orders = _prepare_monthly_orders(
        orders=orders
    )

    monthly_returns = _prepare_monthly_returns(
        orders=orders,
        returns=returns,
    )

    monthly_marketing = _prepare_monthly_marketing(
        marketing=marketing
    )

    statement = (
        periods.merge(
            monthly_orders,
            on="periodo",
            how="left",
            validate="one_to_one",
        )
        .merge(
            monthly_returns,
            on="periodo",
            how="left",
            validate="one_to_one",
        )
        .merge(
            monthly_marketing,
            on="periodo",
            how="left",
            validate="one_to_one",
        )
    )

    numeric_input_columns = [
        "ingresos_brutos_cop",
        "descuentos_cop",
        "costo_inicial_ventas_cop",
        "devoluciones_ventas_cop",
        "costo_revertido_cop",
        "costo_logistico_devoluciones_cop",
        "gastos_marketing_cop",
    ]

    statement[numeric_input_columns] = (
        statement[numeric_input_columns]
        .fillna(0)
        .astype(int)
    )

    statement["ingresos_netos_cop"] = (
        statement["ingresos_brutos_cop"]
        - statement["descuentos_cop"]
        - statement["devoluciones_ventas_cop"]
    )

    statement["costo_mercancia_vendida_cop"] = (
        statement["costo_inicial_ventas_cop"]
        - statement["costo_revertido_cop"]
    ).clip(lower=0)

    statement["utilidad_bruta_cop"] = (
        statement["ingresos_netos_cop"]
        - statement["costo_mercancia_vendida_cop"]
    )

    statement["gastos_logistica_cop"] = (
        statement["ingresos_netos_cop"]
        * LOGISTICS_EXPENSE_RATE
    ).round().astype(int)

    statement["gastos_logistica_cop"] = (
        statement["gastos_logistica_cop"]
        + statement[
            "costo_logistico_devoluciones_cop"
        ]
    )

    statement["gastos_plataforma_cop"] = (
        statement["ingresos_netos_cop"]
        * PLATFORM_EXPENSE_RATE
    ).round().astype(int)

    statement["gastos_personal_cop"] = (
        statement["ingresos_netos_cop"]
        * PERSONNEL_EXPENSE_RATE
    ).round().astype(int)

    statement["gastos_administrativos_cop"] = (
        statement["ingresos_netos_cop"]
        * ADMINISTRATIVE_EXPENSE_RATE
    ).round().astype(int)

    statement["depreciacion_cop"] = (
        MONTHLY_FIXED_DEPRECIATION_COP
    )

    statement["total_gastos_operacionales_cop"] = (
        statement["gastos_marketing_cop"]
        + statement["gastos_logistica_cop"]
        + statement["gastos_plataforma_cop"]
        + statement["gastos_personal_cop"]
        + statement["gastos_administrativos_cop"]
        + statement["depreciacion_cop"]
    )

    statement["utilidad_operacional_cop"] = (
        statement["utilidad_bruta_cop"]
        - statement["total_gastos_operacionales_cop"]
    )

    statement["ingresos_no_operacionales_cop"] = [
        int(
            rng.integers(
                NON_OPERATING_INCOME_MINIMUM_COP,
                NON_OPERATING_INCOME_MAXIMUM_COP + 1,
            )
        )
        for _ in range(len(statement))
    ]

    statement["gastos_financieros_cop"] = [
        int(
            rng.integers(
                MONTHLY_FINANCIAL_EXPENSE_MINIMUM_COP,
                MONTHLY_FINANCIAL_EXPENSE_MAXIMUM_COP + 1,
            )
        )
        for _ in range(len(statement))
    ]

    statement["utilidad_antes_impuestos_cop"] = (
        statement["utilidad_operacional_cop"]
        + statement["ingresos_no_operacionales_cop"]
        - statement["gastos_financieros_cop"]
    )

    statement["impuesto_cop"] = (
        statement["utilidad_antes_impuestos_cop"]
        .clip(lower=0)
        * income_tax_rate
    ).round().astype(int)

    statement["utilidad_neta_cop"] = (
        statement["utilidad_antes_impuestos_cop"]
        - statement["impuesto_cop"]
    )

    statement["margen_bruto"] = statement.apply(
        lambda row: _safe_ratio(
            row["utilidad_bruta_cop"],
            row["ingresos_netos_cop"],
        ),
        axis=1,
    )

    statement["margen_operacional"] = statement.apply(
        lambda row: _safe_ratio(
            row["utilidad_operacional_cop"],
            row["ingresos_netos_cop"],
        ),
        axis=1,
    )

    statement["margen_neto"] = statement.apply(
        lambda row: _safe_ratio(
            row["utilidad_neta_cop"],
            row["ingresos_netos_cop"],
        ),
        axis=1,
    )

    statement["datos_sinteticos"] = True

    income_statement = statement[
        INCOME_STATEMENT_COLUMNS
    ].copy()

    _validate_generated_income_statement(
        income_statement=income_statement,
        expected_periods=len(periods),
    )

    LOGGER.info(
        "Estado de resultados generado correctamente: "
        "%s periodos.",
        len(income_statement),
    )

    return income_statement


def _validate_generated_income_statement(
    income_statement: pd.DataFrame,
    expected_periods: int,
) -> None:
    """Valida el estado de resultados generado.

    Args:
        income_statement: Estado de resultados mensual.
        expected_periods: Cantidad esperada de meses.

    Raises:
        ValueError: Si alguna relación financiera no se cumple.
    """
    if len(income_statement) != expected_periods:
        raise ValueError(
            "La cantidad de periodos del estado de resultados "
            "no coincide con la esperada."
        )

    if income_statement["periodo"].duplicated().any():
        raise ValueError(
            "El estado de resultados contiene periodos duplicados."
        )

    if (income_statement["ingresos_brutos_cop"] < 0).any():
        raise ValueError(
            "Los ingresos brutos no pueden ser negativos."
        )

    if (income_statement["descuentos_cop"] < 0).any():
        raise ValueError(
            "Los descuentos no pueden ser negativos."
        )

    if (
        income_statement["devoluciones_ventas_cop"] < 0
    ).any():
        raise ValueError(
            "Las devoluciones no pueden ser negativas."
        )

    expected_net_revenue = (
        income_statement["ingresos_brutos_cop"]
        - income_statement["descuentos_cop"]
        - income_statement["devoluciones_ventas_cop"]
    )

    if not expected_net_revenue.equals(
        income_statement["ingresos_netos_cop"]
    ):
        raise ValueError(
            "Los ingresos netos presentan inconsistencias."
        )

    expected_gross_profit = (
        income_statement["ingresos_netos_cop"]
        - income_statement[
            "costo_mercancia_vendida_cop"
        ]
    )

    if not expected_gross_profit.equals(
        income_statement["utilidad_bruta_cop"]
    ):
        raise ValueError(
            "La utilidad bruta presenta inconsistencias."
        )

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

    if not expected_operating_expenses.equals(
        income_statement[
            "total_gastos_operacionales_cop"
        ]
    ):
        raise ValueError(
            "Los gastos operacionales presentan inconsistencias."
        )

    expected_operating_profit = (
        income_statement["utilidad_bruta_cop"]
        - income_statement[
            "total_gastos_operacionales_cop"
        ]
    )

    if not expected_operating_profit.equals(
        income_statement["utilidad_operacional_cop"]
    ):
        raise ValueError(
            "La utilidad operacional es inconsistente."
        )

    expected_profit_before_tax = (
        income_statement["utilidad_operacional_cop"]
        + income_statement[
            "ingresos_no_operacionales_cop"
        ]
        - income_statement["gastos_financieros_cop"]
    )

    if not expected_profit_before_tax.equals(
        income_statement[
            "utilidad_antes_impuestos_cop"
        ]
    ):
        raise ValueError(
            "La utilidad antes de impuestos es inconsistente."
        )

    expected_net_profit = (
        income_statement[
            "utilidad_antes_impuestos_cop"
        ]
        - income_statement["impuesto_cop"]
    )

    if not expected_net_profit.equals(
        income_statement["utilidad_neta_cop"]
    ):
        raise ValueError(
            "La utilidad neta es inconsistente."
        )

    if (income_statement["impuesto_cop"] < 0).any():
        raise ValueError(
            "El impuesto no puede ser negativo."
        )

    if not income_statement["datos_sinteticos"].all():
        raise ValueError(
            "Todos los periodos deben identificarse "
            "como sintéticos."
        )