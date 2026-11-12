"""Pruebas automáticas para el generador de inventario sintético."""

from __future__ import annotations

import pandas as pd
import pytest

from novaretail.config import load_data_generation_config
from novaretail.generation.customers import generate_customers
from novaretail.generation.inventory import (
    INVENTORY_COLUMNS,
    MAXIMUM_ADJUSTMENT,
    MINIMUM_ADJUSTMENT,
    generate_inventory,
)
from novaretail.generation.orders import generate_orders
from novaretail.generation.products import generate_products


@pytest.fixture(scope="module")
def products() -> pd.DataFrame:
    """Genera una sola vez el catálogo sintético de productos."""
    return generate_products()


@pytest.fixture(scope="module")
def customers() -> pd.DataFrame:
    """Genera una sola vez el catálogo sintético de clientes."""
    return generate_customers()


@pytest.fixture(scope="module")
def orders(
    products: pd.DataFrame,
    customers: pd.DataFrame,
) -> pd.DataFrame:
    """Genera una sola vez las líneas sintéticas de pedido."""
    return generate_orders(
        products=products,
        customers=customers,
    )


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


def test_inventory_has_expected_columns(
    inventory: pd.DataFrame,
) -> None:
    """Comprueba el nombre y orden de las columnas."""
    assert inventory.columns.tolist() == INVENTORY_COLUMNS


def test_inventory_is_not_empty(
    inventory: pd.DataFrame,
) -> None:
    """Comprueba que se hayan generado registros."""
    assert not inventory.empty


def test_inventory_contains_all_products(
    inventory: pd.DataFrame,
    products: pd.DataFrame,
) -> None:
    """Comprueba que todos los productos tengan inventario."""
    inventory_product_ids = set(
        inventory["producto_id"].unique()
    )

    product_ids = set(
        products["producto_id"]
    )

    assert inventory_product_ids == product_ids


def test_inventory_contains_expected_periods(
    inventory: pd.DataFrame,
) -> None:
    """Comprueba la cobertura temporal del inventario."""
    configuration = load_data_generation_config()

    expected_periods = pd.date_range(
        start=configuration["period"]["start_date"],
        end=configuration["period"]["end_date"],
        freq="MS",
    ).strftime("%Y-%m")

    generated_periods = sorted(
        inventory["periodo"].unique()
    )

    assert generated_periods == sorted(
        expected_periods.tolist()
    )


def test_inventory_has_one_record_per_product_and_period(
    inventory: pd.DataFrame,
) -> None:
    """Comprueba la unicidad producto-periodo."""
    duplicated_records = inventory.duplicated(
        subset=["periodo", "producto_id"]
    )

    assert not duplicated_records.any()


def test_inventory_references_existing_products(
    inventory: pd.DataFrame,
    products: pd.DataFrame,
) -> None:
    """Comprueba la integridad con el catálogo de productos."""
    inventory_product_ids = set(
        inventory["producto_id"]
    )

    valid_product_ids = set(
        products["producto_id"]
    )

    assert inventory_product_ids.issubset(
        valid_product_ids
    )


def test_inventory_categories_match_product_catalog(
    inventory: pd.DataFrame,
    products: pd.DataFrame,
) -> None:
    """Comprueba la categoría heredada del producto."""
    product_reference = products[
        ["producto_id", "categoria"]
    ].rename(
        columns={
            "categoria": "categoria_catalogo",
        }
    )

    comparison = inventory.merge(
        product_reference,
        on="producto_id",
        how="left",
        validate="many_to_one",
    )

    assert (
        comparison["categoria"]
        == comparison["categoria_catalogo"]
    ).all()


def test_inventory_starts_after_product_entry_date(
    inventory: pd.DataFrame,
    products: pd.DataFrame,
) -> None:
    """Comprueba que no exista inventario antes del ingreso."""
    product_reference = products[
        ["producto_id", "fecha_ingreso"]
    ].copy()

    comparison = inventory.merge(
        product_reference,
        on="producto_id",
        how="left",
        validate="many_to_one",
    )

    inventory_month_end = (
        pd.to_datetime(
            comparison["periodo"] + "-01"
        )
        + pd.offsets.MonthEnd(0)
    )

    entry_dates = pd.to_datetime(
        comparison["fecha_ingreso"]
    )

    assert (
        entry_dates <= inventory_month_end
    ).all()


def test_inventory_opening_balances_are_non_negative(
    inventory: pd.DataFrame,
) -> None:
    """Comprueba los saldos iniciales."""
    assert (
        inventory["inventario_inicial_unidades"] >= 0
    ).all()


def test_inventory_closing_balances_are_non_negative(
    inventory: pd.DataFrame,
) -> None:
    """Comprueba que no existan saldos finales negativos."""
    assert (
        inventory["inventario_final_unidades"] >= 0
    ).all()


def test_inventory_purchases_are_non_negative(
    inventory: pd.DataFrame,
) -> None:
    """Comprueba que las compras no sean negativas."""
    assert (
        inventory["compras_unidades"] >= 0
    ).all()


def test_inventory_sales_are_non_negative(
    inventory: pd.DataFrame,
) -> None:
    """Comprueba que las ventas no sean negativas."""
    assert (
        inventory["ventas_unidades"] >= 0
    ).all()


def test_inventory_returns_are_non_negative(
    inventory: pd.DataFrame,
) -> None:
    """Comprueba que las devoluciones no sean negativas."""
    assert (
        inventory["devoluciones_unidades"] >= 0
    ).all()


def test_inventory_adjustments_are_inside_allowed_range(
    inventory: pd.DataFrame,
) -> None:
    """Comprueba el rango de ajustes de inventario."""
    assert inventory["ajustes_unidades"].between(
        MINIMUM_ADJUSTMENT,
        MAXIMUM_ADJUSTMENT,
        inclusive="both",
    ).all()


def test_inventory_unit_reconciliation_is_correct(
    inventory: pd.DataFrame,
) -> None:
    """Comprueba la ecuación de movimiento de unidades."""
    expected_closing_stock = (
        inventory["inventario_inicial_unidades"]
        + inventory["compras_unidades"]
        + inventory["devoluciones_unidades"]
        + inventory["ajustes_unidades"]
        - inventory["ventas_unidades"]
    )

    pd.testing.assert_series_equal(
        inventory["inventario_final_unidades"],
        expected_closing_stock,
        check_names=False,
    )


def test_inventory_costs_are_positive(
    inventory: pd.DataFrame,
) -> None:
    """Comprueba que los costos promedio sean positivos."""
    assert (
        inventory["costo_promedio_cop"] > 0
    ).all()


def test_inventory_final_value_is_correct(
    inventory: pd.DataFrame,
) -> None:
    """Comprueba el valor monetario del inventario final."""
    expected_value = (
        inventory["inventario_final_unidades"]
        * inventory["costo_promedio_cop"]
    )

    pd.testing.assert_series_equal(
        inventory["valor_inventario_final_cop"],
        expected_value,
        check_names=False,
    )


def test_inventory_reorder_levels_are_positive(
    inventory: pd.DataFrame,
) -> None:
    """Comprueba que los niveles de reorden sean positivos."""
    assert (
        inventory["nivel_reorden_unidades"] > 0
    ).all()


def test_stockout_flag_is_boolean(
    inventory: pd.DataFrame,
) -> None:
    """Comprueba el tipo del indicador de quiebre."""
    assert inventory["quiebre_stock"].dtype == bool


def test_zero_closing_inventory_is_marked_as_stockout(
    inventory: pd.DataFrame,
) -> None:
    """Comprueba que un saldo cero se marque como quiebre."""
    zero_stock = inventory[
        inventory["inventario_final_unidades"] == 0
    ]

    if not zero_stock.empty:
        assert zero_stock["quiebre_stock"].all()


def test_inventory_sales_match_non_cancelled_orders(
    inventory: pd.DataFrame,
    orders: pd.DataFrame,
) -> None:
    """Comprueba que ventas coincidan con pedidos no cancelados."""
    expected_sales = (
        orders[
            orders["estado_pedido"] != "Cancelado"
        ]
        .groupby(
            ["periodo", "producto_id"],
            as_index=False,
        )["unidades"]
        .sum()
        .rename(
            columns={
                "unidades": "ventas_esperadas",
            }
        )
    )

    comparison = inventory.merge(
        expected_sales,
        on=["periodo", "producto_id"],
        how="left",
        validate="one_to_one",
    )

    comparison["ventas_esperadas"] = (
        comparison["ventas_esperadas"]
        .fillna(0)
        .astype(int)
    )

    assert (
        comparison["ventas_unidades"]
        == comparison["ventas_esperadas"]
    ).all()


def test_inventory_returns_match_returned_orders(
    inventory: pd.DataFrame,
    orders: pd.DataFrame,
) -> None:
    """Comprueba las unidades asociadas a devoluciones."""
    expected_returns = (
        orders[
            orders["estado_pedido"] == "Devuelto"
        ]
        .groupby(
            ["periodo", "producto_id"],
            as_index=False,
        )["unidades"]
        .sum()
        .rename(
            columns={
                "unidades": "devoluciones_esperadas",
            }
        )
    )

    comparison = inventory.merge(
        expected_returns,
        on=["periodo", "producto_id"],
        how="left",
        validate="one_to_one",
    )

    comparison["devoluciones_esperadas"] = (
        comparison["devoluciones_esperadas"]
        .fillna(0)
        .astype(int)
    )

    assert (
        comparison["devoluciones_unidades"]
        == comparison["devoluciones_esperadas"]
    ).all()


def test_inventory_continuity_between_periods(
    inventory: pd.DataFrame,
) -> None:
    """Comprueba continuidad entre cierre y apertura."""
    ordered_inventory = inventory.sort_values(
        ["producto_id", "periodo"]
    ).copy()

    previous_closing_stock = (
        ordered_inventory.groupby(
            "producto_id"
        )["inventario_final_unidades"]
        .shift(1)
    )

    comparable_rows = previous_closing_stock.notna()

    assert (
        ordered_inventory.loc[
            comparable_rows,
            "inventario_inicial_unidades",
        ].to_numpy()
        == previous_closing_stock.loc[
            comparable_rows
        ].to_numpy()
    ).all()


def test_all_inventory_records_are_synthetic(
    inventory: pd.DataFrame,
) -> None:
    """Comprueba la identificación como datos sintéticos."""
    assert inventory["datos_sinteticos"].all()


def test_inventory_is_reproducible(
    products: pd.DataFrame,
    orders: pd.DataFrame,
    inventory: pd.DataFrame,
) -> None:
    """Comprueba el resultado con la misma semilla."""
    second_inventory = generate_inventory(
        products=products,
        orders=orders,
    )

    pd.testing.assert_frame_equal(
        inventory,
        second_inventory,
    )


def test_different_seed_changes_inventory(
    products: pd.DataFrame,
    orders: pd.DataFrame,
    inventory: pd.DataFrame,
) -> None:
    """Comprueba que otra semilla cambie el inventario."""
    alternative_inventory = generate_inventory(
        products=products,
        orders=orders,
        random_seed=20261505,
    )

    assert not inventory.equals(
        alternative_inventory
    )