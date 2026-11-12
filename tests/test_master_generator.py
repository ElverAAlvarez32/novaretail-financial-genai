"""Pruebas automáticas del generador maestro de datos sintéticos."""

from __future__ import annotations

import pandas as pd
import pytest

from novaretail.config import (
    load_data_generation_config,
    load_settings,
)
from novaretail.generation.generator import (
    TABLE_ORDER,
    GeneratedData,
    generate_all_data,
)


@pytest.fixture(scope="module")
def generated_data() -> GeneratedData:
    """Ejecuta una sola vez la generación maestra."""
    return generate_all_data()


def test_master_generator_returns_expected_type(
    generated_data: GeneratedData,
) -> None:
    """Comprueba el tipo del resultado maestro."""
    assert isinstance(
        generated_data,
        GeneratedData,
    )


def test_master_generator_contains_expected_tables(
    generated_data: GeneratedData,
) -> None:
    """Comprueba los nombres y el orden de las doce tablas."""
    assert list(
        generated_data.as_dict().keys()
    ) == TABLE_ORDER


def test_master_generator_contains_twelve_tables(
    generated_data: GeneratedData,
) -> None:
    """Comprueba la cantidad total de tablas."""
    assert len(
        generated_data.as_dict()
    ) == 12


def test_all_generated_tables_are_dataframes(
    generated_data: GeneratedData,
) -> None:
    """Comprueba que todas las tablas sean DataFrames."""
    for dataframe in generated_data.as_dict().values():
        assert isinstance(
            dataframe,
            pd.DataFrame,
        )


def test_all_generated_tables_have_records(
    generated_data: GeneratedData,
) -> None:
    """Comprueba que ninguna tabla esté vacía."""
    for dataframe in generated_data.as_dict().values():
        assert not dataframe.empty


def test_control_table_identifies_synthetic_data(
    generated_data: GeneratedData,
) -> None:
    """Comprueba la declaración explícita de datos sintéticos."""
    control = generated_data.control.set_index(
        "campo"
    )["valor"]

    assert control["empresa_ficticia"] is True
    assert control["naturaleza_datos"] == (
        "Datos sintéticos"
    )
    assert control["uso"] == (
        "Exclusivamente académico"
    )


def test_control_table_contains_project_warning(
    generated_data: GeneratedData,
) -> None:
    """Comprueba que exista una advertencia de uso."""
    control = generated_data.control.set_index(
        "campo"
    )["valor"]

    warning = str(control["advertencia"])

    assert "ficticios" in warning
    assert "decisiones empresariales reales" in warning


def test_parameters_table_contains_random_seed(
    generated_data: GeneratedData,
) -> None:
    """Comprueba el registro de la semilla reproducible."""
    configuration = load_data_generation_config()

    seed_record = generated_data.parameters[
        generated_data.parameters["parametro"]
        == "generation.random_seed"
    ]

    assert len(seed_record) == 1
    assert int(
        seed_record.iloc[0]["valor"]
    ) == configuration["generation"]["random_seed"]


def test_product_count_matches_configuration(
    generated_data: GeneratedData,
) -> None:
    """Comprueba la cantidad configurada de productos."""
    configuration = load_data_generation_config()

    assert len(generated_data.products) == (
        configuration["volumes"]["products"]
    )


def test_customer_count_matches_configuration(
    generated_data: GeneratedData,
) -> None:
    """Comprueba la cantidad configurada de clientes."""
    configuration = load_data_generation_config()

    assert len(generated_data.customers) == (
        configuration["volumes"]["customers"]
    )


def test_order_lines_are_inside_configured_range(
    generated_data: GeneratedData,
) -> None:
    """Comprueba el volumen previsto de líneas de pedido."""
    configuration = load_data_generation_config()

    minimum_lines = configuration["volumes"][
        "minimum_order_lines"
    ]
    maximum_lines = configuration["volumes"][
        "maximum_order_lines"
    ]

    assert minimum_lines <= len(
        generated_data.orders
    ) <= maximum_lines


def test_monthly_financial_tables_have_expected_periods(
    generated_data: GeneratedData,
) -> None:
    """Comprueba los 36 periodos financieros."""
    expected_months = load_settings()["period"][
        "expected_months"
    ]

    assert len(
        generated_data.income_statement
    ) == expected_months

    assert len(
        generated_data.balance_sheet
    ) == expected_months

    assert len(
        generated_data.cash_flow
    ) == expected_months


def test_financial_tables_have_matching_periods(
    generated_data: GeneratedData,
) -> None:
    """Comprueba que los periodos financieros coincidan."""
    income_periods = (
        generated_data.income_statement[
            "periodo"
        ].tolist()
    )

    balance_periods = (
        generated_data.balance_sheet[
            "periodo"
        ].tolist()
    )

    cash_flow_periods = (
        generated_data.cash_flow[
            "periodo"
        ].tolist()
    )

    assert income_periods == balance_periods
    assert balance_periods == cash_flow_periods


def test_return_count_matches_returned_order_lines(
    generated_data: GeneratedData,
) -> None:
    """Comprueba la relación entre pedidos y devoluciones."""
    returned_order_lines = generated_data.orders[
        generated_data.orders["estado_pedido"]
        == "Devuelto"
    ]

    assert len(
        generated_data.returns
    ) == len(returned_order_lines)


def test_inventory_references_existing_products(
    generated_data: GeneratedData,
) -> None:
    """Comprueba la integridad entre inventario y productos."""
    inventory_products = set(
        generated_data.inventory["producto_id"]
    )

    valid_products = set(
        generated_data.products["producto_id"]
    )

    assert inventory_products.issubset(
        valid_products
    )


def test_orders_reference_existing_products_and_customers(
    generated_data: GeneratedData,
) -> None:
    """Comprueba las relaciones maestras de los pedidos."""
    order_products = set(
        generated_data.orders["producto_id"]
    )

    valid_products = set(
        generated_data.products["producto_id"]
    )

    order_customers = set(
        generated_data.orders["cliente_id"]
    )

    valid_customers = set(
        generated_data.customers["cliente_id"]
    )

    assert order_products.issubset(valid_products)
    assert order_customers.issubset(valid_customers)


def test_balance_sheet_is_balanced(
    generated_data: GeneratedData,
) -> None:
    """Comprueba la ecuación contable mensual."""
    balance_sheet = generated_data.balance_sheet

    assert (
        balance_sheet["total_activos_cop"]
        == balance_sheet[
            "total_pasivo_patrimonio_cop"
        ]
    ).all()

    assert (
        balance_sheet["diferencia_balance_cop"] == 0
    ).all()


def test_cash_flow_is_reconciled(
    generated_data: GeneratedData,
) -> None:
    """Comprueba la conciliación mensual del efectivo."""
    cash_flow = generated_data.cash_flow

    assert (
        cash_flow["efectivo_final_cop"]
        == cash_flow["efectivo_inicial_cop"]
        + cash_flow["variacion_neta_efectivo_cop"]
    ).all()

    assert (
        cash_flow["diferencia_conciliacion_cop"] == 0
    ).all()


def test_cash_flow_matches_balance_sheet(
    generated_data: GeneratedData,
) -> None:
    """Comprueba el efectivo entre flujo y balance."""
    cash_flow = generated_data.cash_flow.sort_values(
        "periodo"
    )

    balance_sheet = (
        generated_data.balance_sheet.sort_values(
            "periodo"
        )
    )

    assert (
        cash_flow["efectivo_final_cop"].to_numpy()
        == balance_sheet["efectivo_cop"].to_numpy()
    ).all()


def test_budget_contains_eight_categories_per_period(
    generated_data: GeneratedData,
) -> None:
    """Comprueba las categorías del presupuesto."""
    category_count = (
        generated_data.budget.groupby(
            "periodo"
        )["categoria"].nunique()
    )

    assert (category_count == 8).all()


def test_budget_has_expected_record_count(
    generated_data: GeneratedData,
) -> None:
    """Comprueba los 288 registros presupuestales."""
    expected_months = load_settings()["period"][
        "expected_months"
    ]

    expected_records = expected_months * 8

    assert len(
        generated_data.budget
    ) == expected_records


def test_key_identifiers_are_unique(
    generated_data: GeneratedData,
) -> None:
    """Comprueba los identificadores principales."""
    assert generated_data.products[
        "producto_id"
    ].is_unique

    assert generated_data.customers[
        "cliente_id"
    ].is_unique

    assert generated_data.orders[
        "linea_pedido_id"
    ].is_unique

    assert generated_data.returns[
        "devolucion_id"
    ].is_unique

    assert generated_data.marketing[
        "campania_id"
    ].is_unique

    assert generated_data.budget[
        "presupuesto_id"
    ].is_unique


def test_operational_tables_are_identified_as_synthetic(
    generated_data: GeneratedData,
) -> None:
    """Comprueba la identificación de tablas operativas."""
    operational_tables = [
        generated_data.products,
        generated_data.customers,
        generated_data.orders,
        generated_data.inventory,
        generated_data.returns,
        generated_data.marketing,
    ]

    for dataframe in operational_tables:
        assert dataframe["datos_sinteticos"].all()


def test_financial_tables_are_identified_as_synthetic(
    generated_data: GeneratedData,
) -> None:
    """Comprueba la identificación de tablas financieras."""
    financial_tables = [
        generated_data.income_statement,
        generated_data.balance_sheet,
        generated_data.cash_flow,
        generated_data.budget,
    ]

    for dataframe in financial_tables:
        assert dataframe["datos_sinteticos"].all()


def test_row_summary_matches_generated_tables(
    generated_data: GeneratedData,
) -> None:
    """Comprueba el resumen de filas."""
    expected_summary = {
        table_name: len(dataframe)
        for table_name, dataframe
        in generated_data.iter_tables()
    }

    assert (
        generated_data.row_summary()
        == expected_summary
    )


def test_master_generator_is_reproducible(
    generated_data: GeneratedData,
) -> None:
    """Comprueba la reproducibilidad del conjunto completo."""
    second_generation = generate_all_data()

    for table_name in TABLE_ORDER:
        pd.testing.assert_frame_equal(
            generated_data.as_dict()[table_name],
            second_generation.as_dict()[table_name],
        )