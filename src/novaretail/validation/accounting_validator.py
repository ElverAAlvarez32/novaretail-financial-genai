"""Validación contable del libro Excel de NovaRetail.

Este módulo comprueba las principales ecuaciones del estado de
resultados, balance general, flujo de efectivo e inventario.

La validación no modifica el archivo analizado. Todos los cálculos
se realizan sobre datos sintéticos de uso exclusivamente académico.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from novaretail.config import (
    load_data_generation_config,
    load_quality_rules,
    load_settings,
    resolve_project_path,
)
from novaretail.logging_config import get_logger
from novaretail.validation.schema_validator import (
    SchemaValidationError,
    validate_excel_schema,
)


LOGGER = get_logger(__name__)


@dataclass(frozen=True)
class AccountingIssue:
    """Representa una diferencia contable detectada."""

    sheet_name: str
    rule: str
    severity: str
    affected_records: int
    maximum_difference: float
    message: str


@dataclass(frozen=True)
class AccountingValidationResult:
    """Resultado de la validación contable."""

    file_path: Path
    is_valid: bool
    issues: tuple[AccountingIssue, ...]
    metrics: dict[str, dict[str, float | int | bool]]

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

    def to_dataframe(self) -> pd.DataFrame:
        """Convierte los problemas contables en una tabla."""
        records = [
            {
                "hoja": issue.sheet_name,
                "regla": issue.rule,
                "severidad": issue.severity,
                "registros_afectados": (
                    issue.affected_records
                ),
                "diferencia_maxima": (
                    issue.maximum_difference
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
                "registros_afectados",
                "diferencia_maxima",
                "mensaje",
            ],
        )


class AccountingValidationError(RuntimeError):
    """Error durante la validación contable."""


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
        raise AccountingValidationError(
            "El archivo debe tener extensión .xlsx."
        )

    if not resolved_path.exists():
        raise AccountingValidationError(
            f"No se encontró el archivo: {resolved_path}"
        )

    if not resolved_path.is_file():
        raise AccountingValidationError(
            "La ruta suministrada no corresponde a un archivo."
        )

    if resolved_path.stat().st_size == 0:
        raise AccountingValidationError(
            "El archivo Excel está vacío."
        )

    return resolved_path


def _load_sheet(
    file_path: Path,
    sheet_name: str,
) -> pd.DataFrame:
    """Carga una hoja financiera del libro."""
    try:
        return pd.read_excel(
            file_path,
            sheet_name=sheet_name,
            engine="openpyxl",
        )

    except Exception as exc:
        raise AccountingValidationError(
            f"No fue posible leer la hoja {sheet_name}."
        ) from exc


def _numeric_series(
    dataframe: pd.DataFrame,
    column_name: str,
    sheet_name: str,
) -> pd.Series:
    """Convierte una columna financiera a valores numéricos."""
    if column_name not in dataframe.columns:
        raise AccountingValidationError(
            f"Falta la columna {column_name} "
            f"en la hoja {sheet_name}."
        )

    numeric_values = pd.to_numeric(
        dataframe[column_name],
        errors="coerce",
    )

    invalid_count = int(
        numeric_values.isna().sum()
    )

    if invalid_count > 0:
        raise AccountingValidationError(
            f"La columna {column_name} de {sheet_name} "
            f"contiene {invalid_count} valores no numéricos."
        )

    return numeric_values


def _add_equation_result(
    issues: list[AccountingIssue],
    metrics: dict[str, dict[str, float | int | bool]],
    sheet_name: str,
    rule: str,
    difference: pd.Series,
    tolerance: float,
    severity: str,
) -> None:
    """Registra el resultado de una ecuación contable."""
    absolute_difference = (
        pd.to_numeric(
            difference,
            errors="coerce",
        )
        .abs()
    )

    if absolute_difference.isna().any():
        raise AccountingValidationError(
            f"La regla {rule} produjo diferencias no numéricas."
        )

    invalid_mask = absolute_difference > tolerance

    affected_records = int(
        invalid_mask.sum()
    )

    maximum_difference = (
        float(absolute_difference.max())
        if not absolute_difference.empty
        else 0.0
    )

    metrics[rule] = {
        "registros_evaluados": len(
            absolute_difference
        ),
        "registros_afectados": affected_records,
        "diferencia_maxima": maximum_difference,
        "tolerancia": float(tolerance),
        "cumple": affected_records == 0,
    }

    if affected_records == 0:
        return

    issues.append(
        AccountingIssue(
            sheet_name=sheet_name,
            rule=rule,
            severity=severity,
            affected_records=affected_records,
            maximum_difference=maximum_difference,
            message=(
                f"La regla {rule} presenta "
                f"{affected_records} registros fuera de "
                f"la tolerancia {tolerance}. La diferencia "
                f"máxima es {maximum_difference:.2f}."
            ),
        )
    )


def _validate_income_statement(
    dataframe: pd.DataFrame,
    issues: list[AccountingIssue],
    metrics: dict[str, dict[str, float | int | bool]],
) -> None:
    """Valida las ecuaciones del estado de resultados."""
    sheet_name = "08_Estado_Resultados"
    rules = load_quality_rules()["accounting_rules"]

    gross_revenue = _numeric_series(
        dataframe,
        "ingresos_brutos_cop",
        sheet_name,
    )

    discounts = _numeric_series(
        dataframe,
        "descuentos_cop",
        sheet_name,
    )

    sales_returns = _numeric_series(
        dataframe,
        "devoluciones_ventas_cop",
        sheet_name,
    )

    net_revenue = _numeric_series(
        dataframe,
        "ingresos_netos_cop",
        sheet_name,
    )

    cost_of_goods_sold = _numeric_series(
        dataframe,
        "costo_mercancia_vendida_cop",
        sheet_name,
    )

    gross_profit = _numeric_series(
        dataframe,
        "utilidad_bruta_cop",
        sheet_name,
    )

    operating_expenses = _numeric_series(
        dataframe,
        "total_gastos_operacionales_cop",
        sheet_name,
    )

    operating_profit = _numeric_series(
        dataframe,
        "utilidad_operacional_cop",
        sheet_name,
    )

    non_operating_income = _numeric_series(
        dataframe,
        "ingresos_no_operacionales_cop",
        sheet_name,
    )

    financial_expenses = _numeric_series(
        dataframe,
        "gastos_financieros_cop",
        sheet_name,
    )

    profit_before_tax = _numeric_series(
        dataframe,
        "utilidad_antes_impuestos_cop",
        sheet_name,
    )

    income_tax = _numeric_series(
        dataframe,
        "impuesto_cop",
        sheet_name,
    )

    net_profit = _numeric_series(
        dataframe,
        "utilidad_neta_cop",
        sheet_name,
    )

    net_revenue_rule = rules["net_revenue"]

    net_revenue_difference = (
        net_revenue
        - (
            gross_revenue
            - discounts
            - sales_returns
        )
    )

    _add_equation_result(
        issues=issues,
        metrics=metrics,
        sheet_name=sheet_name,
        rule="net_revenue",
        difference=net_revenue_difference,
        tolerance=float(
            net_revenue_rule["tolerance"]
        ),
        severity=str(
            net_revenue_rule["severity"]
        ),
    )

    gross_profit_rule = rules["gross_profit"]

    gross_profit_difference = (
        gross_profit
        - (
            net_revenue
            - cost_of_goods_sold
        )
    )

    _add_equation_result(
        issues=issues,
        metrics=metrics,
        sheet_name=sheet_name,
        rule="gross_profit",
        difference=gross_profit_difference,
        tolerance=float(
            gross_profit_rule["tolerance"]
        ),
        severity=str(
            gross_profit_rule["severity"]
        ),
    )

    operating_profit_rule = rules[
        "operating_profit"
    ]

    operating_profit_difference = (
        operating_profit
        - (
            gross_profit
            - operating_expenses
        )
    )

    _add_equation_result(
        issues=issues,
        metrics=metrics,
        sheet_name=sheet_name,
        rule="operating_profit",
        difference=operating_profit_difference,
        tolerance=float(
            operating_profit_rule["tolerance"]
        ),
        severity=str(
            operating_profit_rule["severity"]
        ),
    )

    profit_before_tax_rule = rules[
        "profit_before_tax"
    ]

    profit_before_tax_difference = (
        profit_before_tax
        - (
            operating_profit
            + non_operating_income
            - financial_expenses
        )
    )

    _add_equation_result(
        issues=issues,
        metrics=metrics,
        sheet_name=sheet_name,
        rule="profit_before_tax",
        difference=profit_before_tax_difference,
        tolerance=float(
            profit_before_tax_rule["tolerance"]
        ),
        severity=str(
            profit_before_tax_rule["severity"]
        ),
    )

    net_profit_rule = rules["net_profit"]

    net_profit_difference = (
        net_profit
        - (
            profit_before_tax
            - income_tax
        )
    )

    _add_equation_result(
        issues=issues,
        metrics=metrics,
        sheet_name=sheet_name,
        rule="net_profit",
        difference=net_profit_difference,
        tolerance=float(
            net_profit_rule["tolerance"]
        ),
        severity=str(
            net_profit_rule["severity"]
        ),
    )


def _validate_balance_sheet(
    dataframe: pd.DataFrame,
    issues: list[AccountingIssue],
    metrics: dict[str, dict[str, float | int | bool]],
) -> None:
    """Valida la ecuación del balance general."""
    sheet_name = "09_Balance_General"
    rule = load_quality_rules()[
        "accounting_rules"
    ]["balance_equation"]

    total_assets = _numeric_series(
        dataframe,
        "total_activos_cop",
        sheet_name,
    )

    liabilities_and_equity = _numeric_series(
        dataframe,
        "total_pasivo_patrimonio_cop",
        sheet_name,
    )

    balance_difference = (
        total_assets
        - liabilities_and_equity
    )

    _add_equation_result(
        issues=issues,
        metrics=metrics,
        sheet_name=sheet_name,
        rule="balance_equation",
        difference=balance_difference,
        tolerance=float(rule["tolerance"]),
        severity=str(rule["severity"]),
    )

    recorded_difference = _numeric_series(
        dataframe,
        "diferencia_balance_cop",
        sheet_name,
    )

    difference_control = (
        recorded_difference
        - balance_difference
    )

    _add_equation_result(
        issues=issues,
        metrics=metrics,
        sheet_name=sheet_name,
        rule="recorded_balance_difference",
        difference=difference_control,
        tolerance=float(rule["tolerance"]),
        severity=str(rule["severity"]),
    )


def _validate_cash_flow(
    dataframe: pd.DataFrame,
    issues: list[AccountingIssue],
    metrics: dict[str, dict[str, float | int | bool]],
) -> None:
    """Valida las ecuaciones del flujo de efectivo."""
    sheet_name = "10_Flujo_Efectivo"
    rule = load_quality_rules()[
        "accounting_rules"
    ]["cash_reconciliation"]

    operating_cash_flow = _numeric_series(
        dataframe,
        "flujo_operacion_cop",
        sheet_name,
    )

    investing_cash_flow = _numeric_series(
        dataframe,
        "flujo_inversion_cop",
        sheet_name,
    )

    financing_cash_flow = _numeric_series(
        dataframe,
        "flujo_financiacion_cop",
        sheet_name,
    )

    reconciliation_adjustment = _numeric_series(
        dataframe,
        "ajuste_conciliacion_cop",
        sheet_name,
    )

    net_cash_change = _numeric_series(
        dataframe,
        "variacion_neta_efectivo_cop",
        sheet_name,
    )

    opening_cash = _numeric_series(
        dataframe,
        "efectivo_inicial_cop",
        sheet_name,
    )

    closing_cash = _numeric_series(
        dataframe,
        "efectivo_final_cop",
        sheet_name,
    )

    expected_net_cash_change = (
        operating_cash_flow
        + investing_cash_flow
        + financing_cash_flow
        + reconciliation_adjustment
    )

    net_cash_change_difference = (
        net_cash_change
        - expected_net_cash_change
    )

    _add_equation_result(
        issues=issues,
        metrics=metrics,
        sheet_name=sheet_name,
        rule="net_cash_change",
        difference=net_cash_change_difference,
        tolerance=float(rule["tolerance"]),
        severity=str(rule["severity"]),
    )

    cash_reconciliation_difference = (
        opening_cash
        + net_cash_change
        - closing_cash
    )

    _add_equation_result(
        issues=issues,
        metrics=metrics,
        sheet_name=sheet_name,
        rule="cash_reconciliation",
        difference=cash_reconciliation_difference,
        tolerance=float(rule["tolerance"]),
        severity=str(rule["severity"]),
    )

    ordered_cash_flow = (
        dataframe.sort_values("periodo")
        .reset_index(drop=True)
    )

    previous_closing_cash = pd.to_numeric(
        ordered_cash_flow[
            "efectivo_final_cop"
        ],
        errors="coerce",
    ).shift(1)

    current_opening_cash = pd.to_numeric(
        ordered_cash_flow[
            "efectivo_inicial_cop"
        ],
        errors="coerce",
    )

    continuity_mask = (
        previous_closing_cash.notna()
    )

    continuity_difference = (
        current_opening_cash.loc[
            continuity_mask
        ]
        - previous_closing_cash.loc[
            continuity_mask
        ]
    )

    _add_equation_result(
        issues=issues,
        metrics=metrics,
        sheet_name=sheet_name,
        rule="cash_continuity",
        difference=continuity_difference,
        tolerance=float(rule["tolerance"]),
        severity=str(rule["severity"]),
    )


def _validate_inventory(
    dataframe: pd.DataFrame,
    issues: list[AccountingIssue],
    metrics: dict[str, dict[str, float | int | bool]],
) -> None:
    """Valida la conciliación de unidades del inventario."""
    sheet_name = "05_Inventario"
    rule = load_quality_rules()[
        "accounting_rules"
    ]["inventory_reconciliation"]

    opening_inventory = _numeric_series(
        dataframe,
        "inventario_inicial_unidades",
        sheet_name,
    )

    purchases = _numeric_series(
        dataframe,
        "compras_unidades",
        sheet_name,
    )

    returns = _numeric_series(
        dataframe,
        "devoluciones_unidades",
        sheet_name,
    )

    adjustments = _numeric_series(
        dataframe,
        "ajustes_unidades",
        sheet_name,
    )

    sales = _numeric_series(
        dataframe,
        "ventas_unidades",
        sheet_name,
    )

    closing_inventory = _numeric_series(
        dataframe,
        "inventario_final_unidades",
        sheet_name,
    )

    inventory_difference = (
        opening_inventory
        + purchases
        + returns
        + adjustments
        - sales
        - closing_inventory
    )

    _add_equation_result(
        issues=issues,
        metrics=metrics,
        sheet_name=sheet_name,
        rule="inventory_reconciliation",
        difference=inventory_difference,
        tolerance=float(rule["tolerance"]),
        severity=str(rule["severity"]),
    )

    average_cost = _numeric_series(
        dataframe,
        "costo_promedio_cop",
        sheet_name,
    )

    recorded_inventory_value = _numeric_series(
        dataframe,
        "valor_inventario_final_cop",
        sheet_name,
    )

    inventory_value_difference = (
        recorded_inventory_value
        - (
            closing_inventory
            * average_cost
        )
    )

    _add_equation_result(
        issues=issues,
        metrics=metrics,
        sheet_name=sheet_name,
        rule="inventory_value",
        difference=inventory_value_difference,
        tolerance=1.0,
        severity="critical",
    )


def _validate_cross_statement_cash(
    balance_sheet: pd.DataFrame,
    cash_flow: pd.DataFrame,
    issues: list[AccountingIssue],
    metrics: dict[str, dict[str, float | int | bool]],
) -> None:
    """Compara el efectivo del balance y el flujo."""
    comparison = balance_sheet[
        [
            "periodo",
            "efectivo_cop",
        ]
    ].merge(
        cash_flow[
            [
                "periodo",
                "efectivo_final_cop",
            ]
        ],
        on="periodo",
        how="outer",
        validate="one_to_one",
    )

    if comparison.isna().any().any():
        raise AccountingValidationError(
            "No fue posible comparar el efectivo entre "
            "el balance general y el flujo de efectivo."
        )

    cash_difference = (
        pd.to_numeric(
            comparison["efectivo_cop"],
            errors="coerce",
        )
        - pd.to_numeric(
            comparison["efectivo_final_cop"],
            errors="coerce",
        )
    )

    _add_equation_result(
        issues=issues,
        metrics=metrics,
        sheet_name="Estados_Financieros",
        rule="cash_between_statements",
        difference=cash_difference,
        tolerance=1.0,
        severity="critical",
    )


def _validate_cross_statement_profit(
    income_statement: pd.DataFrame,
    balance_sheet: pd.DataFrame,
    cash_flow: pd.DataFrame,
    issues: list[AccountingIssue],
    metrics: dict[str, dict[str, float | int | bool]],
) -> None:
    """Compara la utilidad neta entre estados financieros."""
    comparison = income_statement[
        [
            "periodo",
            "utilidad_neta_cop",
        ]
    ].merge(
        balance_sheet[
            [
                "periodo",
                "resultado_periodo_cop",
            ]
        ],
        on="periodo",
        how="outer",
        validate="one_to_one",
    ).merge(
        cash_flow[
            [
                "periodo",
                "utilidad_neta_cop",
            ]
        ].rename(
            columns={
                "utilidad_neta_cop":
                    "utilidad_neta_flujo_cop",
            }
        ),
        on="periodo",
        how="outer",
        validate="one_to_one",
    )

    if comparison.isna().any().any():
        raise AccountingValidationError(
            "No fue posible comparar la utilidad neta "
            "entre los estados financieros."
        )

    balance_profit_difference = (
        pd.to_numeric(
            comparison["utilidad_neta_cop"],
            errors="coerce",
        )
        - pd.to_numeric(
            comparison["resultado_periodo_cop"],
            errors="coerce",
        )
    )

    _add_equation_result(
        issues=issues,
        metrics=metrics,
        sheet_name="Estados_Financieros",
        rule="profit_income_vs_balance",
        difference=balance_profit_difference,
        tolerance=1.0,
        severity="critical",
    )

    cash_flow_profit_difference = (
        pd.to_numeric(
            comparison["utilidad_neta_cop"],
            errors="coerce",
        )
        - pd.to_numeric(
            comparison[
                "utilidad_neta_flujo_cop"
            ],
            errors="coerce",
        )
    )

    _add_equation_result(
        issues=issues,
        metrics=metrics,
        sheet_name="Estados_Financieros",
        rule="profit_income_vs_cash_flow",
        difference=cash_flow_profit_difference,
        tolerance=1.0,
        severity="critical",
    )


def validate_accounting(
    file_path: Path | str,
) -> AccountingValidationResult:
    """Ejecuta la validación contable completa.

    Args:
        file_path: Ruta absoluta o relativa del libro Excel.

    Returns:
        Resultado estructurado de validación contable.

    Raises:
        AccountingValidationError: Si el libro no puede evaluarse.
    """
    resolved_path = _resolve_excel_path(
        file_path=file_path
    )

    LOGGER.info(
        "Iniciando validación contable: %s",
        resolved_path,
    )

    try:
        schema_result = validate_excel_schema(
            file_path=resolved_path
        )

    except SchemaValidationError as exc:
        raise AccountingValidationError(
            "No fue posible validar la estructura del libro."
        ) from exc

    if not schema_result.is_valid:
        raise AccountingValidationError(
            "El libro contiene errores estructurales críticos."
        )

    inventory = _load_sheet(
        file_path=resolved_path,
        sheet_name="05_Inventario",
    )

    income_statement = _load_sheet(
        file_path=resolved_path,
        sheet_name="08_Estado_Resultados",
    )

    balance_sheet = _load_sheet(
        file_path=resolved_path,
        sheet_name="09_Balance_General",
    )

    cash_flow = _load_sheet(
        file_path=resolved_path,
        sheet_name="10_Flujo_Efectivo",
    )

    issues: list[AccountingIssue] = []

    metrics: dict[
        str,
        dict[str, float | int | bool],
    ] = {}

    _validate_income_statement(
        dataframe=income_statement,
        issues=issues,
        metrics=metrics,
    )

    _validate_balance_sheet(
        dataframe=balance_sheet,
        issues=issues,
        metrics=metrics,
    )

    _validate_cash_flow(
        dataframe=cash_flow,
        issues=issues,
        metrics=metrics,
    )

    _validate_inventory(
        dataframe=inventory,
        issues=issues,
        metrics=metrics,
    )

    _validate_cross_statement_cash(
        balance_sheet=balance_sheet,
        cash_flow=cash_flow,
        issues=issues,
        metrics=metrics,
    )

    _validate_cross_statement_profit(
        income_statement=income_statement,
        balance_sheet=balance_sheet,
        cash_flow=cash_flow,
        issues=issues,
        metrics=metrics,
    )

    blocking_issue_count = sum(
        issue.severity in {
            "critical",
            "high",
        }
        for issue in issues
    )

    result = AccountingValidationResult(
        file_path=resolved_path,
        is_valid=blocking_issue_count == 0,
        issues=tuple(issues),
        metrics=metrics,
    )

    LOGGER.info(
        "Validación contable finalizada. "
        "Válido: %s. Reglas: %s. "
        "Problemas: %s. Críticos: %s.",
        result.is_valid,
        len(result.metrics),
        result.issue_count,
        result.critical_issue_count,
    )

    return result


def validate_default_raw_accounting(
) -> AccountingValidationResult:
    """Valida contablemente el libro RAW configurado."""
    settings = load_settings()
    generation_config = load_data_generation_config()

    raw_directory = resolve_project_path(
        settings["paths"]["raw_data"]
    )

    filename = generation_config[
        "output"
    ]["raw_workbook"]

    return validate_accounting(
        file_path=raw_directory / filename
    )