"""Exportación del conjunto sintético NovaRetail a Excel."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

from novaretail.config import (
    load_data_generation_config,
    load_settings,
    resolve_project_path,
)
from novaretail.generation.generator import GeneratedData
from novaretail.logging_config import get_logger


LOGGER = get_logger(__name__)

HEADER_FILL = PatternFill(
    fill_type="solid",
    fgColor="17365D",
)

HEADER_FONT = Font(
    color="FFFFFF",
    bold=True,
)

SYNTHETIC_FILL = PatternFill(
    fill_type="solid",
    fgColor="FFF2CC",
)

CONTROL_FILL = PatternFill(
    fill_type="solid",
    fgColor="D9EAF7",
)

WARNING_FILL = PatternFill(
    fill_type="solid",
    fgColor="F4B183",
)


class ExcelExportError(RuntimeError):
    """Error producido durante la exportación a Excel."""


def _sanitize_table_name(sheet_name: str) -> str:
    """Crea un nombre válido para una tabla de Excel."""
    sanitized = "".join(
        character if character.isalnum() else "_"
        for character in sheet_name
    )

    if not sanitized:
        sanitized = "Datos"

    return f"Tabla_{sanitized}"[:250]


def _calculate_column_width(
    dataframe: pd.DataFrame,
    column_name: str,
) -> int:
    """Calcula un ancho legible para una columna."""
    maximum_length = len(str(column_name))

    for value in dataframe[column_name]:
        if pd.isna(value):
            continue

        maximum_length = max(
            maximum_length,
            len(str(value)),
        )

    return min(
        max(maximum_length + 2, 10),
        45,
    )


def _format_header(worksheet) -> None:
    """Aplica formato a los encabezados."""
    for cell in worksheet[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(
            horizontal="center",
            vertical="center",
            wrap_text=True,
        )

    worksheet.row_dimensions[1].height = 32


def _format_data_cells(worksheet) -> None:
    """Aplica alineación a las celdas de datos."""
    for row in worksheet.iter_rows(
        min_row=2,
        max_row=worksheet.max_row,
    ):
        for cell in row:
            cell.alignment = Alignment(
                vertical="center",
            )

            if isinstance(cell.value, bool):
                cell.alignment = Alignment(
                    horizontal="center",
                    vertical="center",
                )


def _format_columns(
    worksheet,
    dataframe: pd.DataFrame,
) -> None:
    """Aplica anchos y formatos numéricos."""
    percentage_columns = {
        "margen_objetivo",
        "descuento_rate",
        "tasa_clics",
        "tasa_conversion",
        "margen_bruto",
        "margen_operacional",
        "margen_neto",
        "variacion_porcentual",
    }

    for position, column_name in enumerate(
        dataframe.columns,
        start=1,
    ):
        column_letter = get_column_letter(position)

        worksheet.column_dimensions[
            column_letter
        ].width = _calculate_column_width(
            dataframe=dataframe,
            column_name=str(column_name),
        )

        for row_number in range(
            2,
            worksheet.max_row + 1,
        ):
            cell = worksheet.cell(
                row=row_number,
                column=position,
            )

            if str(column_name).endswith("_cop"):
                cell.number_format = "#,##0"

            elif column_name in percentage_columns:
                cell.number_format = "0.00%"

            elif column_name == "retorno_publicitario":
                cell.number_format = "0.00"


def _highlight_synthetic_column(
    worksheet,
    dataframe: pd.DataFrame,
) -> None:
    """Destaca la columna que identifica datos sintéticos."""
    if "datos_sinteticos" not in dataframe.columns:
        return

    position = (
        dataframe.columns.get_loc(
            "datos_sinteticos"
        )
        + 1
    )

    for row_number in range(
        2,
        worksheet.max_row + 1,
    ):
        worksheet.cell(
            row=row_number,
            column=position,
        ).fill = SYNTHETIC_FILL


def _add_excel_table(
    worksheet,
    sheet_name: str,
) -> None:
    """Convierte los datos de una hoja en tabla de Excel."""
    if worksheet.max_row < 2:
        return

    final_column = get_column_letter(
        worksheet.max_column
    )

    table_reference = (
        f"A1:{final_column}{worksheet.max_row}"
    )

    excel_table = Table(
        displayName=_sanitize_table_name(
            sheet_name
        ),
        ref=table_reference,
    )

    excel_table.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium2",
        showFirstColumn=False,
        showLastColumn=False,
        showRowStripes=True,
        showColumnStripes=False,
    )

    worksheet.add_table(excel_table)


def _format_control_sheet(worksheet) -> None:
    """Aplica formato especial a la hoja de control."""
    for row_number in range(
        2,
        worksheet.max_row + 1,
    ):
        label_cell = worksheet.cell(
            row=row_number,
            column=1,
        )

        value_cell = worksheet.cell(
            row=row_number,
            column=2,
        )

        label_cell.fill = CONTROL_FILL
        label_cell.font = Font(bold=True)

        if label_cell.value == "advertencia":
            label_cell.fill = WARNING_FILL
            value_cell.fill = WARNING_FILL
            value_cell.font = Font(bold=True)
            value_cell.alignment = Alignment(
                vertical="center",
                wrap_text=True,
            )

            worksheet.row_dimensions[
                row_number
            ].height = 60


def _format_worksheet(
    worksheet,
    dataframe: pd.DataFrame,
    sheet_name: str,
) -> None:
    """Aplica formato completo a una hoja."""
    worksheet.freeze_panes = "A2"
    worksheet.sheet_view.showGridLines = False

    _format_header(worksheet)
    _format_data_cells(worksheet)

    _format_columns(
        worksheet=worksheet,
        dataframe=dataframe,
    )

    _highlight_synthetic_column(
        worksheet=worksheet,
        dataframe=dataframe,
    )

    _add_excel_table(
        worksheet=worksheet,
        sheet_name=sheet_name,
    )

    if sheet_name == "00_Control":
        _format_control_sheet(worksheet)


def _validate_generated_data(
    generated_data: GeneratedData,
) -> None:
    """Valida que todas las tablas puedan exportarse."""
    tables = generated_data.as_dict()

    if len(tables) != 12:
        raise ExcelExportError(
            "Se esperaban exactamente doce tablas."
        )

    for sheet_name, dataframe in tables.items():
        if not isinstance(dataframe, pd.DataFrame):
            raise ExcelExportError(
                f"{sheet_name} no es un DataFrame."
            )

        if dataframe.empty:
            raise ExcelExportError(
                f"{sheet_name} está vacía."
            )

        if len(sheet_name) > 31:
            raise ExcelExportError(
                f"Nombre de hoja demasiado largo: {sheet_name}"
            )


def export_to_excel(
    generated_data: GeneratedData,
    output_path: Path | str | None = None,
) -> Path:
    """Exporta las doce tablas a un libro Excel.

    Args:
        generated_data: Contenedor maestro de datos.
        output_path: Ruta opcional del archivo.

    Returns:
        Ruta absoluta del archivo creado.
    """
    _validate_generated_data(generated_data)

    settings = load_settings()
    generation_config = load_data_generation_config()

    if output_path is None:
        output_directory = resolve_project_path(
            settings["paths"]["raw_data"]
        )

        filename = generation_config[
            "output"
        ]["raw_workbook"]

        final_path = output_directory / filename

    else:
        final_path = Path(output_path)

        if not final_path.is_absolute():
            final_path = resolve_project_path(
                str(final_path)
            )

    if final_path.suffix.lower() != ".xlsx":
        raise ExcelExportError(
            "El archivo debe tener extensión .xlsx."
        )

    final_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    LOGGER.info(
        "Iniciando exportación a Excel: %s",
        final_path,
    )

    try:
        with pd.ExcelWriter(
            final_path,
            engine="openpyxl",
        ) as writer:
            for sheet_name, dataframe in (
                generated_data.iter_tables()
            ):
                dataframe.to_excel(
                    writer,
                    sheet_name=sheet_name,
                    index=False,
                )

        workbook = load_workbook(final_path)

        for sheet_name, dataframe in (
            generated_data.iter_tables()
        ):
            worksheet = workbook[sheet_name]

            _format_worksheet(
                worksheet=worksheet,
                dataframe=dataframe,
                sheet_name=sheet_name,
            )

        workbook.properties.title = (
            "NovaRetail Financial GenAI - Datos RAW"
        )

        workbook.properties.subject = (
            "Datos sintéticos financieros y operativos"
        )

        workbook.properties.creator = (
            settings["project"]["owner"]
        )

        workbook.properties.description = (
            "Datos sintéticos de NovaRetail Colombia S.A.S."
        )

        workbook.save(final_path)

    except Exception as exc:
        raise ExcelExportError(
            "No fue posible exportar el libro Excel."
        ) from exc

    if not final_path.exists():
        raise ExcelExportError(
            "El archivo Excel no fue creado."
        )

    if final_path.stat().st_size == 0:
        raise ExcelExportError(
            "El archivo Excel creado está vacío."
        )

    LOGGER.info(
        "Libro Excel exportado correctamente: %s",
        final_path,
    )

    return final_path

