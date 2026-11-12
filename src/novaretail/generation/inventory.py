"""Generación reproducible del inventario mensual sintético.

Este módulo construye movimientos y saldos mensuales de inventario
por producto, utilizando las ventas registradas en los pedidos.

Todos los valores pertenecen a la empresa ficticia
NovaRetail Colombia S.A.S. y son exclusivamente académicos.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from novaretail.config import load_data_generation_config
from novaretail.logging_config import get_logger


LOGGER = get_logger(__name__)

INVENTORY_COLUMNS = [
    "periodo",
    "producto_id",
    "categoria",
    "inventario_inicial_unidades",
    "compras_unidades",
    "ventas_unidades",
    "devoluciones_unidades",
    "ajustes_unidades",
    "inventario_final_unidades",
    "costo_promedio_cop",
    "valor_inventario_final_cop",
    "nivel_reorden_unidades",
    "quiebre_stock",
    "datos_sinteticos",
]


INITIAL_STOCK_MINIMUM = 40
INITIAL_STOCK_MAXIMUM = 180

REORDER_LEVEL_MINIMUM = 15
REORDER_LEVEL_MAXIMUM = 55

PURCHASE_COVERAGE_MINIMUM = 1.20
PURCHASE_COVERAGE_MAXIMUM = 2.00

MINIMUM_ADJUSTMENT = -2
MAXIMUM_ADJUSTMENT = 3


def _validate_input_data(
    products: pd.DataFrame,
    orders: pd.DataFrame,
) -> None:
    """Valida los datos requeridos para generar inventario.

    Args:
        products: Catálogo sintético de productos.
        orders: Líneas sintéticas de pedidos.

    Raises:
        ValueError: Si falta información requerida.
    """
    required_product_columns = {
        "producto_id",
        "categoria",
        "costo_estandar_cop",
        "fecha_ingreso",
        "datos_sinteticos",
    }

    required_order_columns = {
        "producto_id",
        "fecha_pedido",
        "periodo",
        "unidades",
        "estado_pedido",
        "devolucion",
        "datos_sinteticos",
    }

    missing_product_columns = required_product_columns.difference(
        products.columns
    )

    missing_order_columns = required_order_columns.difference(
        orders.columns
    )

    if missing_product_columns:
        missing_text = ", ".join(
            sorted(missing_product_columns)
        )
        raise ValueError(
            f"Faltan columnas en productos: {missing_text}"
        )

    if missing_order_columns:
        missing_text = ", ".join(
            sorted(missing_order_columns)
        )
        raise ValueError(
            f"Faltan columnas en pedidos: {missing_text}"
        )

    if products.empty:
        raise ValueError(
            "El catálogo de productos está vacío."
        )

    if orders.empty:
        raise ValueError(
            "El conjunto de pedidos está vacío."
        )

    if products["producto_id"].duplicated().any():
        raise ValueError(
            "El catálogo contiene productos duplicados."
        )

    if not products["datos_sinteticos"].all():
        raise ValueError(
            "Los productos deben identificarse como sintéticos."
        )

    if not orders["datos_sinteticos"].all():
        raise ValueError(
            "Los pedidos deben identificarse como sintéticos."
        )


def _prepare_monthly_sales(
    orders: pd.DataFrame,
) -> pd.DataFrame:
    """Consolida las ventas mensuales por producto.

    Los pedidos cancelados no reducen el inventario. Las líneas
    entregadas y devueltas sí representan una salida inicial.

    Args:
        orders: Líneas de pedido generadas.

    Returns:
        Tabla mensual con las unidades vendidas.
    """
    valid_orders = orders[
        orders["estado_pedido"] != "Cancelado"
    ].copy()

    monthly_sales = (
        valid_orders.groupby(
            ["periodo", "producto_id"],
            as_index=False,
        )["unidades"]
        .sum()
        .rename(
            columns={"unidades": "ventas_unidades"}
        )
    )

    return monthly_sales


def _prepare_monthly_returns(
    orders: pd.DataFrame,
) -> pd.DataFrame:
    """Consolida unidades retornadas al inventario.

    Para esta primera versión, todas las unidades asociadas a una
    línea devuelta retornan al inventario del mismo periodo del pedido.

    Args:
        orders: Líneas de pedido generadas.

    Returns:
        Tabla mensual con unidades devueltas.
    """
    returned_orders = orders[
        orders["estado_pedido"] == "Devuelto"
    ].copy()

    monthly_returns = (
        returned_orders.groupby(
            ["periodo", "producto_id"],
            as_index=False,
        )["unidades"]
        .sum()
        .rename(
            columns={"unidades": "devoluciones_unidades"}
        )
    )

    return monthly_returns


def _calculate_purchase_units(
    opening_stock: int,
    sales_units: int,
    returned_units: int,
    reorder_level: int,
    rng: np.random.Generator,
) -> int:
    """Calcula las compras necesarias del periodo.

    Args:
        opening_stock: Inventario inicial del mes.
        sales_units: Unidades vendidas durante el mes.
        returned_units: Unidades devueltas durante el mes.
        reorder_level: Nivel mínimo deseado de inventario.
        rng: Generador aleatorio reproducible.

    Returns:
        Cantidad de unidades compradas.
    """
    projected_stock = (
        opening_stock
        + returned_units
        - sales_units
    )

    if projected_stock >= reorder_level:
        return 0

    coverage_factor = float(
        rng.uniform(
            PURCHASE_COVERAGE_MINIMUM,
            PURCHASE_COVERAGE_MAXIMUM,
        )
    )

    target_stock = max(
        int(round(sales_units * coverage_factor)),
        reorder_level,
    )

    purchase_units = target_stock - projected_stock

    return max(purchase_units, 0)


def generate_inventory(
    products: pd.DataFrame,
    orders: pd.DataFrame,
    random_seed: int | None = None,
) -> pd.DataFrame:
    """Genera el inventario mensual por producto.

    Args:
        products: Catálogo sintético de productos.
        orders: Líneas sintéticas de pedido.
        random_seed: Semilla alternativa de generación.

    Returns:
        DataFrame con movimientos y saldos mensuales.

    Raises:
        ValueError: Si los datos generados incumplen las reglas.
    """
    _validate_input_data(
        products=products,
        orders=orders,
    )

    configuration = load_data_generation_config()

    configured_seed = int(
        configuration["generation"]["random_seed"]
    )

    seed = (
        configured_seed + 400
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

    periods = pd.date_range(
        start=start_date,
        end=end_date,
        freq="MS",
    )

    monthly_sales = _prepare_monthly_sales(orders)
    monthly_returns = _prepare_monthly_returns(orders)

    sales_lookup = {
        (row.periodo, row.producto_id): int(
            row.ventas_unidades
        )
        for row in monthly_sales.itertuples(index=False)
    }

    returns_lookup = {
        (row.periodo, row.producto_id): int(
            row.devoluciones_unidades
        )
        for row in monthly_returns.itertuples(index=False)
    }

    opening_stock_by_product: dict[str, int] = {}
    reorder_level_by_product: dict[str, int] = {}

    records: list[dict] = []

    LOGGER.info(
        "Iniciando generación de inventario para %s productos "
        "y %s periodos.",
        len(products),
        len(periods),
    )

    for product in products.itertuples(index=False):
        product_id = str(product.producto_id)

        opening_stock_by_product[product_id] = int(
            rng.integers(
                INITIAL_STOCK_MINIMUM,
                INITIAL_STOCK_MAXIMUM + 1,
            )
        )

        reorder_level_by_product[product_id] = int(
            rng.integers(
                REORDER_LEVEL_MINIMUM,
                REORDER_LEVEL_MAXIMUM + 1,
            )
        )

    for period_start in periods:
        period = period_start.strftime("%Y-%m")

        for product in products.itertuples(index=False):
            product_id = str(product.producto_id)
            entry_date = pd.Timestamp(product.fecha_ingreso)

            if entry_date > period_start + pd.offsets.MonthEnd(0):
                continue

            opening_stock = opening_stock_by_product[
                product_id
            ]

            sales_units = sales_lookup.get(
                (period, product_id),
                0,
            )

            returned_units = returns_lookup.get(
                (period, product_id),
                0,
            )

            reorder_level = reorder_level_by_product[
                product_id
            ]

            adjustment_units = int(
                rng.integers(
                    MINIMUM_ADJUSTMENT,
                    MAXIMUM_ADJUSTMENT + 1,
                )
            )

            purchase_units = _calculate_purchase_units(
                opening_stock=opening_stock,
                sales_units=sales_units,
                returned_units=returned_units,
                reorder_level=reorder_level,
                rng=rng,
            )

            preliminary_closing_stock = (
                opening_stock
                + purchase_units
                + returned_units
                + adjustment_units
                - sales_units
            )

            if preliminary_closing_stock < 0:
                additional_purchase = abs(
                    preliminary_closing_stock
                )
                purchase_units += additional_purchase
                preliminary_closing_stock = 0

            closing_stock = int(
                preliminary_closing_stock
            )

            stockout = bool(
                closing_stock == 0
                or (
                    sales_units > 0
                    and opening_stock + purchase_units
                    < sales_units
                )
            )

            average_cost = int(
                product.costo_estandar_cop
            )

            ending_inventory_value = (
                closing_stock * average_cost
            )

            record = {
                "periodo": period,
                "producto_id": product_id,
                "categoria": product.categoria,
                "inventario_inicial_unidades": (
                    opening_stock
                ),
                "compras_unidades": purchase_units,
                "ventas_unidades": sales_units,
                "devoluciones_unidades": returned_units,
                "ajustes_unidades": adjustment_units,
                "inventario_final_unidades": closing_stock,
                "costo_promedio_cop": average_cost,
                "valor_inventario_final_cop": (
                    ending_inventory_value
                ),
                "nivel_reorden_unidades": reorder_level,
                "quiebre_stock": stockout,
                "datos_sinteticos": True,
            }

            records.append(record)

            opening_stock_by_product[
                product_id
            ] = closing_stock

    inventory = pd.DataFrame(
        records,
        columns=INVENTORY_COLUMNS,
    )

    _validate_generated_inventory(
        inventory=inventory,
        products=products,
    )

    LOGGER.info(
        "Inventario generado correctamente: %s registros.",
        len(inventory),
    )

    return inventory


def _validate_generated_inventory(
    inventory: pd.DataFrame,
    products: pd.DataFrame,
) -> None:
    """Valida el inventario generado.

    Args:
        inventory: Inventario mensual generado.
        products: Catálogo maestro de productos.

    Raises:
        ValueError: Si una regla de integridad falla.
    """
    if inventory.empty:
        raise ValueError(
            "No se generaron registros de inventario."
        )

    duplicated_rows = inventory.duplicated(
        subset=["periodo", "producto_id"]
    )

    if duplicated_rows.any():
        raise ValueError(
            "Existen productos duplicados dentro de un periodo."
        )

    valid_product_ids = set(products["producto_id"])
    inventory_product_ids = set(
        inventory["producto_id"]
    )

    if not inventory_product_ids.issubset(
        valid_product_ids
    ):
        raise ValueError(
            "Existen registros asociados a productos inexistentes."
        )

    expected_closing_stock = (
        inventory["inventario_inicial_unidades"]
        + inventory["compras_unidades"]
        + inventory["devoluciones_unidades"]
        + inventory["ajustes_unidades"]
        - inventory["ventas_unidades"]
    )

    if not expected_closing_stock.equals(
        inventory["inventario_final_unidades"]
    ):
        raise ValueError(
            "La conciliación del inventario presenta diferencias."
        )

    if (inventory["inventario_final_unidades"] < 0).any():
        raise ValueError(
            "Se detectaron saldos negativos de inventario."
        )

    expected_inventory_value = (
        inventory["inventario_final_unidades"]
        * inventory["costo_promedio_cop"]
    )

    if not expected_inventory_value.equals(
        inventory["valor_inventario_final_cop"]
    ):
        raise ValueError(
            "El valor final del inventario es inconsistente."
        )

    ordered_inventory = inventory.sort_values(
        ["producto_id", "periodo"]
    ).copy()

    previous_closing_stock = (
        ordered_inventory.groupby(
            "producto_id"
        )["inventario_final_unidades"]
        .shift(1)
    )

    continuity_rows = previous_closing_stock.notna()

    continuity_is_valid = (
        ordered_inventory.loc[
            continuity_rows,
            "inventario_inicial_unidades",
        ].to_numpy()
        == previous_closing_stock.loc[
            continuity_rows
        ].to_numpy()
    )

    if not continuity_is_valid.all():
        raise ValueError(
            "El inventario inicial no coincide con el cierre "
            "del periodo anterior."
        )

    if not inventory["datos_sinteticos"].all():
        raise ValueError(
            "Todos los registros deben identificarse como sintéticos."
        )