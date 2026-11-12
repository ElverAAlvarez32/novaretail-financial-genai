"""Generación reproducible de devoluciones sintéticas.

Este módulo crea registros de devolución a partir de las líneas
de pedido cuyo estado es "Devuelto".

Cada devolución mantiene trazabilidad con el pedido y el producto
originales. Todos los datos son ficticios y de uso académico.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from novaretail.config import load_data_generation_config
from novaretail.logging_config import get_logger


LOGGER = get_logger(__name__)

RETURN_COLUMNS = [
    "devolucion_id",
    "linea_pedido_id",
    "pedido_id",
    "fecha_devolucion",
    "periodo_devolucion",
    "cliente_id",
    "producto_id",
    "categoria",
    "motivo_devolucion",
    "unidades_devueltas",
    "valor_reintegrado_cop",
    "costo_logistico_cop",
    "costo_total_devolucion_cop",
    "dias_desde_entrega",
    "estado_devolucion",
    "datos_sinteticos",
]


RETURN_REASONS = [
    "Producto defectuoso",
    "Producto diferente al solicitado",
    "Entrega tardía",
    "Daño durante el transporte",
    "Cambio de decisión",
    "Especificación incorrecta",
    "Información insuficiente del producto",
]


RETURN_REASON_PROBABILITIES = [
    0.24,
    0.13,
    0.12,
    0.18,
    0.16,
    0.09,
    0.08,
]


RETURN_STATES = [
    "Reintegro completado",
    "Cambio completado",
    "En revisión",
]


RETURN_STATE_PROBABILITIES = [
    0.72,
    0.20,
    0.08,
]


MINIMUM_RETURN_DAYS = 1
MAXIMUM_RETURN_DAYS = 30

MINIMUM_LOGISTICS_COST_COP = 8_000
MAXIMUM_LOGISTICS_COST_COP = 45_000


def _validate_orders(orders: pd.DataFrame) -> None:
    """Valida la estructura de pedidos requerida.

    Args:
        orders: Líneas de pedido previamente generadas.

    Raises:
        ValueError: Si faltan columnas o relaciones necesarias.
    """
    required_columns = {
        "linea_pedido_id",
        "pedido_id",
        "fecha_pedido",
        "cliente_id",
        "producto_id",
        "categoria",
        "unidades",
        "valor_neto_cop",
        "estado_pedido",
        "dias_entrega",
        "devolucion",
        "datos_sinteticos",
    }

    missing_columns = required_columns.difference(
        orders.columns
    )

    if missing_columns:
        missing_text = ", ".join(
            sorted(missing_columns)
        )
        raise ValueError(
            f"Faltan columnas en pedidos: {missing_text}"
        )

    if orders.empty:
        raise ValueError(
            "El conjunto de pedidos está vacío."
        )

    if orders["linea_pedido_id"].duplicated().any():
        raise ValueError(
            "Las líneas de pedido deben ser únicas."
        )

    returned_orders = orders[
        orders["estado_pedido"] == "Devuelto"
    ]

    if returned_orders.empty:
        raise ValueError(
            "No existen pedidos devueltos para generar registros."
        )

    if not returned_orders["devolucion"].all():
        raise ValueError(
            "Todos los pedidos con estado Devuelto deben estar "
            "marcados como devolución."
        )


def _calculate_refund_value(
    net_value: int,
    units_ordered: int,
    units_returned: int,
) -> int:
    """Calcula el valor reintegrado proporcionalmente.

    Args:
        net_value: Valor neto total de la línea.
        units_ordered: Unidades originalmente compradas.
        units_returned: Unidades efectivamente devueltas.

    Returns:
        Valor entero del reintegro.
    """
    unit_net_value = net_value / units_ordered

    return int(
        round(unit_net_value * units_returned)
    )


def generate_returns(
    orders: pd.DataFrame,
    random_seed: int | None = None,
) -> pd.DataFrame:
    """Genera devoluciones sintéticas desde pedidos devueltos.

    Args:
        orders: Líneas de pedido sintéticas.
        random_seed: Semilla alternativa de generación.

    Returns:
        DataFrame con las devoluciones generadas.

    Raises:
        ValueError: Si los pedidos o resultados son inválidos.
    """
    _validate_orders(orders)

    configuration = load_data_generation_config()

    configured_seed = int(
        configuration["generation"]["random_seed"]
    )

    seed = (
        configured_seed + 300
        if random_seed is None
        else random_seed
    )

    rng = np.random.default_rng(seed)

    project_end_date = pd.Timestamp(
        configuration["period"]["end_date"]
    )

    returned_orders = (
        orders[
            orders["estado_pedido"] == "Devuelto"
        ]
        .copy()
        .reset_index(drop=True)
    )

    records: list[dict] = []

    LOGGER.info(
        "Iniciando generación de devoluciones para %s "
        "líneas devueltas.",
        len(returned_orders),
    )

    for return_number, order_line in enumerate(
        returned_orders.itertuples(index=False),
        start=1,
    ):
        order_date = pd.Timestamp(
            order_line.fecha_pedido
        )

        units_ordered = int(
            order_line.unidades
        )

        units_returned = int(
            rng.integers(
                1,
                units_ordered + 1,
            )
        )

        days_after_delivery = int(
            rng.integers(
                MINIMUM_RETURN_DAYS,
                MAXIMUM_RETURN_DAYS + 1,
            )
        )

        return_date = (
            order_date
            + pd.Timedelta(
                days=int(order_line.dias_entrega)
            )
            + pd.Timedelta(
                days=days_after_delivery
            )
        )

        if return_date > project_end_date:
            return_date = project_end_date

        refund_value = _calculate_refund_value(
            net_value=int(order_line.valor_neto_cop),
            units_ordered=units_ordered,
            units_returned=units_returned,
        )

        logistics_cost = int(
            rng.integers(
                MINIMUM_LOGISTICS_COST_COP,
                MAXIMUM_LOGISTICS_COST_COP + 1,
            )
        )

        total_return_cost = (
            refund_value + logistics_cost
        )

        return_reason = str(
            rng.choice(
                RETURN_REASONS,
                p=RETURN_REASON_PROBABILITIES,
            )
        )

        return_state = str(
            rng.choice(
                RETURN_STATES,
                p=RETURN_STATE_PROBABILITIES,
            )
        )

        record = {
            "devolucion_id": (
                f"DEV-{return_number:06d}"
            ),
            "linea_pedido_id": (
                order_line.linea_pedido_id
            ),
            "pedido_id": order_line.pedido_id,
            "fecha_devolucion": return_date.date(),
            "periodo_devolucion": (
                return_date.strftime("%Y-%m")
            ),
            "cliente_id": order_line.cliente_id,
            "producto_id": order_line.producto_id,
            "categoria": order_line.categoria,
            "motivo_devolucion": return_reason,
            "unidades_devueltas": units_returned,
            "valor_reintegrado_cop": refund_value,
            "costo_logistico_cop": logistics_cost,
            "costo_total_devolucion_cop": (
                total_return_cost
            ),
            "dias_desde_entrega": days_after_delivery,
            "estado_devolucion": return_state,
            "datos_sinteticos": True,
        }

        records.append(record)

    returns = pd.DataFrame(
        records,
        columns=RETURN_COLUMNS,
    )

    _validate_generated_returns(
        returns=returns,
        returned_orders=returned_orders,
        project_end_date=project_end_date,
    )

    LOGGER.info(
        "Devoluciones generadas correctamente: %s registros.",
        len(returns),
    )

    return returns


def _validate_generated_returns(
    returns: pd.DataFrame,
    returned_orders: pd.DataFrame,
    project_end_date: pd.Timestamp,
) -> None:
    """Valida las devoluciones antes de devolverlas.

    Args:
        returns: Devoluciones generadas.
        returned_orders: Líneas de pedido devueltas.
        project_end_date: Fecha máxima permitida.

    Raises:
        ValueError: Si una regla de integridad falla.
    """
    if returns.empty:
        raise ValueError(
            "No se generaron devoluciones."
        )

    if len(returns) != len(returned_orders):
        raise ValueError(
            "Cada línea devuelta debe producir un registro "
            "de devolución."
        )

    if returns["devolucion_id"].duplicated().any():
        raise ValueError(
            "Se detectaron identificadores de devolución "
            "duplicados."
        )

    if returns["linea_pedido_id"].duplicated().any():
        raise ValueError(
            "Una línea de pedido no puede producir más de una "
            "devolución en esta versión."
        )

    expected_line_ids = set(
        returned_orders["linea_pedido_id"]
    )

    generated_line_ids = set(
        returns["linea_pedido_id"]
    )

    if generated_line_ids != expected_line_ids:
        raise ValueError(
            "Las devoluciones no coinciden con las líneas "
            "marcadas como devueltas."
        )

    if not returns["devolucion_id"].str.match(
        r"^DEV-\d{6}$"
    ).all():
        raise ValueError(
            "Existen identificadores de devolución inválidos."
        )

    if (returns["unidades_devueltas"] < 1).any():
        raise ValueError(
            "Las unidades devueltas deben ser positivas."
        )

    if (returns["valor_reintegrado_cop"] <= 0).any():
        raise ValueError(
            "Los reintegros deben ser mayores que cero."
        )

    if (returns["costo_logistico_cop"] <= 0).any():
        raise ValueError(
            "Los costos logísticos deben ser mayores que cero."
        )

    expected_total_cost = (
        returns["valor_reintegrado_cop"]
        + returns["costo_logistico_cop"]
    )

    if not expected_total_cost.equals(
        returns["costo_total_devolucion_cop"]
    ):
        raise ValueError(
            "Existen costos totales de devolución inconsistentes."
        )

    return_dates = pd.to_datetime(
        returns["fecha_devolucion"]
    )

    if (return_dates > project_end_date).any():
        raise ValueError(
            "Existen devoluciones posteriores al periodo."
        )

    if not returns["datos_sinteticos"].all():
        raise ValueError(
            "Todas las devoluciones deben identificarse "
            "como sintéticas."
        )