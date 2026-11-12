"""Pruebas automáticas del script maestro de validación."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = (
    PROJECT_ROOT
    / "scripts"
    / "validate_data.py"
)


@pytest.fixture(scope="module")
def validate_data_script() -> ModuleType:
    """Carga scripts/validate_data.py como módulo de prueba."""
    module_specification = (
        importlib.util.spec_from_file_location(
            "validate_data_script_test_module",
            SCRIPT_PATH,
        )
    )

    assert module_specification is not None
    assert module_specification.loader is not None

    module = importlib.util.module_from_spec(
        module_specification
    )

    module_specification.loader.exec_module(
        module
    )

    return module


def _empty_issue_table() -> pd.DataFrame:
    """Construye una tabla vacía compatible con los resultados."""
    return pd.DataFrame()


def _approved_schema_result() -> SimpleNamespace:
    """Crea un resultado estructural aprobado."""
    return SimpleNamespace(
        is_valid=True,
        issue_count=0,
        critical_issue_count=0,
        sheet_summary={
            f"Hoja_{number:02d}": {
                "filas": 1,
                "columnas": 1,
            }
            for number in range(1, 13)
        },
        to_dataframe=_empty_issue_table,
    )


def _rejected_schema_result() -> SimpleNamespace:
    """Crea un resultado estructural no aprobado."""
    issues = pd.DataFrame(
        [
            {
                "hoja": "11_Presupuesto",
                "regla": "required_sheet",
                "severidad": "critical",
                "mensaje": "Falta una hoja obligatoria.",
            }
        ]
    )

    return SimpleNamespace(
        is_valid=False,
        issue_count=1,
        critical_issue_count=1,
        sheet_summary={
            "00_Control": {
                "filas": 17,
                "columnas": 2,
            }
        },
        to_dataframe=lambda: issues,
    )


def _approved_quality_result() -> SimpleNamespace:
    """Crea un resultado de calidad aprobado."""
    issues = pd.DataFrame(
        [
            {
                "hoja": "04_Pedidos",
                "regla": "iqr_outlier",
                "severidad": "medium",
                "columna": "valor_neto_cop",
                "registros_afectados": 10,
                "mensaje": "Alerta atípica para revisión.",
            }
        ]
    )

    return SimpleNamespace(
        is_valid=True,
        issue_count=1,
        critical_issue_count=0,
        high_issue_count=0,
        outlier_alert_count=10,
        metrics={
            f"Hoja_{number:02d}": {}
            for number in range(1, 13)
        },
        to_dataframe=lambda: issues,
    )


def _approved_accounting_result() -> SimpleNamespace:
    """Crea un resultado contable aprobado."""
    return SimpleNamespace(
        is_valid=True,
        issue_count=0,
        critical_issue_count=0,
        high_issue_count=0,
        metrics={
            f"regla_{number:02d}": {
                "cumple": True,
            }
            for number in range(1, 16)
        },
        to_dataframe=_empty_issue_table,
    )


def _approved_relationship_result() -> SimpleNamespace:
    """Crea un resultado relacional aprobado."""
    return SimpleNamespace(
        is_valid=True,
        issue_count=0,
        critical_issue_count=0,
        high_issue_count=0,
        affected_record_count=0,
        metrics={
            f"relacion_{number:02d}": {
                "cumple": True,
            }
            for number in range(1, 10)
        },
        to_dataframe=_empty_issue_table,
    )


def _configure_approved_validators(
    monkeypatch: pytest.MonkeyPatch,
    module: ModuleType,
) -> None:
    """Configura las cuatro validaciones como aprobadas."""
    monkeypatch.setattr(
        module,
        "validate_excel_schema",
        lambda file_path: _approved_schema_result(),
    )

    monkeypatch.setattr(
        module,
        "validate_data_quality",
        lambda file_path: _approved_quality_result(),
    )

    monkeypatch.setattr(
        module,
        "validate_accounting",
        lambda file_path: (
            _approved_accounting_result()
        ),
    )

    monkeypatch.setattr(
        module,
        "validate_relationships",
        lambda file_path: (
            _approved_relationship_result()
        ),
    )


def test_script_file_exists() -> None:
    """Comprueba que el script maestro exista."""
    assert SCRIPT_PATH.exists()
    assert SCRIPT_PATH.is_file()
    assert SCRIPT_PATH.stat().st_size > 0


def test_script_exposes_main_function(
    validate_data_script: ModuleType,
) -> None:
    """Comprueba la existencia del punto de entrada."""
    assert callable(
        validate_data_script.main
    )


def test_argument_parser_accepts_file_argument(
    validate_data_script: ModuleType,
) -> None:
    """Comprueba el argumento opcional --file."""
    parser = (
        validate_data_script
        ._build_argument_parser()
    )

    arguments = parser.parse_args(
        [
            "--file",
            "data/raw/prueba.xlsx",
        ]
    )

    assert arguments.file == Path(
        "data/raw/prueba.xlsx"
    )


def test_argument_parser_uses_default_file(
    validate_data_script: ModuleType,
) -> None:
    """Comprueba que --file sea opcional."""
    parser = (
        validate_data_script
        ._build_argument_parser()
    )

    arguments = parser.parse_args([])

    assert arguments.file is None


@pytest.mark.parametrize(
    ("is_valid", "expected_text"),
    [
        (True, "APROBADO"),
        (False, "NO APROBADO"),
    ],
)
def test_format_status(
    validate_data_script: ModuleType,
    is_valid: bool,
    expected_text: str,
) -> None:
    """Comprueba la conversión del estado a texto."""
    assert (
        validate_data_script._format_status(
            is_valid
        )
        == expected_text
    )


def test_resolve_input_path_uses_absolute_path(
    validate_data_script: ModuleType,
    tmp_path: Path,
) -> None:
    """Comprueba una ruta absoluta suministrada."""
    supplied_path = (
        tmp_path / "libro_prueba.xlsx"
    )

    resolved_path = (
        validate_data_script
        ._resolve_input_path(
            supplied_path=supplied_path
        )
    )

    assert resolved_path == (
        supplied_path.resolve()
    )


def test_main_returns_zero_when_all_validations_pass(
    validate_data_script: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Comprueba el código cero con todas las capas aprobadas."""
    input_path = (
        tmp_path / "libro_aprobado.xlsx"
    )

    _configure_approved_validators(
        monkeypatch=monkeypatch,
        module=validate_data_script,
    )

    exit_code = validate_data_script.main(
        [
            "--file",
            str(input_path),
        ]
    )

    captured_output = capsys.readouterr().out

    assert exit_code == 0

    assert (
        "Estructura: APROBADO"
        in captured_output
    )

    assert (
        "Calidad: APROBADO"
        in captured_output
    )

    assert (
        "Contabilidad: APROBADO"
        in captured_output
    )

    assert (
        "Relaciones: APROBADO"
        in captured_output
    )

    assert (
        "Resultado general: APROBADO"
        in captured_output
    )


def test_main_stops_after_structural_rejection(
    validate_data_script: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Comprueba el bloqueo ante un error estructural."""
    input_path = (
        tmp_path / "libro_invalido.xlsx"
    )

    monkeypatch.setattr(
        validate_data_script,
        "validate_excel_schema",
        lambda file_path: (
            _rejected_schema_result()
        ),
    )

    def unexpected_validation(
        file_path: Path,
    ) -> None:
        raise AssertionError(
            "No debía ejecutarse esta validación."
        )

    monkeypatch.setattr(
        validate_data_script,
        "validate_data_quality",
        unexpected_validation,
    )

    monkeypatch.setattr(
        validate_data_script,
        "validate_accounting",
        unexpected_validation,
    )

    monkeypatch.setattr(
        validate_data_script,
        "validate_relationships",
        unexpected_validation,
    )

    exit_code = validate_data_script.main(
        [
            "--file",
            str(input_path),
        ]
    )

    captured_output = capsys.readouterr().out

    assert exit_code == 1

    assert (
        "Estado: NO APROBADO"
        in captured_output
    )

    assert (
        "Las demás validaciones no se ejecutarán"
        in captured_output
    )


def test_main_returns_two_when_validator_raises_error(
    validate_data_script: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Comprueba el código dos ante un error operativo."""
    input_path = (
        tmp_path / "archivo_inexistente.xlsx"
    )

    def raise_schema_error(
        file_path: Path,
    ) -> None:
        raise (
            validate_data_script
            .SchemaValidationError(
                "No se encontró el archivo."
            )
        )

    monkeypatch.setattr(
        validate_data_script,
        "validate_excel_schema",
        raise_schema_error,
    )

    exit_code = validate_data_script.main(
        [
            "--file",
            str(input_path),
        ]
    )

    captured_output = capsys.readouterr().out

    assert exit_code == 2

    assert (
        "ERROR DE VALIDACIÓN"
        in captured_output
    )

    assert (
        "No se encontró el archivo"
        in captured_output
    )


def test_main_returns_one_when_quality_is_not_approved(
    validate_data_script: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Comprueba un resultado general no aprobado."""
    input_path = (
        tmp_path / "libro_calidad_invalida.xlsx"
    )

    rejected_quality = (
        _approved_quality_result()
    )

    rejected_quality.is_valid = False
    rejected_quality.high_issue_count = 1

    monkeypatch.setattr(
        validate_data_script,
        "validate_excel_schema",
        lambda file_path: (
            _approved_schema_result()
        ),
    )

    monkeypatch.setattr(
        validate_data_script,
        "validate_data_quality",
        lambda file_path: rejected_quality,
    )

    monkeypatch.setattr(
        validate_data_script,
        "validate_accounting",
        lambda file_path: (
            _approved_accounting_result()
        ),
    )

    monkeypatch.setattr(
        validate_data_script,
        "validate_relationships",
        lambda file_path: (
            _approved_relationship_result()
        ),
    )

    exit_code = validate_data_script.main(
        [
            "--file",
            str(input_path),
        ]
    )

    captured_output = capsys.readouterr().out

    assert exit_code == 1

    assert (
        "Calidad: NO APROBADO"
        in captured_output
    )

    assert (
        "Resultado general: NO APROBADO"
        in captured_output
    )


def test_main_passes_same_file_to_all_validators(
    validate_data_script: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Comprueba que las capas reciban el mismo archivo."""
    input_path = (
        tmp_path / "libro_compartido.xlsx"
    ).resolve()

    received_paths: list[Path] = []

    def record_schema(
        file_path: Path,
    ) -> SimpleNamespace:
        received_paths.append(
            Path(file_path)
        )

        return _approved_schema_result()

    def record_quality(
        file_path: Path,
    ) -> SimpleNamespace:
        received_paths.append(
            Path(file_path)
        )

        return _approved_quality_result()

    def record_accounting(
        file_path: Path,
    ) -> SimpleNamespace:
        received_paths.append(
            Path(file_path)
        )

        return _approved_accounting_result()

    def record_relationships(
        file_path: Path,
    ) -> SimpleNamespace:
        received_paths.append(
            Path(file_path)
        )

        return _approved_relationship_result()

    monkeypatch.setattr(
        validate_data_script,
        "validate_excel_schema",
        record_schema,
    )

    monkeypatch.setattr(
        validate_data_script,
        "validate_data_quality",
        record_quality,
    )

    monkeypatch.setattr(
        validate_data_script,
        "validate_accounting",
        record_accounting,
    )

    monkeypatch.setattr(
        validate_data_script,
        "validate_relationships",
        record_relationships,
    )

    exit_code = validate_data_script.main(
        [
            "--file",
            str(input_path),
        ]
    )

    assert exit_code == 0
    assert len(received_paths) == 4

    assert all(
        received_path == input_path
        for received_path in received_paths
    )