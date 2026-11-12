"""Pruebas automáticas para los generadores de datos sintéticos."""

from __future__ import annotations

import pandas as pd

from novaretail.config import load_data_generation_config
from novaretail.generation.customers import (
    ACQUISITION_CHANNELS,
    CUSTOMER_COLUMNS,
    CUSTOMER_STATES,
    CUSTOMER_TYPES,
    LOCATIONS,
    generate_customers,
)
from novaretail.generation.products import (
    PRODUCT_COLUMNS,
    generate_products,
)


# ============================================================
# PRUEBAS DEL GENERADOR DE PRODUCTOS
# ============================================================


def test_generate_products_has_expected_dimensions() -> None:
    """Comprueba la cantidad esperada de filas y columnas."""
    configuration = load_data_generation_config()
    expected_products = configuration["volumes"]["products"]

    products = generate_products()

    assert products.shape == (
        expected_products,
        len(PRODUCT_COLUMNS),
    )


def test_generate_products_has_expected_columns() -> None:
    """Comprueba el orden y nombre de las columnas."""
    products = generate_products()

    assert products.columns.tolist() == PRODUCT_COLUMNS


def test_product_identifiers_are_unique_and_complete() -> None:
    """Comprueba la integridad de los identificadores."""
    products = generate_products()

    assert products["producto_id"].notna().all()
    assert products["producto_id"].is_unique
    assert products["producto_id"].str.match(
        r"^PROD-\d{4}$"
    ).all()


def test_product_prices_are_within_configured_range() -> None:
    """Comprueba que los precios respeten la configuración."""
    configuration = load_data_generation_config()

    minimum_price = configuration["pricing"][
        "minimum_product_price_cop"
    ]
    maximum_price = configuration["pricing"][
        "maximum_product_price_cop"
    ]

    products = generate_products()

    assert products["precio_lista_cop"].between(
        minimum_price,
        maximum_price,
        inclusive="both",
    ).all()


def test_product_cost_is_lower_than_list_price() -> None:
    """Comprueba que el costo sea inferior al precio de lista."""
    products = generate_products()

    assert (
        products["costo_estandar_cop"]
        < products["precio_lista_cop"]
    ).all()


def test_product_margin_matches_price_and_cost() -> None:
    """Comprueba el margen calculado para cada producto."""
    products = generate_products()

    expected_margin = (
        (
            products["precio_lista_cop"]
            - products["costo_estandar_cop"]
        )
        / products["precio_lista_cop"]
    ).round(4)

    pd.testing.assert_series_equal(
        products["margen_objetivo"],
        expected_margin,
        check_names=False,
    )


def test_all_products_are_identified_as_synthetic() -> None:
    """Comprueba la identificación explícita de datos sintéticos."""
    products = generate_products()

    assert products["datos_sinteticos"].all()


def test_generate_products_is_reproducible() -> None:
    """Comprueba que la misma semilla produzca el mismo catálogo."""
    first_products = generate_products()
    second_products = generate_products()

    pd.testing.assert_frame_equal(
        first_products,
        second_products,
    )


def test_different_seed_changes_generated_product_catalog() -> None:
    """Comprueba que una semilla distinta cambie los productos."""
    default_products = generate_products()
    alternative_products = generate_products(
        random_seed=20261105
    )

    assert not default_products.equals(
        alternative_products
    )


def test_product_categories_are_authorized() -> None:
    """Comprueba que solo existan categorías configuradas."""
    configuration = load_data_generation_config()
    allowed_categories = set(
        configuration["product_catalog"]["categories"]
    )

    products = generate_products()
    generated_categories = set(products["categoria"].unique())

    assert generated_categories.issubset(
        allowed_categories
    )


def test_product_entry_dates_are_inside_project_period() -> None:
    """Comprueba que las fechas estén dentro del periodo definido."""
    configuration = load_data_generation_config()

    minimum_date = pd.Timestamp(
        configuration["period"]["start_date"]
    ).date()
    maximum_date = pd.Timestamp(
        configuration["period"]["end_date"]
    ).date()

    products = generate_products()

    assert products["fecha_ingreso"].between(
        minimum_date,
        maximum_date,
        inclusive="both",
    ).all()


# ============================================================
# PRUEBAS DEL GENERADOR DE CLIENTES
# ============================================================


def test_generate_customers_has_expected_dimensions() -> None:
    """Comprueba la cantidad esperada de clientes y columnas."""
    configuration = load_data_generation_config()
    expected_customers = configuration["volumes"]["customers"]

    customers = generate_customers()

    assert customers.shape == (
        expected_customers,
        len(CUSTOMER_COLUMNS),
    )


def test_generate_customers_has_expected_columns() -> None:
    """Comprueba el orden y nombre de las columnas."""
    customers = generate_customers()

    assert customers.columns.tolist() == CUSTOMER_COLUMNS


def test_customer_identifiers_are_unique_and_complete() -> None:
    """Comprueba la integridad de los identificadores."""
    customers = generate_customers()

    assert customers["cliente_id"].notna().all()
    assert customers["cliente_id"].is_unique
    assert customers["cliente_id"].str.match(
        r"^CLI-\d{5}$"
    ).all()


def test_customer_registration_dates_are_valid() -> None:
    """Comprueba que las fechas estén dentro del periodo."""
    configuration = load_data_generation_config()

    minimum_date = pd.Timestamp(
        configuration["period"]["start_date"]
    ).date()
    maximum_date = pd.Timestamp(
        configuration["period"]["end_date"]
    ).date()

    customers = generate_customers()

    assert customers["fecha_registro"].between(
        minimum_date,
        maximum_date,
        inclusive="both",
    ).all()


def test_customer_segments_are_authorized() -> None:
    """Comprueba que solo existan segmentos configurados."""
    configuration = load_data_generation_config()

    allowed_segments = set(
        configuration["customer_segments"]["values"]
    )

    customers = generate_customers()
    generated_segments = set(customers["segmento"].unique())

    assert generated_segments.issubset(
        allowed_segments
    )


def test_customer_locations_are_authorized() -> None:
    """Comprueba que ciudad y departamento correspondan."""
    allowed_locations = set(LOCATIONS)
    customers = generate_customers()

    generated_locations = set(
        zip(
            customers["ciudad"],
            customers["departamento"],
        )
    )

    assert generated_locations.issubset(
        allowed_locations
    )


def test_customer_types_are_authorized() -> None:
    """Comprueba los tipos de cliente generados."""
    customers = generate_customers()

    assert set(
        customers["tipo_cliente"].unique()
    ).issubset(set(CUSTOMER_TYPES))


def test_customer_acquisition_channels_are_authorized() -> None:
    """Comprueba los canales de adquisición."""
    customers = generate_customers()

    assert set(
        customers["canal_adquisicion"].unique()
    ).issubset(set(ACQUISITION_CHANNELS))


def test_customer_states_are_authorized() -> None:
    """Comprueba los estados de cliente generados."""
    customers = generate_customers()

    assert set(
        customers["estado_cliente"].unique()
    ).issubset(set(CUSTOMER_STATES))


def test_all_customers_are_identified_as_synthetic() -> None:
    """Comprueba la identificación explícita como sintéticos."""
    customers = generate_customers()

    assert customers["datos_sinteticos"].all()


def test_generate_customers_is_reproducible() -> None:
    """Comprueba que la misma semilla produzca los mismos clientes."""
    first_customers = generate_customers()
    second_customers = generate_customers()

    pd.testing.assert_frame_equal(
        first_customers,
        second_customers,
    )


def test_different_seed_changes_generated_customers() -> None:
    """Comprueba que una semilla distinta cambie los clientes."""
    default_customers = generate_customers()
    alternative_customers = generate_customers(
        random_seed=20261205
    )

    assert not default_customers.equals(
        alternative_customers
    )


def test_customer_marketing_consent_is_boolean() -> None:
    """Comprueba que el consentimiento sea booleano."""
    customers = generate_customers()

    assert customers["acepta_marketing"].dtype == bool