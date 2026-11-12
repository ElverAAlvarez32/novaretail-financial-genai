"""Validación de calidad de datos del libro NovaRetail.

Este módulo revisa valores nulos, duplicados, rangos numéricos,
fechas y valores atípicos. La validación no modifica el archivo.

Una observación de valor atípico representa una alerta para revisión,
no una confirmación de error.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from novaretail.config import (
    load_data_generation_config,
    load_quality_rules,
    load_settings,
    resolve_project_path,
)
from novaretail.generation.generator import TABLE_ORDER
from novaretail.logging_config import get_logger
from novaretail.validation.schema_validator import (
    SchemaValidationError,
    validate_excel_schema,
)


LOGGER = get_logger(__name__)


DATE_COLUMNS = {
    "02_Productos": [
        "fecha_ingreso",
    ],
    "03_Clientes": [
        "fecha_registro",
    ],
    "04_Pedidos": [
        "fecha_pedido",
    ],
    "06_Devoluciones": [
        "fecha_devolucion",
    ],
}


NUMERIC_RULES_BY_SHEET = {
    "02_Productos": {
        "precio_lista_cop": "precio_unitario",
        "costo_estandar_cop": "costo_unitario",
        "margen_objetivo": "margen_objetivo",
    },
    "04_Pedidos": {
        "unidades": "unidades",
        "precio_unitario_cop": "precio_unitario",
        "costo_unitario_cop": "costo_unitario",
        "descuento_rate": "descuento_rate",
        "dias_entrega": "dias_entrega",
    },
    "06_Devoluciones": {
        "unidades_devueltas": "unidades",
        "valor_reintegrado_cop": "valor_monetario",
        "costo_logistico_cop": "valor_monetario",
    },
    "07_Marketing": {
        "inversion_cop": "valor_monetario",
        "impresiones": "valor_monetario",
        "clics": "valor_monetario",
        "sesiones": "valor_monetario",
        "conversiones": "valor_monetario",
        "pedidos_atribuidos": "valor_monetario",
    },
    "08_Estado_Resultados": {
        "ingresos_brutos_cop": "valor_monetario",
        "ingresos_netos_cop": "valor_monetario",
        "costo_mercancia_vendida_cop": "valor_monetario",
        "impuesto_cop": "valor_monetario",
    },
    "09_Balance_General": {
        "efectivo_cop": "valor_monetario",
        "total_activos_cop": "valor_monetario",
        "total_pasivos_cop": "valor_monetario",
        "total_patrimonio_cop": "valor_monetario",
    },
    "11_Presupuesto": {
        "valor_presupuestado_cop": "valor_monetario",
        "valor_ejecutado_cop": "valor_monetario",
    },
}


OUTLIER_COLUMNS = {
    "02_Productos": [
        "precio_lista_cop",
        "costo_estandar_cop",
    ],
    "04_Pedidos": [
        "valor_neto_cop",
        "costo_total_cop",
        "margen_bruto_cop",
    ],
    "06_Devoluciones": [
        "valor_reintegrado_cop",
        "costo_total_devolucion_cop",
    ],
    "07_Marketing": [
        "inversion_cop",
        "ingresos_atribuidos_cop",
        "costo_adquisicion_cop",
        "retorno_publicitario",
    ],
    "08_Estado_Resultados": [
        "ingresos_netos_cop",
        "utilidad_operacional_cop",
        "utilidad_neta_cop",
    ],
    "09_Balance_General": [
        "total_activos_cop",
        "total_pasivos_cop",
        "total_patrimonio_cop",
    ],
    "10_Flujo_Efectivo": [
        "flujo_operacion_cop",
        "flujo_inversion_cop",
        "flujo_financiacion_cop",
    ],
    "11_Presupuesto": [
        "variacion_absoluta_cop",
        "variacion_porcentual",
    ],
}


@dataclass(frozen=True)
class QualityIssue:
    """Problema o alerta de calidad encontrado."""

    sheet_name: str
    rule: str
    severity: str
    column_name: str
    affected_records: int
    message: str


@dataclass(frozen=True)
class QualityValidationResult:
    """Resultado completo de la validación de calidad."""

    file_path: Path
    is_valid: bool
    issues: tuple[QualityIssue, ...]
    metrics: dict[str, dict[str, int]]

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

    @property
    def high_issue_count(self) -> int:
        """Devuelve la cantidad de problemas de severidad alta."""
        return sum(
            issue.severity == "high"
            for issue in self.issues
        )

    @property
    def outlier_alert_count(self) -> int:
        """Devuelve el total de registros marcados como atípicos."""
        return sum(
            issue.affected_records
            for issue in self.issues
            if issue.rule == "iqr_outlier"
        )

    def to_dataframe(self) -> pd.DataFrame:
        """Convierte los problemas en una tabla."""
        records = [
            {
                "hoja": issue.sheet_name,
                "regla": issue.rule,
                "severidad": issue.severity,
                "columna": issue.column_name,
                "registros_afectados": (
                    issue.affected_records
                ),
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
                "columna",
                "registros_afectados",
                "mensaje",
            ],
        )


class QualityValidationError(RuntimeError):
    """Error durante la validación de calidad."""


def _resolve_excel_path(
    file_path: Path | str,
) -> Path:
    """Resuelve y valida la ruta del libro Excel."""
    resolved_path = Path(file_path)

    if not resolved_path.is_absolute():
        resolved_path = resolve_project_path(
            str(resolved_path)
        )

    resolved_path = resolved_path.resolve()

    if resolved_path.suffix.lower() != ".xlsx":
        raise QualityValidationError(
            "El archivo debe tener extensión .xlsx."
        )

    if not resolved_path.exists():
        raise QualityValidationError(
            f"No se encontró el archivo: {resolved_path}"
        )

    if not resolved_path.is_file():
        raise QualityValidationError(
            f"La ruta no corresponde a un archivo: {resolved_path}"
        )

    return resolved_path


def _add_issue(
    issues: list[QualityIssue],
    sheet_name: str,
    rule: str,
    severity: str,
    column_name: str,
    affected_records: int,
    message: str,
) -> None:
    """Agrega un problema a la colección."""
    issues.append(
        QualityIssue(
            sheet_name=sheet_name,
            rule=rule,
            severity=severity,
            column_name=column_name,
            affected_records=affected_records,
            message=message,
        )
    )


def _validate_missing_values(
    sheet_name: str,
    dataframe: pd.DataFrame,
    issues: list[QualityIssue],
) -> int:
    """Registra columnas que contienen valores nulos."""
    total_missing = 0

    for column_name in dataframe.columns:
        missing_count = int(
            dataframe[column_name].isna().sum()
        )

        total_missing += missing_count

        if missing_count == 0:
            continue

        missing_rate = (
            missing_count / len(dataframe) * 100
            if len(dataframe) > 0
            else 0
        )

        _add_issue(
            issues=issues,
            sheet_name=sheet_name,
            rule="missing_value",
            severity="medium",
            column_name=str(column_name),
            affected_records=missing_count,
            message=(
                f"La columna contiene {missing_count} valores "
                f"nulos, equivalentes al {missing_rate:.2f} %."
            ),
        )

    return total_missing


def _validate_complete_duplicates(
    sheet_name: str,
    dataframe: pd.DataFrame,
    issues: list[QualityIssue],
) -> int:
    """Detecta filas completamente duplicadas."""
    duplicate_count = int(
        dataframe.duplicated(
            keep=False
        ).sum()
    )

    if duplicate_count > 0:
        _add_issue(
            issues=issues,
            sheet_name=sheet_name,
            rule="complete_duplicate",
            severity="high",
            column_name="todas",
            affected_records=duplicate_count,
            message=(
                f"Se detectaron {duplicate_count} registros "
                "involucrados en duplicados completos."
            ),
        )

    return duplicate_count


def _validate_dates(
    sheet_name: str,
    dataframe: pd.DataFrame,
    issues: list[QualityIssue],
) -> int:
    """Valida fechas y límites del periodo del proyecto."""
    configuration = load_data_generation_config()

    minimum_date = pd.Timestamp(
        configuration["period"]["start_date"]
    )

    maximum_date = pd.Timestamp(
        configuration["period"]["end_date"]
    )

    invalid_total = 0

    for column_name in DATE_COLUMNS.get(
        sheet_name,
        [],
    ):
        if column_name not in dataframe.columns:
            continue

        original_values = dataframe[column_name]

        parsed_dates = pd.to_datetime(
            original_values,
            errors="coerce",
        )

        invalid_mask = (
            original_values.notna()
            & parsed_dates.isna()
        )

        invalid_count = int(
            invalid_mask.sum()
        )

        invalid_total += invalid_count

        if invalid_count > 0:
            _add_issue(
                issues=issues,
                sheet_name=sheet_name,
                rule="invalid_date",
                severity="high",
                column_name=column_name,
                affected_records=invalid_count,
                message=(
                    f"Se detectaron {invalid_count} fechas "
                    "que no pueden interpretarse."
                ),
            )

        outside_period_mask = (
            parsed_dates.notna()
            & (
                (parsed_dates < minimum_date)
                | (parsed_dates > maximum_date)
            )
        )

        outside_count = int(
            outside_period_mask.sum()
        )

        invalid_total += outside_count

        if outside_count > 0:
            _add_issue(
                issues=issues,
                sheet_name=sheet_name,
                rule="date_outside_period",
                severity="high",
                column_name=column_name,
                affected_records=outside_count,
                message=(
                    f"Se detectaron {outside_count} fechas "
                    "fuera del periodo 2023-01-01 a 2025-12-31."
                ),
            )

    return invalid_total


def _validate_numeric_ranges(
    sheet_name: str,
    dataframe: pd.DataFrame,
    issues: list[QualityIssue],
) -> int:
    """Valida los rangos numéricos configurados."""
    quality_rules = load_quality_rules()
    rules = quality_rules["numeric_rules"]

    invalid_total = 0

    for column_name, rule_name in (
        NUMERIC_RULES_BY_SHEET.get(
            sheet_name,
            {},
        ).items()
    ):
        if column_name not in dataframe.columns:
            continue

        rule = rules[rule_name]

        numeric_values = pd.to_numeric(
            dataframe[column_name],
            errors="coerce",
        )

        non_numeric_mask = (
            dataframe[column_name].notna()
            & numeric_values.isna()
        )

        non_numeric_count = int(
            non_numeric_mask.sum()
        )

        invalid_total += non_numeric_count

        if non_numeric_count > 0:
            _add_issue(
                issues=issues,
                sheet_name=sheet_name,
                rule="non_numeric_value",
                severity=str(rule["severity"]),
                column_name=column_name,
                affected_records=non_numeric_count,
                message=(
                    f"Se detectaron {non_numeric_count} valores "
                    "que no pueden convertirse a número."
                ),
            )

        valid_values = numeric_values.dropna()

        invalid_mask = pd.Series(
            False,
            index=valid_values.index,
        )

        if "minimum" in rule:
            invalid_mask = (
                invalid_mask
                | (
                    valid_values
                    < float(rule["minimum"])
                )
            )

        if "maximum" in rule:
            invalid_mask = (
                invalid_mask
                | (
                    valid_values
                    > float(rule["maximum"])
                )
            )

        invalid_count = int(
            invalid_mask.sum()
        )

        invalid_total += invalid_count

        if invalid_count > 0:
            minimum_text = rule.get(
                "minimum",
                "sin mínimo",
            )

            maximum_text = rule.get(
                "maximum",
                "sin máximo",
            )

            _add_issue(
                issues=issues,
                sheet_name=sheet_name,
                rule="numeric_range",
                severity=str(rule["severity"]),
                column_name=column_name,
                affected_records=invalid_count,
                message=(
                    f"Se detectaron {invalid_count} valores "
                    f"fuera del rango {minimum_text} a "
                    f"{maximum_text}."
                ),
            )

    return invalid_total


def _validate_outliers(
    sheet_name: str,
    dataframe: pd.DataFrame,
    issues: list[QualityIssue],
) -> int:
    """Detecta alertas de valores atípicos mediante IQR."""
    quality_rules = load_quality_rules()
    outlier_rules = quality_rules["outlier_rules"]

    multiplier = float(
        outlier_rules["iqr_multiplier"]
    )

    severity = str(
        outlier_rules["severity"]
    )

    total_outliers = 0

    for column_name in OUTLIER_COLUMNS.get(
        sheet_name,
        [],
    ):
        if column_name not in dataframe.columns:
            continue

        numeric_values = pd.to_numeric(
            dataframe[column_name],
            errors="coerce",
        ).dropna()

        if len(numeric_values) < 4:
            continue

        first_quartile = float(
            numeric_values.quantile(0.25)
        )

        third_quartile = float(
            numeric_values.quantile(0.75)
        )

        interquartile_range = (
            third_quartile - first_quartile
        )

        if interquartile_range == 0:
            continue

        lower_limit = (
            first_quartile
            - multiplier * interquartile_range
        )

        upper_limit = (
            third_quartile
            + multiplier * interquartile_range
        )

        outlier_mask = (
            (numeric_values < lower_limit)
            | (numeric_values > upper_limit)
        )

        outlier_count = int(
            outlier_mask.sum()
        )

        total_outliers += outlier_count

        if outlier_count > 0:
            _add_issue(
                issues=issues,
                sheet_name=sheet_name,
                rule="iqr_outlier",
                severity=severity,
                column_name=column_name,
                affected_records=outlier_count,
                message=(
                    f"Se marcaron {outlier_count} observaciones "
                    f"fuera del rango IQR [{lower_limit:.2f}, "
                    f"{upper_limit:.2f}]. Requieren revisión, "
                    "pero no se clasifican automáticamente "
                    "como errores."
                ),
            )

    return total_outliers


def validate_data_quality(
    file_path: Path | str,
) -> QualityValidationResult:
    """Ejecuta la validación de calidad del libro NovaRetail.

    Args:
        file_path: Ruta absoluta o relativa del archivo Excel.

    Returns:
        Resultado estructurado de calidad.

    Raises:
        QualityValidationError: Si el libro no puede procesarse.
    """
    resolved_path = _resolve_excel_path(
        file_path=file_path
    )

    LOGGER.info(
        "Iniciando validación de calidad: %s",
        resolved_path,
    )

    try:
        schema_result = validate_excel_schema(
            file_path=resolved_path
        )
    except SchemaValidationError as exc:
        raise QualityValidationError(
            "No fue posible validar la estructura del libro."
        ) from exc

    if not schema_result.is_valid:
        raise QualityValidationError(
            "El libro contiene errores estructurales críticos. "
            "La calidad no puede evaluarse de forma confiable."
        )

    issues: list[QualityIssue] = []
    metrics: dict[str, dict[str, int]] = {}

    for sheet_name in TABLE_ORDER:
        dataframe = pd.read_excel(
            resolved_path,
            sheet_name=sheet_name,
            engine="openpyxl",
        )

        missing_count = _validate_missing_values(
            sheet_name=sheet_name,
            dataframe=dataframe,
            issues=issues,
        )

        duplicate_count = _validate_complete_duplicates(
            sheet_name=sheet_name,
            dataframe=dataframe,
            issues=issues,
        )

        invalid_date_count = _validate_dates(
            sheet_name=sheet_name,
            dataframe=dataframe,
            issues=issues,
        )

        invalid_numeric_count = (
            _validate_numeric_ranges(
                sheet_name=sheet_name,
                dataframe=dataframe,
                issues=issues,
            )
        )

        outlier_count = _validate_outliers(
            sheet_name=sheet_name,
            dataframe=dataframe,
            issues=issues,
        )

        metrics[sheet_name] = {
            "filas": len(dataframe),
            "columnas": len(dataframe.columns),
            "valores_nulos": missing_count,
            "filas_duplicadas": duplicate_count,
            "fechas_invalidas": invalid_date_count,
            "valores_fuera_rango": (
                invalid_numeric_count
            ),
            "alertas_atipicas": outlier_count,
        }

    blocking_severities = {
        "critical",
        "high",
    }

    blocking_issue_count = sum(
        issue.severity in blocking_severities
        for issue in issues
    )

    result = QualityValidationResult(
        file_path=resolved_path,
        is_valid=blocking_issue_count == 0,
        issues=tuple(issues),
        metrics=metrics,
    )

    LOGGER.info(
        "Validación de calidad finalizada. "
        "Válido: %s. Problemas: %s. "
        "Críticos: %s. Altos: %s. "
        "Alertas atípicas: %s.",
        result.is_valid,
        result.issue_count,
        result.critical_issue_count,
        result.high_issue_count,
        result.outlier_alert_count,
    )

    return result


def validate_default_raw_quality() -> QualityValidationResult:
    """Valida la calidad del libro RAW configurado."""
    settings = load_settings()
    generation_config = load_data_generation_config()

    raw_directory = resolve_project_path(
        settings["paths"]["raw_data"]
    )

    filename = generation_config[
        "output"
    ]["raw_workbook"]

    return validate_data_quality(
        file_path=raw_directory / filename
    )
