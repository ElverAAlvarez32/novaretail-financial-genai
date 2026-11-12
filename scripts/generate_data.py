"""Punto de entrada para generar el conjunto sintético NovaRetail.

Este script ejecuta la generación maestra y exporta las doce tablas
al archivo Excel RAW definido en config/data_generation.yaml.
"""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRECTORY = PROJECT_ROOT / "src"

if str(SOURCE_DIRECTORY) not in sys.path:
    sys.path.insert(
        0,
        str(SOURCE_DIRECTORY),
    )


from novaretail.generation import generate_all_data
from novaretail.logging_config import get_logger
from novaretail.reporting import (
    ExcelExportError,
    export_to_excel,
)


LOGGER = get_logger("scripts.generate_data")


def main() -> int:
    """Genera y exporta el conjunto completo de datos sintéticos.

    Returns:
        Código de salida del proceso:
        0 cuando la generación finaliza correctamente.
        1 cuando ocurre un error controlado.
    """
    LOGGER.info(
        "Inicio del proceso completo de generación de datos."
    )

    try:
        generated_data = generate_all_data()

        output_path = export_to_excel(
            generated_data=generated_data
        )

    except (
        ExcelExportError,
        OSError,
        RuntimeError,
        ValueError,
        KeyError,
    ) as exc:
        LOGGER.exception(
            "El proceso de generación no pudo completarse: %s",
            exc,
        )

        return 1

    print()
    print("=" * 70)
    print("GENERACIÓN COMPLETADA")
    print("=" * 70)
    print(f"Archivo: {output_path}")
    print(f"Tamaño: {output_path.stat().st_size:,} bytes")
    print("Naturaleza: datos completamente sintéticos")
    print("Uso: exclusivamente académico")
    print()
    print("Resumen de registros:")

    for table_name, row_count in (
        generated_data.row_summary().items()
    ):
        print(
            f"  {table_name}: {row_count:,}"
        )

    print("=" * 70)

    LOGGER.info(
        "Proceso completo finalizado correctamente."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())