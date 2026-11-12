"""Herramientas de validación de datos de NovaRetail.

Este paquete contiene validaciones estructurales, contables,
relacionales y de calidad para los archivos sintéticos del proyecto.
"""

from __future__ import annotations

from novaretail.validation.accounting_validator import (
    AccountingIssue,
    AccountingValidationError,
    AccountingValidationResult,
    validate_accounting,
    validate_default_raw_accounting,
)
from novaretail.validation.quality_validator import (
    QualityIssue,
    QualityValidationError,
    QualityValidationResult,
    validate_data_quality,
    validate_default_raw_quality,
)
from novaretail.validation.relationship_validator import (
    RelationshipIssue,
    RelationshipValidationError,
    RelationshipValidationResult,
    validate_default_raw_relationships,
    validate_relationships,
)
from novaretail.validation.schema_validator import (
    SchemaIssue,
    SchemaValidationError,
    SchemaValidationResult,
    validate_default_raw_workbook,
    validate_excel_schema,
)


__all__ = [
    "AccountingIssue",
    "AccountingValidationError",
    "AccountingValidationResult",
    "QualityIssue",
    "QualityValidationError",
    "QualityValidationResult",
    "RelationshipIssue",
    "RelationshipValidationError",
    "RelationshipValidationResult",
    "SchemaIssue",
    "SchemaValidationError",
    "SchemaValidationResult",
    "validate_accounting",
    "validate_data_quality",
    "validate_default_raw_accounting",
    "validate_default_raw_quality",
    "validate_default_raw_relationships",
    "validate_default_raw_workbook",
    "validate_excel_schema",
    "validate_relationships",
]