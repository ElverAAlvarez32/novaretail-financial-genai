"""Pruebas automáticas del validador de relaciones de NovaRetail."""

from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd
import pytest
from openpyxl import load_workbook

from novaretail.config import (
    load_data_generation_config,
    load_settings,
    resolve_project_path,
)
from novaretail.validation.relationship_validator import (
    RelationshipValidationError,
    RelationshipValidationResult,
    validate_default_raw_relationships,
    validate_relationships,
)


@pytest.fixture(scope="module")
def raw_workbook_path() -> Path:
    """Obtiene la ruta del libro RAW generado."""
    settings = load_settings()
    generation_config = load_data_generation_config()

    raw_directory = resolve_project_path(
        settings["paths"]["raw_data"]
    )

    filename = generation_config[
        "output"
    ]["raw_workbook"]

    workbook_path = raw_directory / filename

    assert workbook_path.exists()
    assert workbook_path.is_file()
    assert workbook_path.stat().st_size > 0

    return workbook_path


@pytest.fixture(scope="module")
def valid_result(
    raw_workbook_path: Path,
) -> RelationshipValidationResult:
    """Ejecuta una vez la validación del libro original."""
    return validate_relationships(
        file_path=raw_workbook_path
    )


def _copy_workbook(
    source_path: Path,
    destination_path: Path,
) -> Path:
    """Crea una copia temporal del libro.

    Args:
        source_path: Libro original.
        destination_path: Ruta de destino.

    Returns:
        Ruta del archivo copiado.
    """
    shutil.copy2(
        source_path,
        destination_path,
    )

    return destination_path


def _find_issues(
    result: RelationshipValidationResult,
    relationship_name: str,
) -> list:
    """Busca problemas asociados a una relación.

    Args:
        result: Resultado de validación.
        relationship_name: Relación buscada.

    Returns:
        Lista de problemas coincidentes.
    """
    return [
        issue
        for issue in result.issues
        if (
            issue.relationship_name
            == relationship_name
        )
    ]


def _find_column(
    worksheet,
    column_name: str,
) -> int:
    """Obtiene la posición de una columna.

    Args:
        worksheet: Hoja de Excel.
        column_name: Nombre del encabezado.

    Returns:
        Número de la columna.

    Raises:
        AssertionError: Si la columna no existe.
    """
    headers = {
        cell.value: cell.column
        for cell in worksheet[1]
    }

    assert column_name in headers

    return int(headers[column_name])


def test_relationship_validation_returns_expected_type(
    valid_result: RelationshipValidationResult,
) -> None:
    """Comprueba el tipo del resultado."""
    assert isinstance(
        valid_result,
        RelationshipValidationResult,
    )


def test_current_raw_workbook_passes_relationship_validation(
    valid_result: RelationshipValidationResult,
) -> None:
    """Comprueba la aprobación relacional del libro RAW."""
    assert valid_result.is_valid is True
    assert valid_result.issue_count == 0
    assert valid_result.critical_issue_count == 0
    assert valid_result.high_issue_count == 0
    assert valid_result.affected_record_count == 0


def test_relationship_validator_evaluates_nine_rules(
    valid_result: RelationshipValidationResult,
) -> None:
    """Comprueba la cantidad de relaciones evaluadas."""
    assert len(valid_result.metrics) == 9


def test_expected_relationships_are_present(
    valid_result: RelationshipValidationResult,
) -> None:
    """Comprueba los nombres de las relaciones."""
    expected_relationships = {
        "pedidos_producto",
        "pedidos_cliente",
        "devoluciones_pedido",
        "devoluciones_linea_pedido",
        "inventario_producto",
        "devoluciones_linea_devuelta",
        "atributos_devolucion_pedido",
        "inventario_categoria_producto",
        "atributos_pedido_maestros",
    }

    assert set(
        valid_result.metrics.keys()
    ) == expected_relationships


def test_all_relationship_rules_are_approved(
    valid_result: RelationshipValidationResult,
) -> None:
    """Comprueba que todas las relaciones sean válidas."""
    assert all(
        metric["cumple"] is True
        for metric in valid_result.metrics.values()
    )

    assert all(
        metric["registros_afectados"] == 0
        for metric in valid_result.metrics.values()
    )


def test_orders_reference_existing_products(
    valid_result: RelationshipValidationResult,
) -> None:
    """Comprueba la relación entre pedidos y productos."""
    metric = valid_result.metrics[
        "pedidos_producto"
    ]

    assert metric["registros_hijos"] == 23706
    assert metric["claves_padre_unicas"] == 120
    assert metric["claves_hijas_nulas"] == 0
    assert metric["registros_huerfanos"] == 0
    assert metric["cumple"] is True


def test_orders_reference_existing_customers(
    valid_result: RelationshipValidationResult,
) -> None:
    """Comprueba la relación entre pedidos y clientes."""
    metric = valid_result.metrics[
        "pedidos_cliente"
    ]

    assert metric["registros_hijos"] == 23706
    assert metric["claves_padre_unicas"] == 4000
    assert metric["claves_hijas_nulas"] == 0
    assert metric["registros_huerfanos"] == 0
    assert metric["cumple"] is True


def test_returns_match_returned_order_lines(
    valid_result: RelationshipValidationResult,
) -> None:
    """Comprueba la correspondencia de devoluciones."""
    metric = valid_result.metrics[
        "devoluciones_linea_devuelta"
    ]

    assert (
        metric["lineas_marcadas_devueltas"]
        == 1511
    )

    assert (
        metric["registros_devolucion"]
        == 1511
    )

    assert (
        metric[
            "devoluciones_sin_estado_devuelto"
        ]
        == 0
    )

    assert (
        metric[
            "lineas_devueltas_sin_registro"
        ]
        == 0
    )

    assert metric["cumple"] is True


def test_relationship_result_can_be_converted_to_dataframe(
    valid_result: RelationshipValidationResult,
) -> None:
    """Comprueba la representación tabular."""
    issues_table = valid_result.to_dataframe()

    assert isinstance(
        issues_table,
        pd.DataFrame,
    )

    assert issues_table.columns.tolist() == [
        "relacion",
        "tabla_hija",
        "tabla_padre",
        "clave_hija",
        "clave_padre",
        "severidad",
        "registros_afectados",
        "mensaje",
    ]

    assert issues_table.empty


def test_default_relationship_validator_uses_configured_file(
) -> None:
    """Comprueba el punto de entrada predeterminado."""
    result = validate_default_raw_relationships()

    assert isinstance(
        result,
        RelationshipValidationResult,
    )

    assert result.is_valid is True
    assert result.issue_count == 0
    assert len(result.metrics) == 9


def test_relationship_validator_rejects_missing_file(
    tmp_path: Path,
) -> None:
    """Comprueba el rechazo de un archivo inexistente."""
    missing_file = (
        tmp_path / "archivo_inexistente.xlsx"
    )

    with pytest.raises(
        RelationshipValidationError,
        match="archivo",
    ):
        validate_relationships(
            file_path=missing_file
        )


def test_relationship_validator_rejects_invalid_extension(
    tmp_path: Path,
) -> None:
    """Comprueba el rechazo de una extensión inválida."""
    invalid_file = (
        tmp_path / "datos_relacionales.csv"
    )

    invalid_file.write_text(
        "campo,valor\nprueba,1\n",
        encoding="utf-8",
    )

    with pytest.raises(
        RelationshipValidationError,
        match=r"\.xlsx",
    ):
        validate_relationships(
            file_path=invalid_file
        )


def test_relationship_validator_detects_orphan_product(
    raw_workbook_path: Path,
    tmp_path: Path,
) -> None:
    """Comprueba un pedido asociado a un producto inexistente."""
    modified_path = _copy_workbook(
        source_path=raw_workbook_path,
        destination_path=(
            tmp_path / "pedido_producto_huerfano.xlsx"
        ),
    )

    workbook = load_workbook(modified_path)
    worksheet = workbook["04_Pedidos"]

    column_number = _find_column(
        worksheet=worksheet,
        column_name="producto_id",
    )

    worksheet.cell(
        row=2,
        column=column_number,
    ).value = "PROD-9999"

    workbook.save(modified_path)
    workbook.close()

    result = validate_relationships(
        file_path=modified_path
    )

    issues = _find_issues(
        result=result,
        relationship_name="pedidos_producto",
    )

    metric = result.metrics[
        "pedidos_producto"
    ]

    assert result.is_valid is False
    assert result.critical_issue_count >= 1
    assert len(issues) == 1
    assert issues[0].affected_records == 1
    assert metric["registros_huerfanos"] == 1
    assert metric["cumple"] is False


def test_relationship_validator_detects_orphan_customer(
    raw_workbook_path: Path,
    tmp_path: Path,
) -> None:
    """Comprueba un pedido asociado a un cliente inexistente."""
    modified_path = _copy_workbook(
        source_path=raw_workbook_path,
        destination_path=(
            tmp_path / "pedido_cliente_huerfano.xlsx"
        ),
    )

    workbook = load_workbook(modified_path)
    worksheet = workbook["04_Pedidos"]

    column_number = _find_column(
        worksheet=worksheet,
        column_name="cliente_id",
    )

    worksheet.cell(
        row=2,
        column=column_number,
    ).value = "CLI-99999"

    workbook.save(modified_path)
    workbook.close()

    result = validate_relationships(
        file_path=modified_path
    )

    issues = _find_issues(
        result=result,
        relationship_name="pedidos_cliente",
    )

    metric = result.metrics[
        "pedidos_cliente"
    ]

    assert result.is_valid is False
    assert result.critical_issue_count >= 1
    assert len(issues) == 1
    assert issues[0].affected_records == 1
    assert metric["registros_huerfanos"] == 1
    assert metric["cumple"] is False


def test_relationship_validator_detects_orphan_inventory_product(
    raw_workbook_path: Path,
    tmp_path: Path,
) -> None:
    """Comprueba inventario asociado a un producto inexistente."""
    modified_path = _copy_workbook(
        source_path=raw_workbook_path,
        destination_path=(
            tmp_path / "inventario_producto_huerfano.xlsx"
        ),
    )

    workbook = load_workbook(modified_path)
    worksheet = workbook["05_Inventario"]

    column_number = _find_column(
        worksheet=worksheet,
        column_name="producto_id",
    )

    worksheet.cell(
        row=2,
        column=column_number,
    ).value = "PROD-9999"

    workbook.save(modified_path)
    workbook.close()

    result = validate_relationships(
        file_path=modified_path
    )

    issues = _find_issues(
        result=result,
        relationship_name="inventario_producto",
    )

    assert result.is_valid is False
    assert result.critical_issue_count >= 1
    assert len(issues) == 1
    assert issues[0].affected_records == 1


def test_relationship_validator_detects_return_without_returned_status(
    raw_workbook_path: Path,
    tmp_path: Path,
) -> None:
    """Comprueba una devolución vinculada a una línea no devuelta."""
    modified_path = _copy_workbook(
        source_path=raw_workbook_path,
        destination_path=(
            tmp_path / "devolucion_estado_invalido.xlsx"
        ),
    )

    workbook = load_workbook(modified_path)

    returns_sheet = workbook[
        "06_Devoluciones"
    ]

    orders_sheet = workbook[
        "04_Pedidos"
    ]

    return_line_column = _find_column(
        worksheet=returns_sheet,
        column_name="linea_pedido_id",
    )

    order_line_column = _find_column(
        worksheet=orders_sheet,
        column_name="linea_pedido_id",
    )

    order_status_column = _find_column(
        worksheet=orders_sheet,
        column_name="estado_pedido",
    )

    return_flag_column = _find_column(
        worksheet=orders_sheet,
        column_name="devolucion",
    )

    return_line_id = returns_sheet.cell(
        row=2,
        column=return_line_column,
    ).value

    target_row = None

    for row_number in range(
        2,
        orders_sheet.max_row + 1,
    ):
        if (
            orders_sheet.cell(
                row=row_number,
                column=order_line_column,
            ).value
            == return_line_id
        ):
            target_row = row_number
            break

    assert target_row is not None

    orders_sheet.cell(
        row=target_row,
        column=order_status_column,
    ).value = "Entregado"

    orders_sheet.cell(
        row=target_row,
        column=return_flag_column,
    ).value = False

    workbook.save(modified_path)
    workbook.close()

    result = validate_relationships(
        file_path=modified_path
    )

    issues = _find_issues(
        result=result,
        relationship_name=(
            "devoluciones_linea_devuelta"
        ),
    )

    assert result.is_valid is False
    assert result.critical_issue_count >= 1
    assert len(issues) >= 1

    assert sum(
        issue.affected_records
        for issue in issues
    ) >= 1


def test_relationship_validator_detects_return_attribute_mismatch(
    raw_workbook_path: Path,
    tmp_path: Path,
) -> None:
    """Comprueba atributos incoherentes en una devolución."""
    modified_path = _copy_workbook(
        source_path=raw_workbook_path,
        destination_path=(
            tmp_path / "devolucion_atributo_invalido.xlsx"
        ),
    )

    workbook = load_workbook(modified_path)
    worksheet = workbook["06_Devoluciones"]

    column_number = _find_column(
        worksheet=worksheet,
        column_name="cliente_id",
    )

    worksheet.cell(
        row=2,
        column=column_number,
    ).value = "CLI-99999"

    workbook.save(modified_path)
    workbook.close()

    result = validate_relationships(
        file_path=modified_path
    )

    issues = _find_issues(
        result=result,
        relationship_name=(
            "atributos_devolucion_pedido"
        ),
    )

    assert result.is_valid is False
    assert result.critical_issue_count >= 1
    assert len(issues) == 1
    assert issues[0].affected_records == 1


def test_relationship_validator_detects_inventory_category_mismatch(
    raw_workbook_path: Path,
    tmp_path: Path,
) -> None:
    """Comprueba una categoría de inventario inconsistente."""
    modified_path = _copy_workbook(
        source_path=raw_workbook_path,
        destination_path=(
            tmp_path / "inventario_categoria_invalida.xlsx"
        ),
    )

    workbook = load_workbook(modified_path)
    worksheet = workbook["05_Inventario"]

    category_column = _find_column(
        worksheet=worksheet,
        column_name="categoria",
    )

    original_category = worksheet.cell(
        row=2,
        column=category_column,
    ).value

    replacement_category = (
        "Categoría simulada inválida"
        if original_category
        != "Categoría simulada inválida"
        else "Otra categoría inválida"
    )

    worksheet.cell(
        row=2,
        column=category_column,
    ).value = replacement_category

    workbook.save(modified_path)
    workbook.close()

    result = validate_relationships(
        file_path=modified_path
    )

    issues = _find_issues(
        result=result,
        relationship_name=(
            "inventario_categoria_producto"
        ),
    )

    assert result.is_valid is False
    assert result.high_issue_count >= 1
    assert len(issues) == 1
    assert issues[0].affected_records == 1


def test_relationship_validator_detects_order_master_mismatch(
    raw_workbook_path: Path,
    tmp_path: Path,
) -> None:
    """Comprueba un atributo de pedido diferente del maestro."""
    modified_path = _copy_workbook(
        source_path=raw_workbook_path,
        destination_path=(
            tmp_path / "pedido_atributo_invalido.xlsx"
        ),
    )

    workbook = load_workbook(modified_path)
    worksheet = workbook["04_Pedidos"]

    city_column = _find_column(
        worksheet=worksheet,
        column_name="ciudad",
    )

    worksheet.cell(
        row=2,
        column=city_column,
    ).value = "Ciudad simulada inválida"

    workbook.save(modified_path)
    workbook.close()

    result = validate_relationships(
        file_path=modified_path
    )

    issues = _find_issues(
        result=result,
        relationship_name=(
            "atributos_pedido_maestros"
        ),
    )

    assert result.is_valid is False
    assert result.high_issue_count >= 1
    assert len(issues) == 1
    assert issues[0].affected_records == 1


def test_relationship_validator_blocks_structural_errors(
    raw_workbook_path: Path,
    tmp_path: Path,
) -> None:
    """Comprueba el bloqueo por estructura inválida."""
    modified_path = _copy_workbook(
        source_path=raw_workbook_path,
        destination_path=(
            tmp_path / "libro_sin_productos.xlsx"
        ),
    )

    workbook = load_workbook(modified_path)

    del workbook["02_Productos"]

    workbook.save(modified_path)
    workbook.close()

    with pytest.raises(
        RelationshipValidationError,
        match="errores estructurales",
    ):
        validate_relationships(
            file_path=modified_path
        )