"""Pruebas automáticas del validador estructural de Excel."""

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
from novaretail.generation.generator import TABLE_ORDER
from novaretail.validation.schema_validator import (
    EXPECTED_COLUMNS,
    SchemaValidationError,
    SchemaValidationResult,
    validate_default_raw_workbook,
    validate_excel_schema,
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
) -> SchemaValidationResult:
    """Valida una sola vez el libro RAW original."""
    return validate_excel_schema(
        file_path=raw_workbook_path
    )


def _copy_workbook(
    source_path: Path,
    destination_path: Path,
) -> Path:
    """Copia el libro original en una ubicación temporal."""
    shutil.copy2(
        source_path,
        destination_path,
    )

    return destination_path


def _find_issues(
    result: SchemaValidationResult,
    rule: str,
    sheet_name: str | None = None,
) -> list:
    """Busca problemas por regla y hoja."""
    return [
        issue
        for issue in result.issues
        if issue.rule == rule
        and (
            sheet_name is None
            or issue.sheet_name == sheet_name
        )
    ]


def test_validation_returns_expected_type(
    valid_result: SchemaValidationResult,
) -> None:
    """Comprueba el tipo del resultado."""
    assert isinstance(
        valid_result,
        SchemaValidationResult,
    )


def test_valid_workbook_is_approved(
    valid_result: SchemaValidationResult,
) -> None:
    """Comprueba que el libro RAW sea aprobado."""
    assert valid_result.is_valid is True
    assert valid_result.issue_count == 0
    assert valid_result.critical_issue_count == 0


def test_all_expected_sheets_are_reviewed(
    valid_result: SchemaValidationResult,
) -> None:
    """Comprueba que se revisen las doce hojas."""
    assert list(
        valid_result.sheet_summary.keys()
    ) == TABLE_ORDER

    assert len(
        valid_result.sheet_summary
    ) == 12


def test_sheet_summary_matches_known_dimensions(
    valid_result: SchemaValidationResult,
) -> None:
    """Comprueba dimensiones representativas."""
    assert valid_result.sheet_summary[
        "00_Control"
    ] == {
        "filas": 17,
        "columnas": 2,
    }

    assert valid_result.sheet_summary[
        "04_Pedidos"
    ] == {
        "filas": 23706,
        "columnas": 25,
    }

    assert valid_result.sheet_summary[
        "09_Balance_General"
    ] == {
        "filas": 36,
        "columnas": 30,
    }


def test_expected_columns_cover_all_sheets() -> None:
    """Comprueba el contrato de columnas."""
    assert list(
        EXPECTED_COLUMNS.keys()
    ) == TABLE_ORDER

    for sheet_name in TABLE_ORDER:
        assert EXPECTED_COLUMNS[sheet_name]


def test_result_can_be_converted_to_dataframe(
    valid_result: SchemaValidationResult,
) -> None:
    """Comprueba la salida tabular de problemas."""
    issues_table = valid_result.to_dataframe()

    assert isinstance(
        issues_table,
        pd.DataFrame,
    )

    assert issues_table.columns.tolist() == [
        "hoja",
        "regla",
        "severidad",
        "mensaje",
    ]

    assert issues_table.empty


def test_default_validator_uses_configured_file() -> None:
    """Comprueba la validación del archivo configurado."""
    result = validate_default_raw_workbook()

    assert isinstance(
        result,
        SchemaValidationResult,
    )

    assert result.is_valid is True
    assert result.issue_count == 0


def test_validator_rejects_missing_file(
    tmp_path: Path,
) -> None:
    """Comprueba el rechazo de una ruta inexistente."""
    missing_file = (
        tmp_path / "archivo_inexistente.xlsx"
    )

    with pytest.raises(
        SchemaValidationError,
        match="No se encontró el archivo",
    ):
        validate_excel_schema(
            file_path=missing_file
        )


def test_validator_rejects_invalid_extension(
    tmp_path: Path,
) -> None:
    """Comprueba el rechazo de una extensión inválida."""
    invalid_file = (
        tmp_path / "datos_novaretail.csv"
    )

    invalid_file.write_text(
        "campo,valor\nprueba,1\n",
        encoding="utf-8",
    )

    with pytest.raises(
        SchemaValidationError,
        match="extensión .xlsx",
    ):
        validate_excel_schema(
            file_path=invalid_file
        )


def test_validator_detects_missing_sheet(
    raw_workbook_path: Path,
    tmp_path: Path,
) -> None:
    """Comprueba una hoja obligatoria ausente."""
    modified_path = _copy_workbook(
        source_path=raw_workbook_path,
        destination_path=(
            tmp_path / "libro_sin_presupuesto.xlsx"
        ),
    )

    workbook = load_workbook(modified_path)

    del workbook["11_Presupuesto"]

    workbook.save(modified_path)
    workbook.close()

    result = validate_excel_schema(
        file_path=modified_path
    )

    issues = _find_issues(
        result=result,
        rule="required_sheet",
        sheet_name="11_Presupuesto",
    )

    assert result.is_valid is False
    assert result.critical_issue_count >= 1
    assert len(issues) == 1


def test_validator_detects_unexpected_sheet(
    raw_workbook_path: Path,
    tmp_path: Path,
) -> None:
    """Comprueba la detección de una hoja adicional."""
    modified_path = _copy_workbook(
        source_path=raw_workbook_path,
        destination_path=(
            tmp_path / "libro_con_hoja_adicional.xlsx"
        ),
    )

    workbook = load_workbook(modified_path)

    worksheet = workbook.create_sheet(
        "Hoja_No_Autorizada"
    )

    worksheet["A1"] = "campo"
    worksheet["A2"] = "prueba"

    workbook.save(modified_path)
    workbook.close()

    result = validate_excel_schema(
        file_path=modified_path
    )

    issues = _find_issues(
        result=result,
        rule="unexpected_sheet",
        sheet_name="Hoja_No_Autorizada",
    )

    assert len(issues) == 1
    assert issues[0].severity == "medium"
    assert result.critical_issue_count == 0
    assert result.is_valid is True


def test_validator_detects_missing_column(
    raw_workbook_path: Path,
    tmp_path: Path,
) -> None:
    """Comprueba una columna obligatoria ausente."""
    modified_path = _copy_workbook(
        source_path=raw_workbook_path,
        destination_path=(
            tmp_path / "libro_sin_columna.xlsx"
        ),
    )

    workbook = load_workbook(modified_path)
    worksheet = workbook["02_Productos"]

    headers = {
        cell.value: cell.column
        for cell in worksheet[1]
    }

    worksheet.delete_cols(
        headers["producto_id"]
    )

    workbook.save(modified_path)
    workbook.close()

    result = validate_excel_schema(
        file_path=modified_path
    )

    issues = _find_issues(
        result=result,
        rule="required_column",
        sheet_name="02_Productos",
    )

    assert result.is_valid is False
    assert result.critical_issue_count >= 1
    assert len(issues) == 1
    assert "producto_id" in issues[0].message


def test_validator_detects_duplicate_primary_key(
    raw_workbook_path: Path,
    tmp_path: Path,
) -> None:
    """Comprueba una clave primaria duplicada."""
    modified_path = _copy_workbook(
        source_path=raw_workbook_path,
        destination_path=(
            tmp_path / "libro_con_clave_duplicada.xlsx"
        ),
    )

    workbook = load_workbook(modified_path)
    worksheet = workbook["02_Productos"]

    first_product_id = worksheet.cell(
        row=2,
        column=1,
    ).value

    worksheet.cell(
        row=3,
        column=1,
    ).value = first_product_id

    workbook.save(modified_path)
    workbook.close()

    result = validate_excel_schema(
        file_path=modified_path
    )

    issues = _find_issues(
        result=result,
        rule="primary_key_duplicate",
        sheet_name="02_Productos",
    )

    assert result.is_valid is False
    assert result.critical_issue_count >= 1
    assert len(issues) == 1


def test_validator_detects_null_required_value(
    raw_workbook_path: Path,
    tmp_path: Path,
) -> None:
    """Comprueba un campo obligatorio vacío."""
    modified_path = _copy_workbook(
        source_path=raw_workbook_path,
        destination_path=(
            tmp_path / "libro_con_nulo.xlsx"
        ),
    )

    workbook = load_workbook(modified_path)
    worksheet = workbook["03_Clientes"]

    headers = {
        cell.value: cell.column
        for cell in worksheet[1]
    }

    worksheet.cell(
        row=2,
        column=headers["ciudad"],
    ).value = None

    workbook.save(modified_path)
    workbook.close()

    result = validate_excel_schema(
        file_path=modified_path
    )

    issues = _find_issues(
        result=result,
        rule="required_non_null",
        sheet_name="03_Clientes",
    )

    assert result.is_valid is False
    assert result.critical_issue_count >= 1
    assert len(issues) == 1
    assert "ciudad" in issues[0].message


def test_validator_detects_missing_financial_period(
    raw_workbook_path: Path,
    tmp_path: Path,
) -> None:
    """Comprueba un periodo financiero faltante."""
    modified_path = _copy_workbook(
        source_path=raw_workbook_path,
        destination_path=(
            tmp_path / "libro_con_periodo_faltante.xlsx"
        ),
    )

    workbook = load_workbook(modified_path)

    worksheet = workbook[
        "08_Estado_Resultados"
    ]

    worksheet.delete_rows(
        worksheet.max_row,
        1,
    )

    workbook.save(modified_path)
    workbook.close()

    result = validate_excel_schema(
        file_path=modified_path
    )

    period_issues = _find_issues(
        result=result,
        rule="expected_periods",
        sheet_name="08_Estado_Resultados",
    )

    minimum_row_issues = _find_issues(
        result=result,
        rule="minimum_rows",
        sheet_name="08_Estado_Resultados",
    )

    assert result.is_valid is False
    assert len(period_issues) == 1
    assert len(minimum_row_issues) == 1


def test_validator_detects_false_synthetic_flag(
    raw_workbook_path: Path,
    tmp_path: Path,
) -> None:
    """Comprueba la identificación sintética obligatoria."""
    modified_path = _copy_workbook(
        source_path=raw_workbook_path,
        destination_path=(
            tmp_path / "libro_con_bandera_falsa.xlsx"
        ),
    )

    workbook = load_workbook(modified_path)
    worksheet = workbook["04_Pedidos"]

    headers = {
        cell.value: cell.column
        for cell in worksheet[1]
    }

    worksheet.cell(
        row=2,
        column=headers["datos_sinteticos"],
    ).value = False

    workbook.save(modified_path)
    workbook.close()

    result = validate_excel_schema(
        file_path=modified_path
    )

    issues = _find_issues(
        result=result,
        rule="synthetic_flag",
        sheet_name="04_Pedidos",
    )

    assert result.is_valid is False
    assert result.critical_issue_count >= 1
    assert len(issues) == 1


def test_schema_issue_dataframe_contains_detected_problem(
    raw_workbook_path: Path,
    tmp_path: Path,
) -> None:
    """Comprueba la trazabilidad tabular de un problema."""
    modified_path = _copy_workbook(
        source_path=raw_workbook_path,
        destination_path=(
            tmp_path / "libro_para_reporte.xlsx"
        ),
    )

    workbook = load_workbook(modified_path)

    del workbook["07_Marketing"]

    workbook.save(modified_path)
    workbook.close()

    result = validate_excel_schema(
        file_path=modified_path
    )

    issues_table = result.to_dataframe()

    assert not issues_table.empty

    detected_problem = issues_table[
        (issues_table["hoja"] == "07_Marketing")
        & (
            issues_table["regla"]
            == "required_sheet"
        )
        & (
            issues_table["severidad"]
            == "critical"
        )
    ]

    assert len(detected_problem) == 1
    