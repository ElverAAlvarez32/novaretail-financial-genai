"""Paquete principal de NovaRetail Financial GenAI.

El proyecto implementa un prototipo académico para generar,
validar, analizar e interpretar datos financieros y operativos
sintéticos de una empresa ficticia de comercio electrónico.
"""

from __future__ import annotations

from novaretail.config import (
    PROJECT_ROOT,
    load_data_generation_config,
    load_financial_accounts,
    load_quality_rules,
    load_settings,
)

__version__ = "0.1.0"
__author__ = "ELVER ALIRIO ALVAREZ RAMIREZ"
__project_name__ = "NovaRetail Financial GenAI"

__all__ = [
    "PROJECT_ROOT",
    "__author__",
    "__project_name__",
    "__version__",
    "load_data_generation_config",
    "load_financial_accounts",
    "load_quality_rules",
    "load_settings",
]