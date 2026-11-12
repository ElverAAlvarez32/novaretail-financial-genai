"""Pruebas automáticas para el generador de pedidos sintéticos."""

from __future__ import annotations

import pandas as pd
import pytest

from novaretail.config import load_data_generation_config
from novaretail.generation.customers import generate_customers
from novaretail.generation.orders import (
    ORDER_CHANNELS,
    ORDER_COLUMNS,
    generate_orders,
)
from novaretail.generation.products import generate_products


@pytest.fixture(scope="module")
def products() -> pd.DataFrame:
    """Genera una sola vez el catálogo de productos para las pruebas."""
    return generate_products()


@pytest.fixture(scope="module")
def customers() -> pd.DataFrame:
    """Genera una sola vez el catálogo de clientes para las pruebas."""
    return generate_customers()


@pytest.fixture(scope="module")
def orders(
    products: pd.DataFrame,
    customers: pd.DataFrame,
) -> pd.DataFrame:
    """Genera una sola vez las líneas de pedido para las pruebas."""
    return generate_orders(
        products=products,
        customers=customers,
    )


def test_orders_have_expected_columns(
    orders: pd.DataFrame,
) -> None:
    """Comprueba el nombre y orden de las columnas."""
    assert orders.columns.tolist() == ORDER_COLUMNS


def test_order_lines_are_inside_configured_range(
    orders: pd.DataFrame,
) -> None:
    """Comprueba que el volumen esté dentro del rango previsto."""
    configuration = load_data_generation_config()

    minimum_lines = configuration["volumes"][
        "minimum_order_lines"
    ]
    maximum_lines = configuration["volumes"][
        "maximum_order_lines"
    ]

    assert minimum_lines <= len(orders) <= maximum_lines


def test_order_line_identifiers_are_unique(
    orders: pd.DataFrame,
) -> None:
    """Comprueba la unicidad de las líneas de pedido."""
    assert orders["linea_pedido_id"].notna().all()
    assert orders["linea_pedido_id"].is_unique
    assert orders["linea_pedido_id"].str.match(
        r"^LIN-\d{6}$"
    ).all()


def test_order_identifiers_have_valid_format(
    orders: pd.DataFrame,
) -> None:
    """Comprueba el formato de los identificadores de pedido."""
    assert orders["pedido_id"].notna().all()
    assert orders["pedido_id"].str.match(
        r"^PED-\d{6}$"
    ).all()


def test_orders_reference_existing_products(
    orders: pd.DataFrame,
    products: pd.DataFrame,
) -> None:
    """Comprueba la integridad entre pedidos y productos."""
    generated_product_ids = set(
        orders["producto_id"].unique()
    )
    valid_product_ids = set(
        products["producto_id"]
    )

    assert generated_product_ids.issubset(
        valid_product_ids
    )


def test_orders_reference_existing_customers(
    orders: pd.DataFrame,
    customers: pd.DataFrame,
) -> None:
    """Comprueba la integridad entre pedidos y clientes."""
    generated_customer_ids = set(
        orders["cliente_id"].unique()
    )
    valid_customer_ids = set(
        customers["cliente_id"]
    )

    assert generated_customer_ids.issubset(
        valid_customer_ids
    )


def test_order_dates_are_inside_project_period(
    orders: pd.DataFrame,
) -> None:
    """Comprueba que las fechas estén dentro del periodo."""
    configuration = load_data_generation_config()

    minimum_date = pd.Timestamp(
        configuration["period"]["start_date"]
    ).date()

    maximum_date = pd.Timestamp(
        configuration["period"]["end_date"]
    ).date()

    assert orders["fecha_pedido"].between(
        minimum_date,
        maximum_date,
        inclusive="both",
    ).all()


def test_order_period_matches_order_date(
    orders: pd.DataFrame,
) -> None:
    """Comprueba que el periodo coincida con la fecha del pedido."""
    expected_period = pd.to_datetime(
        orders["fecha_pedido"]
    ).dt.strftime("%Y-%m")

    pd.testing.assert_series_equal(
        orders["periodo"],
        expected_period,
        check_names=False,
    )


def test_order_units_are_inside_configured_range(
    orders: pd.DataFrame,
) -> None:
    """Comprueba las cantidades vendidas."""
    configuration = load_data_generation_config()

    minimum_units = configuration["sales"][
        "minimum_units_per_order"
    ]

    maximum_units = configuration["sales"][
        "maximum_units_per_order"
    ]

    assert orders["unidades"].between(
        minimum_units,
        maximum_units,
        inclusive="both",
    ).all()


def test_order_prices_and_costs_are_positive(
    orders: pd.DataFrame,
) -> None:
    """Comprueba que precios y costos tengan valores positivos."""
    assert (orders["precio_unitario_cop"] > 0).all()
    assert (orders["costo_unitario_cop"] > 0).all()


def test_order_gross_values_are_correct(
    orders: pd.DataFrame,
) -> None:
    """Comprueba el cálculo del valor bruto."""
    expected_value = (
        orders["unidades"]
        * orders["precio_unitario_cop"]
    )

    pd.testing.assert_series_equal(
        orders["valor_bruto_cop"],
        expected_value,
        check_names=False,
    )


def test_order_discount_rates_are_valid(
    orders: pd.DataFrame,
) -> None:
    """Comprueba que los descuentos estén dentro del rango."""
    configuration = load_data_generation_config()

    maximum_discount = configuration["pricing"][
        "maximum_discount_rate"
    ]

    assert orders["descuento_rate"].between(
        0.0,
        maximum_discount,
        inclusive="both",
    ).all()


def test_order_discount_values_are_consistent(
    orders: pd.DataFrame,
) -> None:
    """Comprueba el valor monetario del descuento."""
    expected_discount = (
        orders["valor_bruto_cop"]
        * orders["descuento_rate"]
    ).round().astype(int)

    pd.testing.assert_series_equal(
        orders["valor_descuento_cop"],
        expected_discount,
        check_names=False,
    )


def test_order_net_values_are_correct(
    orders: pd.DataFrame,
) -> None:
    """Comprueba el cálculo del valor neto."""
    expected_value = (
        orders["valor_bruto_cop"]
        - orders["valor_descuento_cop"]
    )

    pd.testing.assert_series_equal(
        orders["valor_neto_cop"],
        expected_value,
        check_names=False,
    )


def test_order_total_costs_are_correct(
    orders: pd.DataFrame,
) -> None:
    """Comprueba el cálculo del costo total."""
    expected_cost = (
        orders["unidades"]
        * orders["costo_unitario_cop"]
    )

    pd.testing.assert_series_equal(
        orders["costo_total_cop"],
        expected_cost,
        check_names=False,
    )


def test_order_gross_margins_are_correct(
    orders: pd.DataFrame,
) -> None:
    """Comprueba el cálculo del margen bruto."""
    expected_margin = (
        orders["valor_neto_cop"]
        - orders["costo_total_cop"]
    )

    pd.testing.assert_series_equal(
        orders["margen_bruto_cop"],
        expected_margin,
        check_names=False,
    )


def test_order_states_are_authorized(
    orders: pd.DataFrame,
) -> None:
    """Comprueba que solo existan estados autorizados."""
    allowed_states = {
        "Entregado",
        "Devuelto",
        "Cancelado",
    }

    generated_states = set(
        orders["estado_pedido"].unique()
    )

    assert generated_states.issubset(
        allowed_states
    )


def test_cancelled_orders_have_no_delivery_or_return(
    orders: pd.DataFrame,
) -> None:
    """Comprueba las reglas aplicables a pedidos cancelados."""
    cancelled = orders[
        orders["estado_pedido"] == "Cancelado"
    ]

    assert not cancelled.empty
    assert (cancelled["dias_entrega"] == 0).all()
    assert not cancelled["devolucion"].any()


def test_returned_orders_are_marked_correctly(
    orders: pd.DataFrame,
) -> None:
    """Comprueba la identificación de pedidos devueltos."""
    returned = orders[
        orders["estado_pedido"] == "Devuelto"
    ]

    assert not returned.empty
    assert returned["devolucion"].all()
    assert (returned["dias_entrega"] > 0).all()


def test_delivered_orders_are_not_marked_as_returns(
    orders: pd.DataFrame,
) -> None:
    """Comprueba la consistencia de los pedidos entregados."""
    delivered = orders[
        orders["estado_pedido"] == "Entregado"
    ]

    assert not delivered.empty
    assert not delivered["devolucion"].any()
    assert (delivered["dias_entrega"] > 0).all()


def test_order_channels_are_authorized(
    orders: pd.DataFrame,
) -> None:
    """Comprueba los canales de venta generados."""
    generated_channels = set(
        orders["canal"].unique()
    )

    assert generated_channels.issubset(
        set(ORDER_CHANNELS)
    )


def test_all_orders_are_identified_as_synthetic(
    orders: pd.DataFrame,
) -> None:
    """Comprueba la identificación de los datos sintéticos."""
    assert orders["datos_sinteticos"].all()


def test_orders_are_reproducible(
    products: pd.DataFrame,
    customers: pd.DataFrame,
    orders: pd.DataFrame,
) -> None:
    """Comprueba la reproducibilidad del generador."""
    second_orders = generate_orders(
        products=products,
        customers=customers,
    )

    pd.testing.assert_frame_equal(
        orders,
        second_orders,
    )


def test_different_seed_changes_orders(
    products: pd.DataFrame,
    customers: pd.DataFrame,
    orders: pd.DataFrame,
) -> None:
    """Comprueba que una semilla realmente diferente cambie los pedidos."""
    alternative_orders = generate_orders(
        products=products,
        customers=customers,
        random_seed=20261305,
    )

    assert not orders.equals(
        alternative_orders
    )