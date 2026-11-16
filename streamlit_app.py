"""Punto de entrada para desplegar NovaRetail en Streamlit Cloud.

Este archivo agrega la carpeta src al path de Python y ejecuta
la aplicación principal sin duplicar su lógica.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
SOURCE_DIRECTORY = PROJECT_ROOT / "src"

if str(SOURCE_DIRECTORY) not in sys.path:
    sys.path.insert(
        0,
        str(SOURCE_DIRECTORY),
    )

APPLICATION_FILE = (
    SOURCE_DIRECTORY
    / "novaretail"
    / "app"
    / "streamlit_app.py"
)

if not APPLICATION_FILE.exists():
    raise FileNotFoundError(
        "No se encontró la aplicación principal: "
        f"{APPLICATION_FILE}"
    )

runpy.run_path(
    str(APPLICATION_FILE),
    run_name="__main__",
)
