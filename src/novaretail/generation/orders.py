"""Generación reproducible de pedidos sintéticos.

Este módulo crea líneas de pedido para NovaRetail Colombia S.A.S.
Los pedidos se relacionan exclusivamente con clientes y productos
sintéticos previamente generados.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from novaretail.config import load_data_generation_config
from novaretail.logging_config import get_logger


LOGGER = get_logger(__name__)

ORDER_COLUMNS = [
    "linea_pedido_id",
    "pedido_id",
    "fecha_pedido",
    "periodo",
    "cliente_id",
    "producto_id",
    "categoria",
    "ciudad",
    "departamento",
    "canal",
    "dispositivo",
    "unidades",
    "precio_unitario_cop",
    "descuento_rate",
    "valor_bruto_cop",
    "valor_descuento_cop",
    "valor_neto_cop",
    "costo_unitario_cop",
    "costo_total_cop",
    "margen_bruto_cop",
    "metodo_pago",
    "estado_pedido",
    "dias_entrega",
    "devolucion",
    "datos_sinteticos",
]


DEVICES = [
    "Móvil",
    "Computador",
    "Tableta",
]

DEVICE_PROBABILITIES = [
    0.67,
    0.29,
    0.04,
]


PAYMENT_METHODS = [
    "Tarjeta de crédito",
    "Tarjeta débito",
    "PSE",
    "Billetera digital",
    "Pago contra entrega",
]

PAYMENT_PROBABILITIES = [
    0.38,
    0.17,
    0.24,
    0.14,
    0.07,
]


ORDER_CHANNELS = [
    "Sitio web",
    "Aplicación móvil",
    "Marketplace",
]

CHANNEL_PROBABILITIES = [
    0.58,
    0.27,
    0.15,
]


DISCOUNT_OPTIONS = [
    0.00,
    0.05,
    0.10,
    0.15,
    0.20,
    0.25,
]

DISCOUNT_PROBABILITIES = [
    0.44,
    0.18,
    0.16,
    0.11,
    0.07,
    0.04,
]


def _validate_input_data(
    products: pd.DataFrame,
    customers: pd.DataFrame,
) -> None:
    """Valida los catálogos utilizados para generar pedidos.

    Args:
        products: Catálogo sintético de productos.
        customers: Catálogo sintético de clientes.

    Raises:
        ValueError: Si faltan columnas, registros o identificadores.
    """
    required_product_columns = {
        "producto_id",
        "categoria",
        "precio_lista_cop",
        "costo_estandar_cop",
        "fecha_ingreso",
        "estado_producto",
    }

    required_customer_columns = {
        "cliente_id",
        "fecha_registro",
        "ciudad",
        "departamento",
        "estado_cliente",
    }

    missing_product_columns = required_product_columns.difference(
        products.columns
    )
    missing_customer_columns = required_customer_columns.difference(
        customers.columns
    )

    if missing_product_columns:
        missing_text = ", ".join(
            sorted(missing_product_columns)
        )
        raise ValueError(
            f"Faltan columnas en productos: {missing_text}"
        )

    if missing_customer_columns:
        missing_text = ", ".join(
            sorted(missing_customer_columns)
        )
        raise ValueError(
            f"Faltan columnas en clientes: {missing_text}"
        )

    if products.empty:
        raise ValueError(
            "El catálogo de productos está vacío."
        )

    if customers.empty:
        raise ValueError(
            "El catálogo de clientes está vacío."
        )

    if products["producto_id"].duplicated().any():
        raise ValueError(
            "El catálogo contiene productos duplicados."
        )

    if customers["cliente_id"].duplicated().any():
        raise ValueError(
            "El catálogo contiene clientes duplicados."
        )


def _monthly_order_count(
    order_date: pd.Timestamp,
    configuration: dict,
    rng: np.random.Generator,
) -> int:
    """Calcula la cantidad simulada de pedidos de un mes.

    Args:
        order_date: Primer día del mes analizado.
        configuration: Configuración de generación.
        rng: Generador aleatorio reproducible.

    Returns:
        Cantidad de pedidos del mes.
    """
    base_orders = int(
        configuration["sales"]["base_monthly_orders"]
    )

    growth_rate = float(
        configuration["sales"]["annual_growth_rate"][
            order_date.year
        ]
    )

    seasonal_factor = float(
        configuration["sales"]["seasonal_factors"][
            order_date.month
        ]
    )

    expected_orders = (
        base_orders
        * (1 + growth_rate)
        * seasonal_factor
    )

    variation_factor = float(
        rng.normal(loc=1.0, scale=0.045)
    )

    calculated_orders = round(
        expected_orders * variation_factor
    )

    return max(calculated_orders, 1)


def _generate_order_date(
    period_start: pd.Timestamp,
    rng: np.random.Generator,
) -> pd.Timestamp:
    """Genera una fecha aleatoria dentro del mes.

    Args:
        period_start: Primer día del mes.
        rng: Generador aleatorio.

    Returns:
        Fecha del pedido.
    """
    period_end = period_start + pd.offsets.MonthEnd(0)
    days_in_month = period_end.day
    day = int(rng.integers(1, days_in_month + 1))

    return pd.Timestamp(
        year=period_start.year,
        month=period_start.month,
        day=day,
    )


def _select_available_record(
    data: pd.DataFrame,
    date_column: str,
    order_date: pd.Timestamp,
    rng: np.random.Generator,
) -> pd.Series:
    """Selecciona un registro disponible en la fecha del pedido.

    Args:
        data: Catálogo del cual se seleccionará el registro.
        date_column: Columna que establece disponibilidad.
        order_date: Fecha del pedido.
        rng: Generador aleatorio.

    Returns:
        Registro seleccionado.

    Raises:
        ValueError: Si no existen registros disponibles.
    """
    dates = pd.to_datetime(data[date_column])
    available = data.loc[dates <= order_date]

    if available.empty:
        raise ValueError(
            "No existen registros disponibles para la fecha "
            f"{order_date.date()} en la columna {date_column}."
        )

    selected_position = int(
        rng.integers(0, len(available))
    )

    return available.iloc[selected_position]


def generate_orders(
    products: pd.DataFrame,
    customers: pd.DataFrame,
    random_seed: int | None = None,
) -> pd.DataFrame:
    """Genera líneas de pedidos sintéticos.

    Args:
        products: Catálogo sintético de productos.
        customers: Catálogo sintético de clientes.
        random_seed: Semilla alternativa de generación.

    Returns:
        DataFrame con líneas de pedidos sintéticos.

    Raises:
        ValueError: Si la configuración o los datos son inválidos.
    """
    _validate_input_data(
        products=products,
        customers=customers,
    )

    configuration = load_data_generation_config()

    configured_seed = int(
        configuration["generation"]["random_seed"]
    )

    seed = (
        configured_seed + 200
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

    minimum_units = int(
        configuration["sales"][
            "minimum_units_per_order"
        ]
    )
    maximum_units = int(
        configuration["sales"][
            "maximum_units_per_order"
        ]
    )

    cancellation_rate = float(
        configuration["operations"]["cancellation_rate"]
    )
    return_rate = float(
        configuration["operations"]["return_rate"]
    )

    minimum_delivery_days = int(
        configuration["operations"][
            "minimum_delivery_days"
        ]
    )
    maximum_delivery_days = int(
        configuration["operations"][
            "maximum_delivery_days"
        ]
    )

    inactive_products = products[
        products["estado_producto"] == "Descontinuado"
    ]["producto_id"].tolist()

    periods = pd.date_range(
        start=start_date,
        end=end_date,
        freq="MS",
    )

    records: list[dict] = []
    order_number = 0
    line_number = 0

    LOGGER.info(
        "Iniciando generación de pedidos para %s periodos.",
        len(periods),
    )

    for period_start in periods:
        monthly_orders = _monthly_order_count(
            order_date=period_start,
            configuration=configuration,
            rng=rng,
        )

        for _ in range(monthly_orders):
            order_number += 1
            order_date = _generate_order_date(
                period_start=period_start,
                rng=rng,
            )

            customer = _select_available_record(
                data=customers,
                date_column="fecha_registro",
                order_date=order_date,
                rng=rng,
            )

            line_count = int(
                rng.choice(
                    [1, 2, 3],
                    p=[0.74, 0.21, 0.05],
                )
            )

            selected_product_ids: set[str] = set()

            for _ in range(line_count):
                eligible_products = products[
                    ~products["producto_id"].isin(
                        selected_product_ids
                    )
                ].copy()

                product = _select_available_record(
                    data=eligible_products,
                    date_column="fecha_ingreso",
                    order_date=order_date,
                    rng=rng,
                )

                product_id = str(product["producto_id"])
                selected_product_ids.add(product_id)

                line_number += 1

                units = int(
                    rng.integers(
                        minimum_units,
                        maximum_units + 1,
                    )
                )

                list_price = int(
                    product["precio_lista_cop"]
                )
                standard_cost = int(
                    product["costo_estandar_cop"]
                )

                discount_rate = float(
                    rng.choice(
                        DISCOUNT_OPTIONS,
                        p=DISCOUNT_PROBABILITIES,
                    )
                )

                gross_value = units * list_price
                discount_value = int(
                    round(gross_value * discount_rate)
                )
                net_value = gross_value - discount_value
                total_cost = units * standard_cost
                gross_margin = net_value - total_cost

                cancelled = bool(
                    rng.random() < cancellation_rate
                )

                if cancelled:
                    order_status = "Cancelado"
                    delivery_days = 0
                    returned = False
                else:
                    returned = bool(
                        rng.random() < return_rate
                    )

                    delivery_days = int(
                        rng.integers(
                            minimum_delivery_days,
                            maximum_delivery_days + 1,
                        )
                    )

                    if returned:
                        order_status = "Devuelto"
                    else:
                        order_status = "Entregado"

                if product_id in inactive_products:
                    product_warning = True
                else:
                    product_warning = False

                record = {
                    "linea_pedido_id": (
                        f"LIN-{line_number:06d}"
                    ),
                    "pedido_id": (
                        f"PED-{order_number:06d}"
                    ),
                    "fecha_pedido": order_date.date(),
                    "periodo": order_date.strftime("%Y-%m"),
                    "cliente_id": customer["cliente_id"],
                    "producto_id": product_id,
                    "categoria": product["categoria"],
                    "ciudad": customer["ciudad"],
                    "departamento": customer["departamento"],
                    "canal": str(
                        rng.choice(
                            ORDER_CHANNELS,
                            p=CHANNEL_PROBABILITIES,
                        )
                    ),
                    "dispositivo": str(
                        rng.choice(
                            DEVICES,
                            p=DEVICE_PROBABILITIES,
                        )
                    ),
                    "unidades": units,
                    "precio_unitario_cop": list_price,
                    "descuento_rate": discount_rate,
                    "valor_bruto_cop": gross_value,
                    "valor_descuento_cop": discount_value,
                    "valor_neto_cop": net_value,
                    "costo_unitario_cop": standard_cost,
                    "costo_total_cop": total_cost,
                    "margen_bruto_cop": gross_margin,
                    "metodo_pago": str(
                        rng.choice(
                            PAYMENT_METHODS,
                            p=PAYMENT_PROBABILITIES,
                        )
                    ),
                    "estado_pedido": order_status,
                    "dias_entrega": delivery_days,
                    "devolucion": returned,
                    "datos_sinteticos": True,
                }

                records.append(record)

                if product_warning:
                    LOGGER.debug(
                        "Pedido generado con producto "
                        "posteriormente descontinuado: %s",
                        product_id,
                    )

    orders = pd.DataFrame(
        records,
        columns=ORDER_COLUMNS,
    )

    _validate_generated_orders(
        orders=orders,
        products=products,
        customers=customers,
        start_date=start_date,
        end_date=end_date,
        minimum_units=minimum_units,
        maximum_units=maximum_units,
    )

    LOGGER.info(
        "Pedidos generados correctamente: %s pedidos y "
        "%s líneas.",
        orders["pedido_id"].nunique(),
        len(orders),
    )

    return orders


def _validate_generated_orders(
    orders: pd.DataFrame,
    products: pd.DataFrame,
    customers: pd.DataFrame,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    minimum_units: int,
    maximum_units: int,
) -> None:
    """Valida las líneas de pedido generadas.

    Args:
        orders: Líneas generadas.
        products: Catálogo de productos.
        customers: Catálogo de clientes.
        start_date: Fecha mínima permitida.
        end_date: Fecha máxima permitida.
        minimum_units: Cantidad mínima permitida.
        maximum_units: Cantidad máxima permitida.

    Raises:
        ValueError: Si se incumple una regla de integridad.
    """
    if orders.empty:
        raise ValueError(
            "No se generaron líneas de pedido."
        )

    if orders["linea_pedido_id"].duplicated().any():
        raise ValueError(
            "Se detectaron líneas de pedido duplicadas."
        )

    if orders["linea_pedido_id"].isna().any():
        raise ValueError(
            "Se detectaron identificadores de línea vacíos."
        )

    valid_product_ids = set(products["producto_id"])
    generated_product_ids = set(orders["producto_id"])

    if not generated_product_ids.issubset(
        valid_product_ids
    ):
        raise ValueError(
            "Existen pedidos asociados a productos inexistentes."
        )

    valid_customer_ids = set(customers["cliente_id"])
    generated_customer_ids = set(orders["cliente_id"])

    if not generated_customer_ids.issubset(
        valid_customer_ids
    ):
        raise ValueError(
            "Existen pedidos asociados a clientes inexistentes."
        )

    order_dates = pd.to_datetime(
        orders["fecha_pedido"]
    )

    if not order_dates.between(
        start_date,
        end_date,
        inclusive="both",
    ).all():
        raise ValueError(
            "Se detectaron pedidos fuera del periodo."
        )

    if not orders["unidades"].between(
        minimum_units,
        maximum_units,
        inclusive="both",
    ).all():
        raise ValueError(
            "Se detectaron cantidades fuera del rango."
        )

    expected_gross_value = (
        orders["unidades"]
        * orders["precio_unitario_cop"]
    )

    if not expected_gross_value.equals(
        orders["valor_bruto_cop"]
    ):
        raise ValueError(
            "Existen valores brutos inconsistentes."
        )

    expected_net_value = (
        orders["valor_bruto_cop"]
        - orders["valor_descuento_cop"]
    )

    if not expected_net_value.equals(
        orders["valor_neto_cop"]
    ):
        raise ValueError(
            "Existen valores netos inconsistentes."
        )

    expected_cost = (
        orders["unidades"]
        * orders["costo_unitario_cop"]
    )

    if not expected_cost.equals(
        orders["costo_total_cop"]
    ):
        raise ValueError(
            "Existen costos totales inconsistentes."
        )

    expected_margin = (
        orders["valor_neto_cop"]
        - orders["costo_total_cop"]
    )

    if not expected_margin.equals(
        orders["margen_bruto_cop"]
    ):
        raise ValueError(
            "Existen márgenes brutos inconsistentes."
        )

    cancelled_orders = orders[
        orders["estado_pedido"] == "Cancelado"
    ]

    if not cancelled_orders.empty:
        if not (
            cancelled_orders["dias_entrega"] == 0
        ).all():
            raise ValueError(
                "Los pedidos cancelados deben tener cero días "
                "de entrega."
            )

        if cancelled_orders["devolucion"].any():
            raise ValueError(
                "Un pedido cancelado no puede figurar devuelto."
            )

    returned_orders = orders[
        orders["estado_pedido"] == "Devuelto"
    ]

    if not returned_orders.empty:
        if not returned_orders["devolucion"].all():
            raise ValueError(
                "Los pedidos devueltos deben estar marcados."
            )

    if not orders["datos_sinteticos"].all():
        raise ValueError(
            "Todos los pedidos deben identificarse como sintéticos."
        )