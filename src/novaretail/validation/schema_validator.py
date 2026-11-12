"""Validación estructural del libro Excel de NovaRetail.

Comprueba hojas, columnas, dimensiones, claves primarias,
campos obligatorios, periodos e identificación sintética.

La validación no modifica el archivo analizado.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

from novaretail.config import (
    load_data_generation_config,
    load_settings,
    resolve_project_path,
)
from novaretail.generation import (
    BALANCE_SHEET_COLUMNS,
    BUDGET_COLUMNS,
    CASH_FLOW_COLUMNS,
    CUSTOMER_COLUMNS,
    INCOME_STATEMENT_COLUMNS,
    INVENTORY_COLUMNS,
    MARKETING_COLUMNS,
    ORDER_COLUMNS,
    PRODUCT_COLUMNS,
    RETURN_COLUMNS,
)
from novaretail.generation.generator import TABLE_ORDER
from novaretail.logging_config import get_logger


LOGGER = get_logger(__name__)


EXPECTED_COLUMNS = {
    "00_Control": ["campo", "valor"],
    "01_Parametros": ["parametro", "valor", "tipo"],
    "02_Productos": PRODUCT_COLUMNS,
    "03_Clientes": CUSTOMER_COLUMNS,
    "04_Pedidos": ORDER_COLUMNS,
    "05_Inventario": INVENTORY_COLUMNS,
    "06_Devoluciones": RETURN_COLUMNS,
    "07_Marketing": MARKETING_COLUMNS,
    "08_Estado_Resultados": INCOME_STATEMENT_COLUMNS,
    "09_Balance_General": BALANCE_SHEET_COLUMNS,
    "10_Flujo_Efectivo": CASH_FLOW_COLUMNS,
    "11_Presupuesto": BUDGET_COLUMNS,
}


PRIMARY_KEYS = {
    "02_Productos": ["producto_id"],
    "03_Clientes": ["cliente_id"],
    "04_Pedidos": ["linea_pedido_id"],
    "05_Inventario": ["periodo", "producto_id"],
    "06_Devoluciones": ["devolucion_id"],
    "07_Marketing": ["campania_id"],
    "08_Estado_Resultados": ["periodo"],
    "09_Balance_General": ["periodo"],
    "10_Flujo_Efectivo": ["periodo"],
    "11_Presupuesto": ["presupuesto_id"],
}


REQUIRED_NON_NULL_COLUMNS = {
    "00_Control": [
        "campo",
        "valor",
    ],
    "01_Parametros": [
        "parametro",
        "valor",
        "tipo",
    ],
    "02_Productos": [
        "producto_id",
        "categoria",
        "precio_lista_cop",
        "costo_estandar_cop",
        "fecha_ingreso",
        "datos_sinteticos",
    ],
    "03_Clientes": [
        "cliente_id",
        "fecha_registro",
        "segmento",
        "ciudad",
        "departamento",
        "datos_sinteticos",
    ],
    "04_Pedidos": [
        "linea_pedido_id",
        "pedido_id",
        "fecha_pedido",
        "periodo",
        "cliente_id",
        "producto_id",
        "unidades",
        "valor_neto_cop",
        "estado_pedido",
        "datos_sinteticos",
    ],
    "05_Inventario": [
        "periodo",
        "producto_id",
        "inventario_final_unidades",
        "valor_inventario_final_cop",
        "datos_sinteticos",
    ],
    "06_Devoluciones": [
        "devolucion_id",
        "linea_pedido_id",
        "pedido_id",
        "fecha_devolucion",
        "producto_id",
        "valor_reintegrado_cop",
        "datos_sinteticos",
    ],
    "07_Marketing": [
        "periodo",
        "canal",
        "campania_id",
        "inversion_cop",
        "datos_sinteticos",
    ],
    "08_Estado_Resultados": [
        "periodo",
        "ingresos_netos_cop",
        "utilidad_neta_cop",
        "datos_sinteticos",
    ],
    "09_Balance_General": [
        "periodo",
        "total_activos_cop",
        "total_pasivo_patrimonio_cop",
        "datos_sinteticos",
    ],
    "10_Flujo_Efectivo": [
        "periodo",
        "efectivo_inicial_cop",
        "efectivo_final_cop",
        "datos_sinteticos",
    ],
    "11_Presupuesto": [
        "presupuesto_id",
        "periodo",
        "categoria",
        "valor_presupuestado_cop",
        "valor_ejecutado_cop",
        "datos_sinteticos",
    ],
}


MINIMUM_EXPECTED_ROWS = {
    "00_Control": 17,
    "01_Parametros": 1,
    "02_Productos": 1,
    "03_Clientes": 1,
    "04_Pedidos": 1,
    "05_Inventario": 1,
    "06_Devoluciones": 1,
    "07_Marketing": 1,
    "08_Estado_Resultados": 36,
    "09_Balance_General": 36,
    "10_Flujo_Efectivo": 36,
    "11_Presupuesto": 288,
}


FINANCIAL_MONTHLY_SHEETS = {
    "08_Estado_Resultados",
    "09_Balance_General",
    "10_Flujo_Efectivo",
}


@dataclass(frozen=True)
class SchemaIssue:
    """Problema estructural detectado."""

    sheet_name: str
    rule: str
    severity: str
    message: str


@dataclass(frozen=True)
class SchemaValidationResult:
    """Resultado de la validación estructural."""

    file_path: Path
    is_valid: bool
    issues: tuple
    sheet_summary: dict

    @property
    def issue_count(self) -> int:
        """Devuelve la cantidad total de problemas."""
        return len(self.issues)

    @property
    def critical_issue_count(self) -> int:
        """Devuelve la cantidad de problemas críticos."""
        return sum(
            issue.severity == "critical"
            for issue in self.issues
        )

    def to_dataframe(self) -> pd.DataFrame:
        """Convierte los problemas en un DataFrame."""
        records = [
            {
                "hoja": issue.sheet_name,
                "regla": issue.rule,
                "severidad": issue.severity,
                "mensaje": issue.message,
            }
            for issue in self.issues
        ]

        return pd.DataFrame(
            records,
            columns=[
                "hoja",
                "regla",
                "severidad",
                "mensaje",
            ],
        )


class SchemaValidationError(RuntimeError):
    """Error al abrir o procesar un libro Excel."""


def _resolve_excel_path(
    file_path: Path | str,
) -> Path:
    """Resuelve y valida la ruta del archivo Excel."""
    resolved_path = Path(file_path)

    if not resolved_path.is_absolute():
        resolved_path = resolve_project_path(
            str(resolved_path)
        )

    resolved_path = resolved_path.resolve()

    if resolved_path.suffix.lower() != ".xlsx":
        raise SchemaValidationError(
            "El archivo debe tener extensión .xlsx."
        )

    if not resolved_path.exists():
        raise SchemaValidationError(
            f"No se encontró el archivo: {resolved_path}"
        )

    if not resolved_path.is_file():
        raise SchemaValidationError(
            f"La ruta no corresponde a un archivo: {resolved_path}"
        )

    if resolved_path.stat().st_size == 0:
        raise SchemaValidationError(
            f"El archivo está vacío: {resolved_path}"
        )

    return resolved_path


def _add_issue(
    issues: list,
    sheet_name: str,
    rule: str,
    severity: str,
    message: str,
) -> None:
    """Agrega un problema a la colección."""
    issues.append(
        SchemaIssue(
            sheet_name=sheet_name,
            rule=rule,
            severity=severity,
            message=message,
        )
    )


def _validate_sheet_names(
    actual_sheet_names: list,
) -> list:
    """Valida presencia, hojas adicionales y orden."""
    issues = []

    for sheet_name in TABLE_ORDER:
        if sheet_name not in actual_sheet_names:
            _add_issue(
                issues=issues,
                sheet_name=sheet_name,
                rule="required_sheet",
                severity="critical",
                message=(
                    f"Falta la hoja obligatoria {sheet_name}."
                ),
            )

    for sheet_name in actual_sheet_names:
        if sheet_name not in TABLE_ORDER:
            _add_issue(
                issues=issues,
                sheet_name=sheet_name,
                rule="unexpected_sheet",
                severity="medium",
                message=(
                    f"La hoja {sheet_name} no pertenece "
                    "a la estructura aprobada."
                ),
            )

    existing_expected = [
        sheet_name
        for sheet_name in actual_sheet_names
        if sheet_name in TABLE_ORDER
    ]

    expected_existing_order = [
        sheet_name
        for sheet_name in TABLE_ORDER
        if sheet_name in actual_sheet_names
    ]

    if existing_expected != expected_existing_order:
        _add_issue(
            issues=issues,
            sheet_name="Libro",
            rule="sheet_order",
            severity="medium",
            message=(
                "Las hojas obligatorias no conservan "
                "el orden establecido."
            ),
        )

    return issues


def _validate_columns(
    sheet_name: str,
    dataframe: pd.DataFrame,
) -> list:
    """Valida columnas faltantes, adicionales y orden."""
    issues = []
    expected_columns = EXPECTED_COLUMNS[sheet_name]
    actual_columns = dataframe.columns.tolist()

    missing_columns = [
        column
        for column in expected_columns
        if column not in actual_columns
    ]

    unexpected_columns = [
        column
        for column in actual_columns
        if column not in expected_columns
    ]

    for column in missing_columns:
        _add_issue(
            issues=issues,
            sheet_name=sheet_name,
            rule="required_column",
            severity="critical",
            message=(
                f"Falta la columna obligatoria {column}."
            ),
        )

    for column in unexpected_columns:
        _add_issue(
            issues=issues,
            sheet_name=sheet_name,
            rule="unexpected_column",
            severity="medium",
            message=(
                f"La columna {column} no pertenece "
                "al contrato de datos."
            ),
        )

    if (
        not missing_columns
        and not unexpected_columns
        and actual_columns != expected_columns
    ):
        _add_issue(
            issues=issues,
            sheet_name=sheet_name,
            rule="column_order",
            severity="medium",
            message=(
                "Las columnas no conservan el orden definido."
            ),
        )

    return issues


def _validate_minimum_rows(
    sheet_name: str,
    dataframe: pd.DataFrame,
) -> list:
    """Valida la cantidad mínima de registros."""
    minimum_rows = MINIMUM_EXPECTED_ROWS[sheet_name]

    if len(dataframe) >= minimum_rows:
        return []

    return [
        SchemaIssue(
            sheet_name=sheet_name,
            rule="minimum_rows",
            severity="critical",
            message=(
                f"La hoja contiene {len(dataframe)} registros. "
                f"Se requieren al menos {minimum_rows}."
            ),
        )
    ]


def _validate_required_values(
    sheet_name: str,
    dataframe: pd.DataFrame,
) -> list:
    """Valida nulos en campos obligatorios."""
    issues = []

    for column in REQUIRED_NON_NULL_COLUMNS.get(
        sheet_name,
        [],
    ):
        if column not in dataframe.columns:
            continue

        null_count = int(
            dataframe[column].isna().sum()
        )

        if null_count > 0:
            _add_issue(
                issues=issues,
                sheet_name=sheet_name,
                rule="required_non_null",
                severity="critical",
                message=(
                    f"La columna {column} contiene "
                    f"{null_count} valores nulos."
                ),
            )

    return issues


def _validate_primary_key(
    sheet_name: str,
    dataframe: pd.DataFrame,
) -> list:
    """Valida completitud y unicidad de la clave primaria."""
    primary_key = PRIMARY_KEYS.get(sheet_name)

    if primary_key is None:
        return []

    if any(
        column not in dataframe.columns
        for column in primary_key
    ):
        return []

    issues = []

    null_key_rows = int(
        dataframe[primary_key]
        .isna()
        .any(axis=1)
        .sum()
    )

    if null_key_rows > 0:
        _add_issue(
            issues=issues,
            sheet_name=sheet_name,
            rule="primary_key_null",
            severity="critical",
            message=(
                "La clave primaria contiene "
                f"{null_key_rows} registros incompletos."
            ),
        )

    duplicate_count = int(
        dataframe.duplicated(
            subset=primary_key,
            keep=False,
        ).sum()
    )

    if duplicate_count > 0:
        _add_issue(
            issues=issues,
            sheet_name=sheet_name,
            rule="primary_key_duplicate",
            severity="critical",
            message=(
                "La clave primaria contiene "
                f"{duplicate_count} registros duplicados."
            ),
        )

    return issues


def _validate_expected_periods(
    sheet_name: str,
    dataframe: pd.DataFrame,
) -> list:
    """Valida los periodos de las tablas financieras."""
    if sheet_name not in FINANCIAL_MONTHLY_SHEETS:
        return []

    if "periodo" not in dataframe.columns:
        return []

    expected_months = int(
        load_settings()["period"]["expected_months"]
    )

    actual_months = int(
        dataframe["periodo"].nunique(
            dropna=True
        )
    )

    if actual_months == expected_months:
        return []

    return [
        SchemaIssue(
            sheet_name=sheet_name,
            rule="expected_periods",
            severity="critical",
            message=(
                f"La hoja contiene {actual_months} periodos. "
                f"Se esperaban {expected_months}."
            ),
        )
    ]


def _validate_synthetic_flag(
    sheet_name: str,
    dataframe: pd.DataFrame,
) -> list:
    """Valida la identificación de datos sintéticos."""
    if "datos_sinteticos" not in dataframe.columns:
        return []

    values = dataframe["datos_sinteticos"]

    null_count = int(values.isna().sum())

    if null_count > 0:
        return [
            SchemaIssue(
                sheet_name=sheet_name,
                rule="synthetic_flag",
                severity="critical",
                message=(
                    "La columna datos_sinteticos contiene "
                    f"{null_count} valores nulos."
                ),
            )
        ]

    normalized_values = (
        values.astype(str)
        .str.strip()
        .str.lower()
    )

    valid_values = normalized_values.isin(
        {"true", "1"}
    )

    invalid_count = int(
        (~valid_values).sum()
    )

    if invalid_count == 0:
        return []

    return [
        SchemaIssue(
            sheet_name=sheet_name,
            rule="synthetic_flag",
            severity="critical",
            message=(
                f"Se encontraron {invalid_count} registros "
                "no identificados como sintéticos."
            ),
        )
    ]


def validate_excel_schema(
    file_path: Path | str,
) -> SchemaValidationResult:
    """Valida la estructura completa de un libro NovaRetail."""
    resolved_path = _resolve_excel_path(
        file_path=file_path
    )

    LOGGER.info(
        "Iniciando validación de esquema: %s",
        resolved_path,
    )

    try:
        workbook = load_workbook(
            resolved_path,
            read_only=True,
            data_only=True,
        )

        actual_sheet_names = workbook.sheetnames
        workbook.close()

    except Exception as exc:
        raise SchemaValidationError(
            "No fue posible abrir el libro Excel."
        ) from exc

    issues = _validate_sheet_names(
        actual_sheet_names=actual_sheet_names
    )

    sheet_summary = {}

    for sheet_name in TABLE_ORDER:
        if sheet_name not in actual_sheet_names:
            continue

        try:
            dataframe = pd.read_excel(
                resolved_path,
                sheet_name=sheet_name,
                engine="openpyxl",
            )

        except Exception as exc:
            raise SchemaValidationError(
                f"No fue posible leer la hoja {sheet_name}."
            ) from exc

        sheet_summary[sheet_name] = {
            "filas": len(dataframe),
            "columnas": len(dataframe.columns),
        }

        issues.extend(
            _validate_columns(
                sheet_name=sheet_name,
                dataframe=dataframe,
            )
        )

        issues.extend(
            _validate_minimum_rows(
                sheet_name=sheet_name,
                dataframe=dataframe,
            )
        )

        issues.extend(
            _validate_required_values(
                sheet_name=sheet_name,
                dataframe=dataframe,
            )
        )

        issues.extend(
            _validate_primary_key(
                sheet_name=sheet_name,
                dataframe=dataframe,
            )
        )

        issues.extend(
            _validate_expected_periods(
                sheet_name=sheet_name,
                dataframe=dataframe,
            )
        )

        issues.extend(
            _validate_synthetic_flag(
                sheet_name=sheet_name,
                dataframe=dataframe,
            )
        )

    critical_count = sum(
        issue.severity == "critical"
        for issue in issues
    )

    result = SchemaValidationResult(
        file_path=resolved_path,
        is_valid=critical_count == 0,
        issues=tuple(issues),
        sheet_summary=sheet_summary,
    )

    LOGGER.info(
        "Validación finalizada. Válido: %s. "
        "Problemas: %s. Críticos: %s.",
        result.is_valid,
        result.issue_count,
        result.critical_issue_count,
    )

    return result


def validate_default_raw_workbook() -> SchemaValidationResult:
    """Valida el libro RAW configurado en el proyecto."""
    settings = load_settings()
    generation_config = load_data_generation_config()

    raw_directory = resolve_project_path(
        settings["paths"]["raw_data"]
    )

    filename = generation_config[
        "output"
    ]["raw_workbook"]

    return validate_excel_schema(
        file_path=raw_directory / filename
    )
