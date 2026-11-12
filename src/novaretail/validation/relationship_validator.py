"""Validación de relaciones entre las tablas de NovaRetail.

Este módulo comprueba la integridad referencial entre productos,
clientes, pedidos, devoluciones e inventario.

La validación no modifica el archivo analizado. Todos los datos
pertenecen a una empresa ficticia y se utilizan con fines académicos.
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
from novaretail.logging_config import get_logger
from novaretail.validation.schema_validator import (
    SchemaValidationError,
    validate_excel_schema,
)


LOGGER = get_logger(__name__)


@dataclass(frozen=True)
class RelationshipIssue:
    """Representa un problema de integridad referencial."""

    relationship_name: str
    child_sheet: str
    parent_sheet: str
    child_key: str
    parent_key: str
    severity: str
    affected_records: int
    message: str


@dataclass(frozen=True)
class RelationshipValidationResult:
    """Resultado completo de la validación de relaciones."""

    file_path: Path
    is_valid: bool
    issues: tuple[RelationshipIssue, ...]
    metrics: dict[str, dict[str, int | bool | str]]

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
    def affected_record_count(self) -> int:
        """Devuelve el total de registros afectados."""
        return sum(
            issue.affected_records
            for issue in self.issues
        )

    def to_dataframe(self) -> pd.DataFrame:
        """Convierte los problemas relacionales en una tabla."""
        records = [
            {
                "relacion": issue.relationship_name,
                "tabla_hija": issue.child_sheet,
                "tabla_padre": issue.parent_sheet,
                "clave_hija": issue.child_key,
                "clave_padre": issue.parent_key,
                "severidad": issue.severity,
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
                "relacion",
                "tabla_hija",
                "tabla_padre",
                "clave_hija",
                "clave_padre",
                "severidad",
                "registros_afectados",
                "mensaje",
            ],
        )


class RelationshipValidationError(RuntimeError):
    """Error durante la validación de relaciones."""


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
        raise RelationshipValidationError(
            "El archivo debe tener extensión .xlsx."
        )

    if not resolved_path.exists():
        raise RelationshipValidationError(
            f"No se encontró el archivo: {resolved_path}"
        )

    if not resolved_path.is_file():
        raise RelationshipValidationError(
            "La ruta suministrada no corresponde a un archivo."
        )

    if resolved_path.stat().st_size == 0:
        raise RelationshipValidationError(
            "El archivo Excel está vacío."
        )

    return resolved_path


def _load_sheet(
    file_path: Path,
    sheet_name: str,
) -> pd.DataFrame:
    """Carga una hoja del libro Excel."""
    try:
        return pd.read_excel(
            file_path,
            sheet_name=sheet_name,
            engine="openpyxl",
        )

    except Exception as exc:
        raise RelationshipValidationError(
            f"No fue posible leer la hoja {sheet_name}."
        ) from exc


def _require_column(
    dataframe: pd.DataFrame,
    sheet_name: str,
    column_name: str,
) -> None:
    """Comprueba que una columna exista."""
    if column_name not in dataframe.columns:
        raise RelationshipValidationError(
            f"Falta la columna {column_name} "
            f"en la hoja {sheet_name}."
        )


def _normalize_identifier_series(
    dataframe: pd.DataFrame,
    sheet_name: str,
    column_name: str,
) -> pd.Series:
    """Normaliza una columna de identificadores."""
    _require_column(
        dataframe=dataframe,
        sheet_name=sheet_name,
        column_name=column_name,
    )

    return (
        dataframe[column_name]
        .dropna()
        .astype(str)
        .str.strip()
    )


def _add_relationship_issue(
    issues: list[RelationshipIssue],
    relationship_name: str,
    child_sheet: str,
    parent_sheet: str,
    child_key: str,
    parent_key: str,
    severity: str,
    affected_records: int,
    message: str,
) -> None:
    """Agrega un problema de relación."""
    issues.append(
        RelationshipIssue(
            relationship_name=relationship_name,
            child_sheet=child_sheet,
            parent_sheet=parent_sheet,
            child_key=child_key,
            parent_key=parent_key,
            severity=severity,
            affected_records=affected_records,
            message=message,
        )
    )


def _validate_foreign_key(
    relationship_name: str,
    child_sheet: str,
    child_dataframe: pd.DataFrame,
    child_key: str,
    parent_sheet: str,
    parent_dataframe: pd.DataFrame,
    parent_key: str,
    severity: str,
    issues: list[RelationshipIssue],
    metrics: dict[
        str,
        dict[str, int | bool | str],
    ],
) -> None:
    """Valida una clave foránea entre dos tablas."""
    _require_column(
        dataframe=child_dataframe,
        sheet_name=child_sheet,
        column_name=child_key,
    )

    _require_column(
        dataframe=parent_dataframe,
        sheet_name=parent_sheet,
        column_name=parent_key,
    )

    child_values = (
        child_dataframe[child_key]
        .astype("string")
        .str.strip()
    )

    parent_values = set(
        _normalize_identifier_series(
            dataframe=parent_dataframe,
            sheet_name=parent_sheet,
            column_name=parent_key,
        )
    )

    null_mask = child_values.isna()

    orphan_mask = (
        child_values.notna()
        & ~child_values.isin(parent_values)
    )

    null_count = int(
        null_mask.sum()
    )

    orphan_count = int(
        orphan_mask.sum()
    )

    affected_records = (
        null_count + orphan_count
    )

    metrics[relationship_name] = {
        "registros_hijos": len(
            child_dataframe
        ),
        "claves_padre_unicas": len(
            parent_values
        ),
        "claves_hijas_nulas": null_count,
        "registros_huerfanos": orphan_count,
        "registros_afectados": affected_records,
        "cumple": affected_records == 0,
    }

    if null_count > 0:
        _add_relationship_issue(
            issues=issues,
            relationship_name=relationship_name,
            child_sheet=child_sheet,
            parent_sheet=parent_sheet,
            child_key=child_key,
            parent_key=parent_key,
            severity=severity,
            affected_records=null_count,
            message=(
                f"La clave hija {child_key} contiene "
                f"{null_count} valores nulos."
            ),
        )

    if orphan_count > 0:
        orphan_examples = (
            child_values.loc[
                orphan_mask
            ]
            .drop_duplicates()
            .head(5)
            .tolist()
        )

        examples_text = ", ".join(
            str(value)
            for value in orphan_examples
        )

        _add_relationship_issue(
            issues=issues,
            relationship_name=relationship_name,
            child_sheet=child_sheet,
            parent_sheet=parent_sheet,
            child_key=child_key,
            parent_key=parent_key,
            severity=severity,
            affected_records=orphan_count,
            message=(
                f"Se detectaron {orphan_count} registros "
                f"sin correspondencia en {parent_sheet}. "
                f"Ejemplos: {examples_text}."
            ),
        )


def _validate_returned_order_lines(
    orders: pd.DataFrame,
    returns: pd.DataFrame,
    issues: list[RelationshipIssue],
    metrics: dict[
        str,
        dict[str, int | bool | str],
    ],
) -> None:
    """Comprueba que las devoluciones provengan de líneas devueltas."""
    relationship_name = (
        "devoluciones_linea_devuelta"
    )

    required_order_columns = {
        "linea_pedido_id",
        "estado_pedido",
        "devolucion",
    }

    required_return_columns = {
        "linea_pedido_id",
    }

    missing_order_columns = (
        required_order_columns.difference(
            orders.columns
        )
    )

    missing_return_columns = (
        required_return_columns.difference(
            returns.columns
        )
    )

    if missing_order_columns:
        missing_text = ", ".join(
            sorted(missing_order_columns)
        )

        raise RelationshipValidationError(
            f"Faltan columnas en 04_Pedidos: "
            f"{missing_text}"
        )

    if missing_return_columns:
        missing_text = ", ".join(
            sorted(missing_return_columns)
        )

        raise RelationshipValidationError(
            f"Faltan columnas en 06_Devoluciones: "
            f"{missing_text}"
        )

    returned_order_lines = orders[
        (orders["estado_pedido"] == "Devuelto")
        & (orders["devolucion"].astype(bool))
    ][
        "linea_pedido_id"
    ].astype(str)

    valid_returned_line_ids = set(
        returned_order_lines
    )

    return_line_ids = (
        returns["linea_pedido_id"]
        .astype("string")
        .str.strip()
    )

    invalid_mask = (
        return_line_ids.notna()
        & ~return_line_ids.isin(
            valid_returned_line_ids
        )
    )

    invalid_count = int(
        invalid_mask.sum()
    )

    missing_return_records = len(
        valid_returned_line_ids.difference(
            set(
                return_line_ids.dropna()
            )
        )
    )

    metrics[relationship_name] = {
        "lineas_marcadas_devueltas": len(
            valid_returned_line_ids
        ),
        "registros_devolucion": len(
            returns
        ),
        "devoluciones_sin_estado_devuelto": (
            invalid_count
        ),
        "lineas_devueltas_sin_registro": (
            missing_return_records
        ),
        "registros_afectados": (
            invalid_count
            + missing_return_records
        ),
        "cumple": (
            invalid_count == 0
            and missing_return_records == 0
        ),
    }

    if invalid_count > 0:
        _add_relationship_issue(
            issues=issues,
            relationship_name=relationship_name,
            child_sheet="06_Devoluciones",
            parent_sheet="04_Pedidos",
            child_key="linea_pedido_id",
            parent_key="linea_pedido_id",
            severity="critical",
            affected_records=invalid_count,
            message=(
                f"Se encontraron {invalid_count} "
                "devoluciones asociadas a líneas que no "
                "tienen estado Devuelto."
            ),
        )

    if missing_return_records > 0:
        _add_relationship_issue(
            issues=issues,
            relationship_name=relationship_name,
            child_sheet="04_Pedidos",
            parent_sheet="06_Devoluciones",
            child_key="linea_pedido_id",
            parent_key="linea_pedido_id",
            severity="critical",
            affected_records=missing_return_records,
            message=(
                f"Se encontraron {missing_return_records} "
                "líneas devueltas sin registro en la tabla "
                "de devoluciones."
            ),
        )


def _validate_return_attributes(
    orders: pd.DataFrame,
    returns: pd.DataFrame,
    issues: list[RelationshipIssue],
    metrics: dict[
        str,
        dict[str, int | bool | str],
    ],
) -> None:
    """Compara pedido, cliente y producto de cada devolución."""
    relationship_name = (
        "atributos_devolucion_pedido"
    )

    required_columns = [
        "linea_pedido_id",
        "pedido_id",
        "cliente_id",
        "producto_id",
    ]

    for column_name in required_columns:
        _require_column(
            dataframe=orders,
            sheet_name="04_Pedidos",
            column_name=column_name,
        )

        _require_column(
            dataframe=returns,
            sheet_name="06_Devoluciones",
            column_name=column_name,
        )

    order_reference = orders[
        required_columns
    ].copy()

    order_reference = (
        order_reference.drop_duplicates(
            subset=["linea_pedido_id"]
        )
        .rename(
            columns={
                "pedido_id":
                    "pedido_id_orden",
                "cliente_id":
                    "cliente_id_orden",
                "producto_id":
                    "producto_id_orden",
            }
        )
    )

    comparison = returns[
        required_columns
    ].merge(
        order_reference,
        on="linea_pedido_id",
        how="left",
        validate="one_to_one",
    )

    mismatch_mask = (
        comparison["pedido_id"]
        != comparison["pedido_id_orden"]
    ) | (
        comparison["cliente_id"]
        != comparison["cliente_id_orden"]
    ) | (
        comparison["producto_id"]
        != comparison["producto_id_orden"]
    )

    mismatch_count = int(
        mismatch_mask.sum()
    )

    metrics[relationship_name] = {
        "registros_evaluados": len(
            comparison
        ),
        "registros_inconsistentes": (
            mismatch_count
        ),
        "registros_afectados": mismatch_count,
        "cumple": mismatch_count == 0,
    }

    if mismatch_count > 0:
        _add_relationship_issue(
            issues=issues,
            relationship_name=relationship_name,
            child_sheet="06_Devoluciones",
            parent_sheet="04_Pedidos",
            child_key="linea_pedido_id",
            parent_key="linea_pedido_id",
            severity="critical",
            affected_records=mismatch_count,
            message=(
                f"Se detectaron {mismatch_count} "
                "devoluciones cuyos datos de pedido, cliente "
                "o producto no coinciden con la línea original."
            ),
        )


def _validate_inventory_category(
    products: pd.DataFrame,
    inventory: pd.DataFrame,
    issues: list[RelationshipIssue],
    metrics: dict[
        str,
        dict[str, int | bool | str],
    ],
) -> None:
    """Comprueba la categoría del inventario frente al catálogo."""
    relationship_name = (
        "inventario_categoria_producto"
    )

    _require_column(
        dataframe=products,
        sheet_name="02_Productos",
        column_name="producto_id",
    )

    _require_column(
        dataframe=products,
        sheet_name="02_Productos",
        column_name="categoria",
    )

    _require_column(
        dataframe=inventory,
        sheet_name="05_Inventario",
        column_name="producto_id",
    )

    _require_column(
        dataframe=inventory,
        sheet_name="05_Inventario",
        column_name="categoria",
    )

    product_reference = products[
        [
            "producto_id",
            "categoria",
        ]
    ].rename(
        columns={
            "categoria":
                "categoria_producto",
        }
    )

    comparison = inventory[
        [
            "producto_id",
            "categoria",
        ]
    ].merge(
        product_reference,
        on="producto_id",
        how="left",
        validate="many_to_one",
    )

    mismatch_mask = (
        comparison["categoria"]
        != comparison["categoria_producto"]
    )

    mismatch_count = int(
        mismatch_mask.sum()
    )

    metrics[relationship_name] = {
        "registros_evaluados": len(
            comparison
        ),
        "categorias_inconsistentes": (
            mismatch_count
        ),
        "registros_afectados": mismatch_count,
        "cumple": mismatch_count == 0,
    }

    if mismatch_count > 0:
        _add_relationship_issue(
            issues=issues,
            relationship_name=relationship_name,
            child_sheet="05_Inventario",
            parent_sheet="02_Productos",
            child_key="producto_id",
            parent_key="producto_id",
            severity="high",
            affected_records=mismatch_count,
            message=(
                f"Se detectaron {mismatch_count} registros "
                "de inventario con una categoría diferente "
                "a la categoría del producto."
            ),
        )


def _validate_order_attributes(
    products: pd.DataFrame,
    customers: pd.DataFrame,
    orders: pd.DataFrame,
    issues: list[RelationshipIssue],
    metrics: dict[
        str,
        dict[str, int | bool | str],
    ],
) -> None:
    """Compara atributos heredados por los pedidos."""
    relationship_name = (
        "atributos_pedido_maestros"
    )

    product_reference = products[
        [
            "producto_id",
            "categoria",
        ]
    ].rename(
        columns={
            "categoria":
                "categoria_producto",
        }
    )

    customer_reference = customers[
        [
            "cliente_id",
            "ciudad",
            "departamento",
        ]
    ].rename(
        columns={
            "ciudad": "ciudad_cliente",
            "departamento":
                "departamento_cliente",
        }
    )

    comparison = orders[
        [
            "linea_pedido_id",
            "producto_id",
            "cliente_id",
            "categoria",
            "ciudad",
            "departamento",
        ]
    ].merge(
        product_reference,
        on="producto_id",
        how="left",
        validate="many_to_one",
    ).merge(
        customer_reference,
        on="cliente_id",
        how="left",
        validate="many_to_one",
    )

    mismatch_mask = (
        (
            comparison["categoria"]
            != comparison["categoria_producto"]
        )
        | (
            comparison["ciudad"]
            != comparison["ciudad_cliente"]
        )
        | (
            comparison["departamento"]
            != comparison[
                "departamento_cliente"
            ]
        )
    )

    mismatch_count = int(
        mismatch_mask.sum()
    )

    metrics[relationship_name] = {
        "registros_evaluados": len(
            comparison
        ),
        "atributos_inconsistentes": (
            mismatch_count
        ),
        "registros_afectados": mismatch_count,
        "cumple": mismatch_count == 0,
    }

    if mismatch_count > 0:
        _add_relationship_issue(
            issues=issues,
            relationship_name=relationship_name,
            child_sheet="04_Pedidos",
            parent_sheet=(
                "02_Productos y 03_Clientes"
            ),
            child_key=(
                "producto_id y cliente_id"
            ),
            parent_key=(
                "producto_id y cliente_id"
            ),
            severity="high",
            affected_records=mismatch_count,
            message=(
                f"Se detectaron {mismatch_count} pedidos "
                "con categoría, ciudad o departamento "
                "diferentes de las tablas maestras."
            ),
        )


def validate_relationships(
    file_path: Path | str,
) -> RelationshipValidationResult:
    """Ejecuta la validación completa de relaciones.

    Args:
        file_path: Ruta absoluta o relativa del libro Excel.

    Returns:
        Resultado estructurado de integridad referencial.

    Raises:
        RelationshipValidationError: Si el libro no puede evaluarse.
    """
    resolved_path = _resolve_excel_path(
        file_path=file_path
    )

    LOGGER.info(
        "Iniciando validación de relaciones: %s",
        resolved_path,
    )

    try:
        schema_result = validate_excel_schema(
            file_path=resolved_path
        )

    except SchemaValidationError as exc:
        raise RelationshipValidationError(
            "No fue posible validar la estructura del libro."
        ) from exc

    if not schema_result.is_valid:
        raise RelationshipValidationError(
            "El libro contiene errores estructurales críticos."
        )

    products = _load_sheet(
        file_path=resolved_path,
        sheet_name="02_Productos",
    )

    customers = _load_sheet(
        file_path=resolved_path,
        sheet_name="03_Clientes",
    )

    orders = _load_sheet(
        file_path=resolved_path,
        sheet_name="04_Pedidos",
    )

    inventory = _load_sheet(
        file_path=resolved_path,
        sheet_name="05_Inventario",
    )

    returns = _load_sheet(
        file_path=resolved_path,
        sheet_name="06_Devoluciones",
    )

    relationship_rules = load_quality_rules()[
        "relationship_rules"
    ]

    issues: list[RelationshipIssue] = []

    metrics: dict[
        str,
        dict[str, int | bool | str],
    ] = {}

    _validate_foreign_key(
        relationship_name="pedidos_producto",
        child_sheet="04_Pedidos",
        child_dataframe=orders,
        child_key="producto_id",
        parent_sheet="02_Productos",
        parent_dataframe=products,
        parent_key="producto_id",
        severity=str(
            relationship_rules[
                "pedidos_producto"
            ]["severity"]
        ),
        issues=issues,
        metrics=metrics,
    )

    _validate_foreign_key(
        relationship_name="pedidos_cliente",
        child_sheet="04_Pedidos",
        child_dataframe=orders,
        child_key="cliente_id",
        parent_sheet="03_Clientes",
        parent_dataframe=customers,
        parent_key="cliente_id",
        severity=str(
            relationship_rules[
                "pedidos_cliente"
            ]["severity"]
        ),
        issues=issues,
        metrics=metrics,
    )

    _validate_foreign_key(
        relationship_name="devoluciones_pedido",
        child_sheet="06_Devoluciones",
        child_dataframe=returns,
        child_key="pedido_id",
        parent_sheet="04_Pedidos",
        parent_dataframe=orders,
        parent_key="pedido_id",
        severity=str(
            relationship_rules[
                "devoluciones_pedido"
            ]["severity"]
        ),
        issues=issues,
        metrics=metrics,
    )

    _validate_foreign_key(
        relationship_name="devoluciones_linea_pedido",
        child_sheet="06_Devoluciones",
        child_dataframe=returns,
        child_key="linea_pedido_id",
        parent_sheet="04_Pedidos",
        parent_dataframe=orders,
        parent_key="linea_pedido_id",
        severity="critical",
        issues=issues,
        metrics=metrics,
    )

    _validate_foreign_key(
        relationship_name="inventario_producto",
        child_sheet="05_Inventario",
        child_dataframe=inventory,
        child_key="producto_id",
        parent_sheet="02_Productos",
        parent_dataframe=products,
        parent_key="producto_id",
        severity=str(
            relationship_rules[
                "inventario_producto"
            ]["severity"]
        ),
        issues=issues,
        metrics=metrics,
    )

    _validate_returned_order_lines(
        orders=orders,
        returns=returns,
        issues=issues,
        metrics=metrics,
    )

    _validate_return_attributes(
        orders=orders,
        returns=returns,
        issues=issues,
        metrics=metrics,
    )

    _validate_inventory_category(
        products=products,
        inventory=inventory,
        issues=issues,
        metrics=metrics,
    )

    _validate_order_attributes(
        products=products,
        customers=customers,
        orders=orders,
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

    result = RelationshipValidationResult(
        file_path=resolved_path,
        is_valid=blocking_issue_count == 0,
        issues=tuple(issues),
        metrics=metrics,
    )

    LOGGER.info(
        "Validación de relaciones finalizada. "
        "Válido: %s. Relaciones: %s. "
        "Problemas: %s. Críticos: %s.",
        result.is_valid,
        len(result.metrics),
        result.issue_count,
        result.critical_issue_count,
    )

    return result


def validate_default_raw_relationships(
) -> RelationshipValidationResult:
    """Valida las relaciones del libro RAW configurado."""
    settings = load_settings()
    generation_config = load_data_generation_config()

    raw_directory = resolve_project_path(
        settings["paths"]["raw_data"]
    )

    filename = generation_config[
        "output"
    ]["raw_workbook"]

    return validate_relationships(
        file_path=raw_directory / filename
    )