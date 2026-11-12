"""Pruebas automáticas del validador de calidad de datos."""

from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd
import pytest
from openpyxl import load_workbook

from novaretail.config import (
    clear_configuration_cache,
    load_data_generation_config,
    load_settings,
    resolve_project_path,
)
from novaretail.generation.generator import TABLE_ORDER
from novaretail.validation.quality_validator import (
    QualityValidationError,
    QualityValidationResult,
    validate_data_quality,
    validate_default_raw_quality,
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
) -> QualityValidationResult:
    """Valida una sola vez el libro RAW original."""
    clear_configuration_cache()

    return validate_data_quality(
        file_path=raw_workbook_path
    )


def _copy_workbook(
    source_path: Path,
    destination_path: Path,
) -> Path:
    """Copia un libro para realizar pruebas controladas."""
    shutil.copy2(
        source_path,
        destination_path,
    )

    return destination_path


def _find_issues(
    result: QualityValidationResult,
    rule: str,
    sheet_name: str | None = None,
    column_name: str | None = None,
) -> list:
    """Busca problemas por regla, hoja y columna."""
    return [
        issue
        for issue in result.issues
        if issue.rule == rule
        and (
            sheet_name is None
            or issue.sheet_name == sheet_name
        )
        and (
            column_name is None
            or issue.column_name == column_name
        )
    ]


def test_quality_validation_returns_expected_type(
    valid_result: QualityValidationResult,
) -> None:
    """Comprueba el tipo del resultado."""
    assert isinstance(
        valid_result,
        QualityValidationResult,
    )


def test_current_raw_workbook_passes_quality_validation(
    valid_result: QualityValidationResult,
) -> None:
    """Comprueba la aprobación del libro RAW original."""
    assert valid_result.is_valid is True
    assert valid_result.critical_issue_count == 0
    assert valid_result.high_issue_count == 0


def test_quality_validation_reviews_all_sheets(
    valid_result: QualityValidationResult,
) -> None:
    """Comprueba que se revisen las doce hojas."""
    assert list(
        valid_result.metrics.keys()
    ) == TABLE_ORDER

    assert len(valid_result.metrics) == 12


def test_order_quality_metrics_are_clean(
    valid_result: QualityValidationResult,
) -> None:
    """Comprueba las métricas principales de pedidos."""
    order_metrics = valid_result.metrics[
        "04_Pedidos"
    ]

    assert order_metrics["filas"] == 23706
    assert order_metrics["columnas"] == 25
    assert order_metrics["valores_nulos"] == 0
    assert order_metrics["filas_duplicadas"] == 0
    assert order_metrics["fechas_invalidas"] == 0
    assert order_metrics["valores_fuera_rango"] == 0


def test_cancelled_orders_with_zero_delivery_days_are_valid(
    valid_result: QualityValidationResult,
) -> None:
    """Comprueba que cero días sea válido para cancelaciones."""
    issues = _find_issues(
        result=valid_result,
        rule="numeric_range",
        sheet_name="04_Pedidos",
        column_name="dias_entrega",
    )

    assert issues == []


def test_product_margins_use_correct_range(
    valid_result: QualityValidationResult,
) -> None:
    """Comprueba el rango válido del margen objetivo."""
    issues = _find_issues(
        result=valid_result,
        rule="numeric_range",
        sheet_name="02_Productos",
        column_name="margen_objetivo",
    )

    assert issues == []


def test_outliers_are_non_blocking_alerts(
    valid_result: QualityValidationResult,
) -> None:
    """Comprueba que los atípicos no invaliden el libro."""
    outlier_issues = _find_issues(
        result=valid_result,
        rule="iqr_outlier",
    )

    assert len(outlier_issues) > 0
    assert valid_result.outlier_alert_count > 0

    assert all(
        issue.severity == "medium"
        for issue in outlier_issues
    )

    assert valid_result.is_valid is True


def test_quality_result_can_be_converted_to_dataframe(
    valid_result: QualityValidationResult,
) -> None:
    """Comprueba la tabla de problemas y alertas."""
    issues_table = valid_result.to_dataframe()

    assert isinstance(
        issues_table,
        pd.DataFrame,
    )

    assert issues_table.columns.tolist() == [
        "hoja",
        "regla",
        "severidad",
        "columna",
        "registros_afectados",
        "mensaje",
    ]

    assert not issues_table.empty


def test_default_quality_validator_uses_configured_file() -> None:
    """Comprueba el punto de entrada predeterminado."""
    clear_configuration_cache()

    result = validate_default_raw_quality()

    assert isinstance(
        result,
        QualityValidationResult,
    )

    assert result.is_valid is True
    assert result.critical_issue_count == 0
    assert result.high_issue_count == 0


def test_quality_validator_rejects_missing_file(
    tmp_path: Path,
) -> None:
    """Comprueba el rechazo de un archivo inexistente."""
    missing_file = (
        tmp_path / "archivo_inexistente.xlsx"
    )

    with pytest.raises(
        QualityValidationError,
        match="archivo",
    ):
        validate_data_quality(
            file_path=missing_file
        )


def test_quality_validator_rejects_invalid_extension(
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
        QualityValidationError,
        match=r"\.xlsx",
    ):
        validate_data_quality(
            file_path=invalid_file
        )


def test_quality_validator_detects_invalid_quantity(
    raw_workbook_path: Path,
    tmp_path: Path,
) -> None:
    """Comprueba la detección de unidades inválidas."""
    modified_path = _copy_workbook(
        source_path=raw_workbook_path,
        destination_path=(
            tmp_path / "libro_cantidad_invalida.xlsx"
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
        column=headers["unidades"],
    ).value = 0

    workbook.save(modified_path)
    workbook.close()

    result = validate_data_quality(
        file_path=modified_path
    )

    issues = _find_issues(
        result=result,
        rule="numeric_range",
        sheet_name="04_Pedidos",
        column_name="unidades",
    )

    assert result.is_valid is False
    assert result.high_issue_count >= 1
    assert len(issues) == 1
    assert issues[0].affected_records == 1


def test_quality_validator_detects_discount_outside_range(
    raw_workbook_path: Path,
    tmp_path: Path,
) -> None:
    """Comprueba un descuento superior al máximo."""
    modified_path = _copy_workbook(
        source_path=raw_workbook_path,
        destination_path=(
            tmp_path / "libro_descuento_invalido.xlsx"
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
        column=headers["descuento_rate"],
    ).value = 0.50

    workbook.save(modified_path)
    workbook.close()

    result = validate_data_quality(
        file_path=modified_path
    )

    issues = _find_issues(
        result=result,
        rule="numeric_range",
        sheet_name="04_Pedidos",
        column_name="descuento_rate",
    )

    assert result.is_valid is False
    assert result.high_issue_count >= 1
    assert len(issues) == 1


def test_quality_validator_detects_invalid_date(
    raw_workbook_path: Path,
    tmp_path: Path,
) -> None:
    """Comprueba una fecha no interpretable."""
    modified_path = _copy_workbook(
        source_path=raw_workbook_path,
        destination_path=(
            tmp_path / "libro_fecha_invalida.xlsx"
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
        column=headers["fecha_registro"],
    ).value = "fecha-invalida"

    workbook.save(modified_path)
    workbook.close()

    result = validate_data_quality(
        file_path=modified_path
    )

    issues = _find_issues(
        result=result,
        rule="invalid_date",
        sheet_name="03_Clientes",
        column_name="fecha_registro",
    )

    assert result.is_valid is False
    assert result.high_issue_count >= 1
    assert len(issues) == 1


def test_quality_validator_detects_date_outside_period(
    raw_workbook_path: Path,
    tmp_path: Path,
) -> None:
    """Comprueba una fecha anterior al periodo permitido."""
    modified_path = _copy_workbook(
        source_path=raw_workbook_path,
        destination_path=(
            tmp_path / "libro_fecha_fuera_periodo.xlsx"
        ),
    )

    workbook = load_workbook(modified_path)
    worksheet = workbook["02_Productos"]

    headers = {
        cell.value: cell.column
        for cell in worksheet[1]
    }

    worksheet.cell(
        row=2,
        column=headers["fecha_ingreso"],
    ).value = "2022-12-31"

    workbook.save(modified_path)
    workbook.close()

    result = validate_data_quality(
        file_path=modified_path
    )

    issues = _find_issues(
        result=result,
        rule="date_outside_period",
        sheet_name="02_Productos",
        column_name="fecha_ingreso",
    )

    assert result.is_valid is False
    assert result.high_issue_count >= 1
    assert len(issues) == 1


def test_quality_validator_detects_complete_duplicate(
    raw_workbook_path: Path,
    tmp_path: Path,
) -> None:
    """Comprueba la detección de filas completamente duplicadas."""
    modified_path = _copy_workbook(
        source_path=raw_workbook_path,
        destination_path=(
            tmp_path / "libro_duplicado_completo.xlsx"
        ),
    )

    workbook = load_workbook(modified_path)
    worksheet = workbook["00_Control"]

    source_row = [
        worksheet.cell(
            row=2,
            column=column_number,
        ).value
        for column_number in range(
            1,
            worksheet.max_column + 1,
        )
    ]

    new_row_number = worksheet.max_row + 1

    for column_number, value in enumerate(
        source_row,
        start=1,
    ):
        worksheet.cell(
            row=new_row_number,
            column=column_number,
        ).value = value

    workbook.save(modified_path)
    workbook.close()

    result = validate_data_quality(
        file_path=modified_path
    )

    issues = _find_issues(
        result=result,
        rule="complete_duplicate",
        sheet_name="00_Control",
    )

    assert result.is_valid is False
    assert result.high_issue_count >= 1
    assert len(issues) == 1
    assert issues[0].affected_records == 2


def test_quality_validator_blocks_structural_errors(
    raw_workbook_path: Path,
    tmp_path: Path,
) -> None:
    """Comprueba el bloqueo por errores estructurales."""
    modified_path = _copy_workbook(
        source_path=raw_workbook_path,
        destination_path=(
            tmp_path / "libro_sin_hoja.xlsx"
        ),
    )

    workbook = load_workbook(modified_path)

    del workbook["07_Marketing"]

    workbook.save(modified_path)
    workbook.close()

    with pytest.raises(
        QualityValidationError,
        match="errores estructurales",
    ):
        validate_data_quality(
            file_path=modified_path
        )
