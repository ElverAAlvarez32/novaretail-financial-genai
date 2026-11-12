"""Herramientas de reportes y exportación de NovaRetail.

Este paquete contiene funciones para generar archivos, gráficos
e informes a partir de los datos sintéticos del proyecto.
"""

from __future__ import annotations

from novaretail.reporting.excel_report import (
    ExcelExportError,
    export_to_excel,
)


__all__ = [
    "ExcelExportError",
    "export_to_excel",
]