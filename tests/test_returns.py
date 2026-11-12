"""Pruebas automáticas para el generador de devoluciones sintéticas."""

from __future__ import annotations

import pandas as pd
import pytest

from novaretail.config import load_data_generation_config
from novaretail.generation.customers import generate_customers
from novaretail.generation.orders import generate_orders
from novaretail.generation.products import generate_products
from novaretail.generation.returns import (
    MAXIMUM_LOGISTICS_COST_COP,
    MAXIMUM_RETURN_DAYS,
    MINIMUM_LOGISTICS_COST_COP,
    MINIMUM_RETURN_DAYS,
    RETURN_COLUMNS,
    RETURN_REASONS,
    RETURN_STATES,
    generate_returns,
)


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


def test_returns_have_expected_columns(
    returns: pd.DataFrame,
) -> None:
    """Comprueba el nombre y orden de las columnas."""
    assert returns.columns.tolist() == RETURN_COLUMNS


def test_return_count_matches_returned_order_lines(
    returns: pd.DataFrame,
    orders: pd.DataFrame,
) -> None:
    """Comprueba que cada línea devuelta tenga un registro."""
    returned_order_lines = orders[
        orders["estado_pedido"] == "Devuelto"
    ]

    assert len(returns) == len(returned_order_lines)


def test_return_identifiers_are_unique(
    returns: pd.DataFrame,
) -> None:
    """Comprueba la integridad de los identificadores."""
    assert returns["devolucion_id"].notna().all()
    assert returns["devolucion_id"].is_unique
    assert returns["devolucion_id"].str.match(
        r"^DEV-\d{6}$"
    ).all()


def test_only_one_return_exists_per_order_line(
    returns: pd.DataFrame,
) -> None:
    """Comprueba que una línea genere una sola devolución."""
    assert returns["linea_pedido_id"].notna().all()
    assert returns["linea_pedido_id"].is_unique


def test_returns_reference_returned_order_lines(
    returns: pd.DataFrame,
    orders: pd.DataFrame,
) -> None:
    """Comprueba la relación con las líneas devueltas."""
    expected_line_ids = set(
        orders.loc[
            orders["estado_pedido"] == "Devuelto",
            "linea_pedido_id",
        ]
    )

    generated_line_ids = set(
        returns["linea_pedido_id"]
    )

    assert generated_line_ids == expected_line_ids


def test_returns_reference_existing_orders(
    returns: pd.DataFrame,
    orders: pd.DataFrame,
) -> None:
    """Comprueba la relación con pedidos existentes."""
    valid_order_ids = set(orders["pedido_id"])
    return_order_ids = set(returns["pedido_id"])

    assert return_order_ids.issubset(valid_order_ids)


def test_returns_reference_existing_products(
    returns: pd.DataFrame,
    products: pd.DataFrame,
) -> None:
    """Comprueba la relación con productos existentes."""
    valid_product_ids = set(products["producto_id"])
    return_product_ids = set(returns["producto_id"])

    assert return_product_ids.issubset(
        valid_product_ids
    )


def test_returns_reference_existing_customers(
    returns: pd.DataFrame,
    customers: pd.DataFrame,
) -> None:
    """Comprueba la relación con clientes existentes."""
    valid_customer_ids = set(customers["cliente_id"])
    return_customer_ids = set(returns["cliente_id"])

    assert return_customer_ids.issubset(
        valid_customer_ids
    )


def test_return_dates_are_inside_project_period(
    returns: pd.DataFrame,
) -> None:
    """Comprueba que las fechas estén dentro del periodo."""
    configuration = load_data_generation_config()

    minimum_date = pd.Timestamp(
        configuration["period"]["start_date"]
    ).date()

    maximum_date = pd.Timestamp(
        configuration["period"]["end_date"]
    ).date()

    assert returns["fecha_devolucion"].between(
        minimum_date,
        maximum_date,
        inclusive="both",
    ).all()


def test_return_period_matches_return_date(
    returns: pd.DataFrame,
) -> None:
    """Comprueba que el periodo coincida con la fecha."""
    expected_period = pd.to_datetime(
        returns["fecha_devolucion"]
    ).dt.strftime("%Y-%m")

    pd.testing.assert_series_equal(
        returns["periodo_devolucion"],
        expected_period,
        check_names=False,
    )


def test_return_units_are_positive(
    returns: pd.DataFrame,
) -> None:
    """Comprueba que las unidades devueltas sean positivas."""
    assert (
        returns["unidades_devueltas"] >= 1
    ).all()


def test_return_units_do_not_exceed_ordered_units(
    returns: pd.DataFrame,
    orders: pd.DataFrame,
) -> None:
    """Comprueba que no se devuelvan más unidades que las compradas."""
    ordered_units = orders[
        ["linea_pedido_id", "unidades"]
    ].rename(
        columns={"unidades": "unidades_compradas"}
    )

    comparison = returns.merge(
        ordered_units,
        on="linea_pedido_id",
        how="left",
        validate="one_to_one",
    )

    assert (
        comparison["unidades_devueltas"]
        <= comparison["unidades_compradas"]
    ).all()


def test_refund_values_are_positive(
    returns: pd.DataFrame,
) -> None:
    """Comprueba que los reintegros sean positivos."""
    assert (
        returns["valor_reintegrado_cop"] > 0
    ).all()


def test_refund_values_do_not_exceed_order_net_value(
    returns: pd.DataFrame,
    orders: pd.DataFrame,
) -> None:
    """Comprueba que el reintegro no supere el valor neto."""
    order_values = orders[
        ["linea_pedido_id", "valor_neto_cop"]
    ]

    comparison = returns.merge(
        order_values,
        on="linea_pedido_id",
        how="left",
        validate="one_to_one",
    )

    assert (
        comparison["valor_reintegrado_cop"]
        <= comparison["valor_neto_cop"]
    ).all()


def test_logistics_costs_are_inside_allowed_range(
    returns: pd.DataFrame,
) -> None:
    """Comprueba el rango de los costos logísticos."""
    assert returns["costo_logistico_cop"].between(
        MINIMUM_LOGISTICS_COST_COP,
        MAXIMUM_LOGISTICS_COST_COP,
        inclusive="both",
    ).all()


def test_total_return_cost_is_correct(
    returns: pd.DataFrame,
) -> None:
    """Comprueba el costo total de la devolución."""
    expected_cost = (
        returns["valor_reintegrado_cop"]
        + returns["costo_logistico_cop"]
    )

    pd.testing.assert_series_equal(
        returns["costo_total_devolucion_cop"],
        expected_cost,
        check_names=False,
    )


def test_return_days_are_inside_allowed_range(
    returns: pd.DataFrame,
) -> None:
    """Comprueba los días transcurridos desde la entrega."""
    assert returns["dias_desde_entrega"].between(
        MINIMUM_RETURN_DAYS,
        MAXIMUM_RETURN_DAYS,
        inclusive="both",
    ).all()


def test_return_reasons_are_authorized(
    returns: pd.DataFrame,
) -> None:
    """Comprueba los motivos de devolución."""
    generated_reasons = set(
        returns["motivo_devolucion"].unique()
    )

    assert generated_reasons.issubset(
        set(RETURN_REASONS)
    )


def test_return_states_are_authorized(
    returns: pd.DataFrame,
) -> None:
    """Comprueba los estados de devolución."""
    generated_states = set(
        returns["estado_devolucion"].unique()
    )

    assert generated_states.issubset(
        set(RETURN_STATES)
    )


def test_return_customer_product_and_category_match_order(
    returns: pd.DataFrame,
    orders: pd.DataFrame,
) -> None:
    """Comprueba los datos heredados de la línea original."""
    order_reference = orders[
        [
            "linea_pedido_id",
            "cliente_id",
            "producto_id",
            "categoria",
        ]
    ].rename(
        columns={
            "cliente_id": "cliente_id_original",
            "producto_id": "producto_id_original",
            "categoria": "categoria_original",
        }
    )

    comparison = returns.merge(
        order_reference,
        on="linea_pedido_id",
        how="left",
        validate="one_to_one",
    )

    assert (
        comparison["cliente_id"]
        == comparison["cliente_id_original"]
    ).all()

    assert (
        comparison["producto_id"]
        == comparison["producto_id_original"]
    ).all()

    assert (
        comparison["categoria"]
        == comparison["categoria_original"]
    ).all()


def test_all_returns_are_identified_as_synthetic(
    returns: pd.DataFrame,
) -> None:
    """Comprueba la identificación de los datos sintéticos."""
    assert returns["datos_sinteticos"].all()


def test_returns_are_reproducible(
    orders: pd.DataFrame,
    returns: pd.DataFrame,
) -> None:
    """Comprueba que la semilla produzca el mismo resultado."""
    second_returns = generate_returns(orders=orders)

    pd.testing.assert_frame_equal(
        returns,
        second_returns,
    )


def test_different_seed_changes_returns(
    orders: pd.DataFrame,
    returns: pd.DataFrame,
) -> None:
    """Comprueba que otra semilla cambie las devoluciones."""
    alternative_returns = generate_returns(
        orders=orders,
        random_seed=20261405,
    )

    assert not returns.equals(
        alternative_returns
    )