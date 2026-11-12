"""Punto de entrada para validar el libro RAW de NovaRetail.

Este script ejecuta, en orden, las siguientes validaciones:

1. Validación estructural.
2. Validación de calidad.
3. Validación contable.
4. Validación de relaciones.

El proceso no modifica el libro Excel analizado.

Códigos de salida:
    0: Todas las validaciones fueron aprobadas.
    1: Una o más validaciones no fueron aprobadas.
    2: Ocurrió un error que impidió completar el proceso.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORY = PROJECT_ROOT / "src"

if str(SOURCE_DIRECTORY) not in sys.path:
    sys.path.insert(
        0,
        str(SOURCE_DIRECTORY),
    )


from novaretail.config import (
    load_data_generation_config,
    load_settings,
    resolve_project_path,
)
from novaretail.logging_config import get_logger
from novaretail.validation import (
    AccountingValidationError,
    QualityValidationError,
    RelationshipValidationError,
    SchemaValidationError,
    validate_accounting,
    validate_data_quality,
    validate_excel_schema,
    validate_relationships,
)


LOGGER = get_logger("scripts.validate_data")


def _build_argument_parser() -> argparse.ArgumentParser:
    """Construye el analizador de argumentos del script.

    Returns:
        Analizador configurado.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Valida la estructura, calidad, contabilidad "
            "y relaciones del libro Excel de NovaRetail."
        )
    )

    parser.add_argument(
        "--file",
        type=Path,
        default=None,
        help=(
            "Ruta opcional del archivo XLSX. "
            "Si se omite, se utiliza el libro RAW configurado."
        ),
    )

    return parser


def _resolve_input_path(
    supplied_path: Path | None,
) -> Path:
    """Resuelve la ruta del libro que será validado.

    Args:
        supplied_path: Ruta opcional recibida por línea de comandos.

    Returns:
        Ruta absoluta del archivo Excel.
    """
    if supplied_path is not None:
        if supplied_path.is_absolute():
            return supplied_path.resolve()

        return resolve_project_path(
            str(supplied_path)
        ).resolve()

    settings = load_settings()
    generation_config = load_data_generation_config()

    raw_directory = resolve_project_path(
        settings["paths"]["raw_data"]
    )

    filename = generation_config[
        "output"
    ]["raw_workbook"]

    return (
        raw_directory / filename
    ).resolve()


def _print_section(
    title: str,
) -> None:
    """Imprime un encabezado de sección.

    Args:
        title: Título que será mostrado.
    """
    print()
    print("-" * 70)
    print(title)
    print("-" * 70)


def _format_status(
    is_valid: bool,
) -> str:
    """Convierte un resultado booleano en texto legible.

    Args:
        is_valid: Estado de la validación.

    Returns:
        Texto APROBADO o NO APROBADO.
    """
    return (
        "APROBADO"
        if is_valid
        else "NO APROBADO"
    )


def _print_schema_summary(
    result: Any,
) -> None:
    """Presenta el resumen de validación estructural."""
    _print_section(
        "1. VALIDACIÓN ESTRUCTURAL"
    )

    print(
        f"Estado: {_format_status(result.is_valid)}"
    )
    print(
        f"Hojas revisadas: {len(result.sheet_summary)}"
    )
    print(
        f"Problemas: {result.issue_count}"
    )
    print(
        f"Problemas críticos: "
        f"{result.critical_issue_count}"
    )


def _print_quality_summary(
    result: Any,
) -> None:
    """Presenta el resumen de validación de calidad."""
    _print_section(
        "2. VALIDACIÓN DE CALIDAD"
    )

    print(
        f"Estado: {_format_status(result.is_valid)}"
    )
    print(
        f"Hojas revisadas: {len(result.metrics)}"
    )
    print(
        f"Problemas y alertas: {result.issue_count}"
    )
    print(
        f"Problemas críticos: "
        f"{result.critical_issue_count}"
    )
    print(
        f"Problemas altos: {result.high_issue_count}"
    )
    print(
        f"Registros marcados como atípicos: "
        f"{result.outlier_alert_count}"
    )

    print(
        "Nota: los valores atípicos son alertas de revisión, "
        "no errores confirmados."
    )


def _print_accounting_summary(
    result: Any,
) -> None:
    """Presenta el resumen de validación contable."""
    _print_section(
        "3. VALIDACIÓN CONTABLE"
    )

    print(
        f"Estado: {_format_status(result.is_valid)}"
    )
    print(
        f"Reglas evaluadas: {len(result.metrics)}"
    )
    print(
        f"Problemas: {result.issue_count}"
    )
    print(
        f"Problemas críticos: "
        f"{result.critical_issue_count}"
    )
    print(
        f"Problemas altos: {result.high_issue_count}"
    )


def _print_relationship_summary(
    result: Any,
) -> None:
    """Presenta el resumen de validación relacional."""
    _print_section(
        "4. VALIDACIÓN DE RELACIONES"
    )

    print(
        f"Estado: {_format_status(result.is_valid)}"
    )
    print(
        f"Relaciones evaluadas: {len(result.metrics)}"
    )
    print(
        f"Problemas: {result.issue_count}"
    )
    print(
        f"Problemas críticos: "
        f"{result.critical_issue_count}"
    )
    print(
        f"Problemas altos: {result.high_issue_count}"
    )
    print(
        f"Registros afectados: "
        f"{result.affected_record_count}"
    )


def _print_issue_table(
    title: str,
    result: Any,
) -> None:
    """Muestra los problemas de una validación.

    Args:
        title: Nombre de la validación.
        result: Resultado que implementa to_dataframe().
    """
    if result.issue_count == 0:
        return

    issues_table = result.to_dataframe()

    _print_section(
        f"DETALLE: {title}"
    )

    print(
        issues_table.to_string(
            index=False
        )
    )


def _print_final_summary(
    input_path: Path,
    results: dict[str, Any],
) -> bool:
    """Presenta el resultado consolidado.

    Args:
        input_path: Libro evaluado.
        results: Resultados de las cuatro validaciones.

    Returns:
        Verdadero si todas las validaciones fueron aprobadas.
    """
    all_valid = all(
        result.is_valid
        for result in results.values()
    )

    print()
    print("=" * 70)
    print("RESULTADO CONSOLIDADO DE VALIDACIÓN")
    print("=" * 70)
    print(f"Archivo: {input_path}")
    print("Naturaleza: datos sintéticos")
    print("Uso: exclusivamente académico")
    print()

    for validation_name, result in results.items():
        print(
            f"{validation_name}: "
            f"{_format_status(result.is_valid)}"
        )

    print()
    print(
        "Resultado general: "
        f"{_format_status(all_valid)}"
    )
    print("=" * 70)

    return all_valid


def main(
    arguments: list[str] | None = None,
) -> int:
    """Ejecuta el proceso completo de validación.

    Args:
        arguments: Argumentos opcionales para pruebas.

    Returns:
        Código de salida del proceso.
    """
    parser = _build_argument_parser()
    parsed_arguments = parser.parse_args(
        arguments
    )

    input_path = _resolve_input_path(
        supplied_path=parsed_arguments.file
    )

    LOGGER.info(
        "Inicio del proceso completo de validación: %s",
        input_path,
    )

    print()
    print("=" * 70)
    print("VALIDACIÓN DEL LIBRO NOVARETAIL")
    print("=" * 70)
    print(f"Archivo: {input_path}")
    print(
        "El proceso no modificará el archivo analizado."
    )

    try:
        schema_result = validate_excel_schema(
            file_path=input_path
        )

        _print_schema_summary(
            result=schema_result
        )

        if not schema_result.is_valid:
            print()
            print(
                "La validación estructural detectó errores "
                "críticos. Las demás validaciones no se "
                "ejecutarán."
            )

            _print_issue_table(
                title="VALIDACIÓN ESTRUCTURAL",
                result=schema_result,
            )

            LOGGER.error(
                "Validación detenida por errores estructurales."
            )

            return 1

        quality_result = validate_data_quality(
            file_path=input_path
        )

        _print_quality_summary(
            result=quality_result
        )

        accounting_result = validate_accounting(
            file_path=input_path
        )

        _print_accounting_summary(
            result=accounting_result
        )

        relationship_result = validate_relationships(
            file_path=input_path
        )

        _print_relationship_summary(
            result=relationship_result
        )

    except (
        SchemaValidationError,
        QualityValidationError,
        AccountingValidationError,
        RelationshipValidationError,
        OSError,
        ValueError,
        KeyError,
    ) as exc:
        LOGGER.exception(
            "El proceso de validación no pudo completarse: %s",
            exc,
        )

        print()
        print("=" * 70)
        print("ERROR DE VALIDACIÓN")
        print("=" * 70)
        print(str(exc))
        print("=" * 70)

        return 2

    results = {
        "Estructura": schema_result,
        "Calidad": quality_result,
        "Contabilidad": accounting_result,
        "Relaciones": relationship_result,
    }

    _print_issue_table(
        title="VALIDACIÓN DE CALIDAD",
        result=quality_result,
    )

    _print_issue_table(
        title="VALIDACIÓN CONTABLE",
        result=accounting_result,
    )

    _print_issue_table(
        title="VALIDACIÓN DE RELACIONES",
        result=relationship_result,
    )

    all_valid = _print_final_summary(
        input_path=input_path,
        results=results,
    )

    if all_valid:
        LOGGER.info(
            "Proceso completo de validación aprobado."
        )

        return 0

    LOGGER.warning(
        "Proceso terminado con validaciones no aprobadas."
    )

    return 1


if __name__ == "__main__":
    raise SystemExit(main())