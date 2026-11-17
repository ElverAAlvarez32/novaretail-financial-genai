"""Carga y validación básica de la configuración del proyecto.

Este módulo centraliza la lectura de archivos YAML y variables de entorno.
Las rutas se resuelven desde la raíz del proyecto para evitar dependencias
del directorio desde el cual se ejecuten los scripts.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"

SETTINGS_FILE = CONFIG_DIR / "settings.yaml"
DATA_GENERATION_FILE = CONFIG_DIR / "data_generation.yaml"
FINANCIAL_ACCOUNTS_FILE = CONFIG_DIR / "financial_accounts.yaml"
QUALITY_RULES_FILE = CONFIG_DIR / "quality_rules.yaml"


class ConfigurationError(RuntimeError):
    """Error producido por una configuración ausente o inválida."""


def _load_yaml(file_path: Path) -> dict[str, Any]:
    """Carga un archivo YAML y devuelve su contenido como diccionario.

    Args:
        file_path: Ruta absoluta del archivo YAML.

    Returns:
        Diccionario con la configuración cargada.

    Raises:
        ConfigurationError: Si el archivo no existe, está vacío,
            contiene una raíz diferente de un diccionario o tiene
            sintaxis YAML inválida.
    """
    if not file_path.exists():
        raise ConfigurationError(
            f"No se encontró el archivo de configuración: {file_path}"
        )

    try:
        with file_path.open("r", encoding="utf-8") as yaml_file:
            content = yaml.safe_load(yaml_file)
    except yaml.YAMLError as exc:
        raise ConfigurationError(
            f"El archivo YAML contiene errores: {file_path}"
        ) from exc
    except OSError as exc:
        raise ConfigurationError(
            f"No fue posible leer el archivo: {file_path}"
        ) from exc

    if content is None:
        raise ConfigurationError(
            f"El archivo de configuración está vacío: {file_path}"
        )

    if not isinstance(content, dict):
        raise ConfigurationError(
            "La raíz de la configuración debe ser un diccionario: "
            f"{file_path}"
        )

    return content


def _require_keys(
    configuration: dict[str, Any],
    required_keys: tuple[str, ...],
    configuration_name: str,
) -> None:
    """Verifica la existencia de secciones obligatorias.

    Args:
        configuration: Configuración que se validará.
        required_keys: Claves obligatorias de primer nivel.
        configuration_name: Nombre legible de la configuración.

    Raises:
        ConfigurationError: Si falta una sección obligatoria.
    """
    missing_keys = [
        key for key in required_keys if key not in configuration
    ]

    if missing_keys:
        missing_text = ", ".join(missing_keys)
        raise ConfigurationError(
            f"Faltan secciones en {configuration_name}: {missing_text}"
        )


@lru_cache(maxsize=1)
def load_settings() -> dict[str, Any]:
    """Carga y valida la configuración general."""
    settings = _load_yaml(SETTINGS_FILE)
    _require_keys(
        settings,
        (
            "project",
            "company",
            "financial",
            "period",
            "paths",
            "logging",
            "ai",
            "application",
        ),
        "settings.yaml",
    )
    return settings


@lru_cache(maxsize=1)
def load_data_generation_config() -> dict[str, Any]:
    """Carga y valida los parámetros de generación sintética."""
    configuration = _load_yaml(DATA_GENERATION_FILE)
    _require_keys(
        configuration,
        (
            "generation",
            "period",
            "company",
            "volumes",
            "product_catalog",
            "customer_segments",
            "sales",
            "pricing",
            "operations",
            "marketing",
            "finance",
            "quality_cases",
            "output",
        ),
        "data_generation.yaml",
    )
    return configuration


@lru_cache(maxsize=1)
def load_financial_accounts() -> dict[str, Any]:
    """Carga y valida el catálogo conceptual de cuentas financieras."""
    configuration = _load_yaml(FINANCIAL_ACCOUNTS_FILE)
    _require_keys(
        configuration,
        (
            "metadata",
            "income_statement",
            "balance_sheet",
            "cash_flow",
        ),
        "financial_accounts.yaml",
    )
    return configuration


@lru_cache(maxsize=1)
def load_quality_rules() -> dict[str, Any]:
    """Carga y valida las reglas de calidad de datos."""
    configuration = _load_yaml(QUALITY_RULES_FILE)
    _require_keys(
        configuration,
        (
            "metadata",
            "severity_levels",
            "general_rules",
            "identifier_rules",
            "date_rules",
            "numeric_rules",
            "relationship_rules",
            "accounting_rules",
            "missing_value_rules",
            "duplicate_rules",
            "outlier_rules",
            "cleaning_rules",
            "quality_log",
        ),
        "quality_rules.yaml",
    )
    return configuration


def resolve_project_path(relative_path: str) -> Path:
    """Convierte una ruta relativa en una ruta absoluta del proyecto.

    Args:
        relative_path: Ruta relativa definida en la configuración.

    Returns:
        Ruta absoluta resuelta.
    """
    path = Path(relative_path)

    if path.is_absolute():
        return path

    return PROJECT_ROOT / path


def clear_configuration_cache() -> None:
    """Limpia la caché de configuración para pruebas o recargas."""
    load_settings.cache_clear()
    load_data_generation_config.cache_clear()
    load_financial_accounts.cache_clear()
    load_quality_rules.cache_clear()