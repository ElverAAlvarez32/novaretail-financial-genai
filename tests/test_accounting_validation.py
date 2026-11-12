"""Pruebas automáticas del validador contable de NovaRetail."""

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
from novaretail.validation.accounting_validator import (
    AccountingValidationError,
    AccountingValidationResult,
    validate_accounting,
    validate_default_raw_accounting,
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
) -> AccountingValidationResult:
    """Ejecuta una vez la validación contable original."""
    return validate_accounting(
        file_path=raw_workbook_path
    )


def _copy_workbook(
    source_path: Path,
    destination_path: Path,
) -> Path:
    """Crea una copia temporal del libro.

    Args:
        source_path: Libro original.
        destination_path: Ruta de la copia.

    Returns:
        Ruta del archivo copiado.
    """
    shutil.copy2(
        source_path,
        destination_path,
    )

    return destination_path


def _find_issues(
    result: AccountingValidationResult,
    rule: str,
) -> list:
    """Busca problemas asociados a una regla.

    Args:
        result: Resultado de validación contable.
        rule: Regla contable buscada.

    Returns:
        Problemas coincidentes.
    """
    return [
        issue
        for issue in result.issues
        if issue.rule == rule
    ]


def _find_column(
    worksheet,
    column_name: str,
) -> int:
    """Obtiene la posición de una columna de Excel.

    Args:
        worksheet: Hoja de Excel.
        column_name: Nombre del encabezado.

    Returns:
        Número de columna.

    Raises:
        AssertionError: Si el encabezado no existe.
    """
    headers = {
        cell.value: cell.column
        for cell in worksheet[1]
    }

    assert column_name in headers

    return int(headers[column_name])


def test_accounting_validation_returns_expected_type(
    valid_result: AccountingValidationResult,
) -> None:
    """Comprueba el tipo del resultado."""
    assert isinstance(
        valid_result,
        AccountingValidationResult,
    )


def test_current_raw_workbook_passes_accounting_validation(
    valid_result: AccountingValidationResult,
) -> None:
    """Comprueba la aprobación contable del libro RAW."""
    assert valid_result.is_valid is True
    assert valid_result.issue_count == 0
    assert valid_result.critical_issue_count == 0
    assert valid_result.high_issue_count == 0


def test_accounting_validation_evaluates_fifteen_rules(
    valid_result: AccountingValidationResult,
) -> None:
    """Comprueba la cantidad de reglas evaluadas."""
    assert len(valid_result.metrics) == 15


def test_all_accounting_rules_are_approved(
    valid_result: AccountingValidationResult,
) -> None:
    """Comprueba que todas las reglas estén conciliadas."""
    assert all(
        metric["cumple"] is True
        for metric in valid_result.metrics.values()
    )

    assert all(
        metric["registros_afectados"] == 0
        for metric in valid_result.metrics.values()
    )

    assert all(
        metric["diferencia_maxima"] == 0.0
        for metric in valid_result.metrics.values()
    )


def test_expected_accounting_rules_are_present(
    valid_result: AccountingValidationResult,
) -> None:
    """Comprueba los nombres de las reglas contables."""
    expected_rules = {
        "net_revenue",
        "gross_profit",
        "operating_profit",
        "profit_before_tax",
        "net_profit",
        "balance_equation",
        "recorded_balance_difference",
        "net_cash_change",
        "cash_reconciliation",
        "cash_continuity",
        "inventory_reconciliation",
        "inventory_value",
        "cash_between_statements",
        "profit_income_vs_balance",
        "profit_income_vs_cash_flow",
    }

    assert set(
        valid_result.metrics.keys()
    ) == expected_rules


def test_balance_equation_reviews_all_periods(
    valid_result: AccountingValidationResult,
) -> None:
    """Comprueba la cobertura del balance general."""
    metric = valid_result.metrics[
        "balance_equation"
    ]

    assert metric["registros_evaluados"] == 36
    assert metric["registros_afectados"] == 0
    assert metric["diferencia_maxima"] == 0.0
    assert metric["tolerancia"] == 1.0
    assert metric["cumple"] is True


def test_cash_reconciliation_reviews_all_periods(
    valid_result: AccountingValidationResult,
) -> None:
    """Comprueba la cobertura del flujo de efectivo."""
    metric = valid_result.metrics[
        "cash_reconciliation"
    ]

    assert metric["registros_evaluados"] == 36
    assert metric["registros_afectados"] == 0
    assert metric["diferencia_maxima"] == 0.0
    assert metric["cumple"] is True


def test_inventory_reconciliation_reviews_all_records(
    valid_result: AccountingValidationResult,
) -> None:
    """Comprueba la cobertura del inventario."""
    metric = valid_result.metrics[
        "inventory_reconciliation"
    ]

    assert metric["registros_evaluados"] == 3712
    assert metric["registros_afectados"] == 0
    assert metric["diferencia_maxima"] == 0.0
    assert metric["tolerancia"] == 0.0
    assert metric["cumple"] is True


def test_accounting_result_can_be_converted_to_dataframe(
    valid_result: AccountingValidationResult,
) -> None:
    """Comprueba la representación tabular de problemas."""
    issues_table = valid_result.to_dataframe()

    assert isinstance(
        issues_table,
        pd.DataFrame,
    )

    assert issues_table.columns.tolist() == [
        "hoja",
        "regla",
        "severidad",
        "registros_afectados",
        "diferencia_maxima",
        "mensaje",
    ]

    assert issues_table.empty


def test_default_accounting_validator_uses_configured_file() -> None:
    """Comprueba el punto de entrada predeterminado."""
    result = validate_default_raw_accounting()

    assert isinstance(
        result,
        AccountingValidationResult,
    )

    assert result.is_valid is True
    assert result.issue_count == 0
    assert len(result.metrics) == 15


def test_accounting_validator_rejects_missing_file(
    tmp_path: Path,
) -> None:
    """Comprueba el rechazo de un archivo inexistente."""
    missing_file = (
        tmp_path / "archivo_inexistente.xlsx"
    )

    with pytest.raises(
        AccountingValidationError,
        match="archivo",
    ):
        validate_accounting(
            file_path=missing_file
        )


def test_accounting_validator_rejects_invalid_extension(
    tmp_path: Path,
) -> None:
    """Comprueba el rechazo de una extensión inválida."""
    invalid_file = (
        tmp_path / "datos_financieros.csv"
    )

    invalid_file.write_text(
        "periodo,valor\n2023-01,1\n",
        encoding="utf-8",
    )

    with pytest.raises(
        AccountingValidationError,
        match=r"\.xlsx",
    ):
        validate_accounting(
            file_path=invalid_file
        )


def test_accounting_validator_detects_net_revenue_difference(
    raw_workbook_path: Path,
    tmp_path: Path,
) -> None:
    """Comprueba una diferencia en ingresos netos."""
    modified_path = _copy_workbook(
        source_path=raw_workbook_path,
        destination_path=(
            tmp_path / "ingresos_netos_incorrectos.xlsx"
        ),
    )

    workbook = load_workbook(modified_path)

    worksheet = workbook[
        "08_Estado_Resultados"
    ]

    column_number = _find_column(
        worksheet=worksheet,
        column_name="ingresos_netos_cop",
    )

    original_value = worksheet.cell(
        row=2,
        column=column_number,
    ).value

    worksheet.cell(
        row=2,
        column=column_number,
    ).value = int(original_value) + 1000

    workbook.save(modified_path)
    workbook.close()

    result = validate_accounting(
        file_path=modified_path
    )

    issues = _find_issues(
        result=result,
        rule="net_revenue",
    )

    assert result.is_valid is False
    assert result.critical_issue_count >= 1
    assert len(issues) == 1
    assert issues[0].affected_records == 1
    assert issues[0].maximum_difference == 1000.0


def test_accounting_validator_detects_balance_difference(
    raw_workbook_path: Path,
    tmp_path: Path,
) -> None:
    """Comprueba una diferencia en la ecuación contable."""
    modified_path = _copy_workbook(
        source_path=raw_workbook_path,
        destination_path=(
            tmp_path / "balance_incorrecto.xlsx"
        ),
    )

    workbook = load_workbook(modified_path)

    worksheet = workbook[
        "09_Balance_General"
    ]

    column_number = _find_column(
        worksheet=worksheet,
        column_name=(
            "total_pasivo_patrimonio_cop"
        ),
    )

    original_value = worksheet.cell(
        row=2,
        column=column_number,
    ).value

    worksheet.cell(
        row=2,
        column=column_number,
    ).value = int(original_value) + 5000

    workbook.save(modified_path)
    workbook.close()

    result = validate_accounting(
        file_path=modified_path
    )

    issues = _find_issues(
        result=result,
        rule="balance_equation",
    )

    assert result.is_valid is False
    assert result.critical_issue_count >= 1
    assert len(issues) == 1
    assert issues[0].affected_records == 1
    assert issues[0].maximum_difference == 5000.0


def test_accounting_validator_detects_cash_reconciliation_error(
    raw_workbook_path: Path,
    tmp_path: Path,
) -> None:
    """Comprueba una diferencia en el efectivo final."""
    modified_path = _copy_workbook(
        source_path=raw_workbook_path,
        destination_path=(
            tmp_path / "flujo_incorrecto.xlsx"
        ),
    )

    workbook = load_workbook(modified_path)

    worksheet = workbook[
        "10_Flujo_Efectivo"
    ]

    column_number = _find_column(
        worksheet=worksheet,
        column_name="efectivo_final_cop",
    )

    original_value = worksheet.cell(
        row=2,
        column=column_number,
    ).value

    worksheet.cell(
        row=2,
        column=column_number,
    ).value = int(original_value) + 2500

    workbook.save(modified_path)
    workbook.close()

    result = validate_accounting(
        file_path=modified_path
    )

    reconciliation_issues = _find_issues(
        result=result,
        rule="cash_reconciliation",
    )

    statement_issues = _find_issues(
        result=result,
        rule="cash_between_statements",
    )

    assert result.is_valid is False
    assert result.critical_issue_count >= 2
    assert len(reconciliation_issues) == 1
    assert len(statement_issues) == 1

    assert (
        reconciliation_issues[0].affected_records
        == 1
    )

    assert (
        reconciliation_issues[0].maximum_difference
        == 2500.0
    )


def test_accounting_validator_detects_inventory_difference(
    raw_workbook_path: Path,
    tmp_path: Path,
) -> None:
    """Comprueba una diferencia en unidades de inventario."""
    modified_path = _copy_workbook(
        source_path=raw_workbook_path,
        destination_path=(
            tmp_path / "inventario_incorrecto.xlsx"
        ),
    )

    workbook = load_workbook(modified_path)

    worksheet = workbook[
        "05_Inventario"
    ]

    column_number = _find_column(
        worksheet=worksheet,
        column_name=(
            "inventario_final_unidades"
        ),
    )

    original_value = worksheet.cell(
        row=2,
        column=column_number,
    ).value

    worksheet.cell(
        row=2,
        column=column_number,
    ).value = int(original_value) + 3

    workbook.save(modified_path)
    workbook.close()

    result = validate_accounting(
        file_path=modified_path
    )

    reconciliation_issues = _find_issues(
        result=result,
        rule="inventory_reconciliation",
    )

    value_issues = _find_issues(
        result=result,
        rule="inventory_value",
    )

    assert result.is_valid is False
    assert result.critical_issue_count >= 2
    assert len(reconciliation_issues) == 1
    assert len(value_issues) == 1

    assert (
        reconciliation_issues[0].affected_records
        == 1
    )

    assert (
        reconciliation_issues[0].maximum_difference
        == 3.0
    )


def test_accounting_validator_detects_profit_between_statements(
    raw_workbook_path: Path,
    tmp_path: Path,
) -> None:
    """Comprueba una diferencia de utilidad entre estados."""
    modified_path = _copy_workbook(
        source_path=raw_workbook_path,
        destination_path=(
            tmp_path / "utilidad_balance_incorrecta.xlsx"
        ),
    )

    workbook = load_workbook(modified_path)

    worksheet = workbook[
        "09_Balance_General"
    ]

    column_number = _find_column(
        worksheet=worksheet,
        column_name="resultado_periodo_cop",
    )

    original_value = worksheet.cell(
        row=2,
        column=column_number,
    ).value

    worksheet.cell(
        row=2,
        column=column_number,
    ).value = int(original_value) + 7000

    workbook.save(modified_path)
    workbook.close()

    result = validate_accounting(
        file_path=modified_path
    )

    issues = _find_issues(
        result=result,
        rule="profit_income_vs_balance",
    )

    assert result.is_valid is False
    assert result.critical_issue_count >= 1
    assert len(issues) == 1
    assert issues[0].affected_records == 1
    assert issues[0].maximum_difference == 7000.0


def test_accounting_validator_blocks_structural_errors(
    raw_workbook_path: Path,
    tmp_path: Path,
) -> None:
    """Comprueba el bloqueo por estructura inválida."""
    modified_path = _copy_workbook(
        source_path=raw_workbook_path,
        destination_path=(
            tmp_path / "libro_sin_balance.xlsx"
        ),
    )

    workbook = load_workbook(modified_path)

    del workbook["09_Balance_General"]

    workbook.save(modified_path)
    workbook.close()

    with pytest.raises(
        AccountingValidationError,
        match="errores estructurales",
    ):
        validate_accounting(
            file_path=modified_path
        )