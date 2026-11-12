"""Pruebas automáticas del exportador de datos sintéticos a Excel."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from openpyxl import load_workbook

from novaretail.generation.generator import (
    TABLE_ORDER,
    GeneratedData,
    generate_all_data,
)
from novaretail.reporting.excel_report import (
    ExcelExportError,
    export_to_excel,
)


@pytest.fixture(scope="module")
def generated_data() -> GeneratedData:
    """Genera una sola vez las doce tablas del proyecto."""
    return generate_all_data()


@pytest.fixture(scope="module")
def exported_file(
    tmp_path_factory: pytest.TempPathFactory,
    generated_data: GeneratedData,
) -> Path:
    """Exporta una sola vez un libro temporal para las pruebas."""
    output_directory = tmp_path_factory.mktemp(
        "excel_export"
    )

    output_path = (
        output_directory
        / "NovaRetail_Prueba_Exportacion.xlsx"
    )

    return export_to_excel(
        generated_data=generated_data,
        output_path=output_path,
    )


def _normalize_date_columns(
    dataframe: pd.DataFrame,
    date_columns: list[str],
) -> pd.DataFrame:
    """Normaliza fechas para comparar datos originales y Excel.

    Excel almacena las fechas como valores de fecha y hora.
    Pandas puede leerlas como datetime64, mientras las tablas
    originales pueden contener objetos date de Python.

    Args:
        dataframe: Tabla que será normalizada.
        date_columns: Columnas que contienen fechas.

    Returns:
        Copia con fechas normalizadas al formato AAAA-MM-DD.
    """
    normalized = dataframe.copy()

    for column in date_columns:
        if column not in normalized.columns:
            continue

        normalized[column] = (
            pd.to_datetime(
                normalized[column],
                errors="raise",
            )
            .dt.strftime("%Y-%m-%d")
        )

    return normalized


def test_export_to_excel_returns_path(
    exported_file: Path,
) -> None:
    """Comprueba que la función devuelva una ruta."""
    assert isinstance(exported_file, Path)


def test_exported_file_exists(
    exported_file: Path,
) -> None:
    """Comprueba que el archivo haya sido creado."""
    assert exported_file.exists()
    assert exported_file.is_file()


def test_exported_file_has_xlsx_extension(
    exported_file: Path,
) -> None:
    """Comprueba la extensión del libro generado."""
    assert exported_file.suffix.lower() == ".xlsx"


def test_exported_file_is_not_empty(
    exported_file: Path,
) -> None:
    """Comprueba que el archivo tenga contenido."""
    assert exported_file.stat().st_size > 0


def test_workbook_contains_expected_sheets(
    exported_file: Path,
) -> None:
    """Comprueba los nombres y el orden de las hojas."""
    workbook = load_workbook(
        exported_file,
        read_only=True,
        data_only=True,
    )

    try:
        assert workbook.sheetnames == TABLE_ORDER
    finally:
        workbook.close()


def test_workbook_contains_twelve_sheets(
    exported_file: Path,
) -> None:
    """Comprueba la cantidad total de hojas."""
    workbook = load_workbook(
        exported_file,
        read_only=True,
        data_only=True,
    )

    try:
        assert len(workbook.sheetnames) == 12
    finally:
        workbook.close()


def test_sheet_dimensions_match_generated_data(
    exported_file: Path,
    generated_data: GeneratedData,
) -> None:
    """Comprueba filas y columnas de cada hoja."""
    workbook = load_workbook(
        exported_file,
        read_only=True,
        data_only=True,
    )

    try:
        for sheet_name, dataframe in (
            generated_data.iter_tables()
        ):
            worksheet = workbook[sheet_name]

            assert worksheet.max_row == len(dataframe) + 1
            assert worksheet.max_column == len(
                dataframe.columns
            )
    finally:
        workbook.close()


def test_sheet_headers_match_dataframes(
    exported_file: Path,
    generated_data: GeneratedData,
) -> None:
    """Comprueba los encabezados exportados."""
    workbook = load_workbook(
        exported_file,
        read_only=True,
        data_only=True,
    )

    try:
        for sheet_name, dataframe in (
            generated_data.iter_tables()
        ):
            worksheet = workbook[sheet_name]

            exported_headers = [
                cell.value
                for cell in worksheet[1]
            ]

            assert exported_headers == (
                dataframe.columns.tolist()
            )
    finally:
        workbook.close()


def test_control_sheet_contains_synthetic_warning(
    exported_file: Path,
) -> None:
    """Comprueba la advertencia de datos sintéticos."""
    workbook = load_workbook(
        exported_file,
        read_only=True,
        data_only=True,
    )

    try:
        worksheet = workbook["00_Control"]

        control_values = {
            worksheet.cell(
                row=row_number,
                column=1,
            ).value: worksheet.cell(
                row=row_number,
                column=2,
            ).value
            for row_number in range(
                2,
                worksheet.max_row + 1,
            )
        }

        assert control_values[
            "naturaleza_datos"
        ] == "Datos sintéticos"

        assert control_values[
            "empresa_ficticia"
        ] is True

        assert control_values[
            "uso"
        ] == "Exclusivamente académico"

        warning = str(
            control_values["advertencia"]
        )

        assert "ficticios" in warning

        assert (
            "decisiones empresariales reales"
            in warning
        )
    finally:
        workbook.close()


def test_workbook_contains_excel_tables(
    exported_file: Path,
) -> None:
    """Comprueba que cada hoja tenga una tabla estructurada."""
    workbook = load_workbook(
        exported_file,
        read_only=False,
        data_only=False,
    )

    try:
        for sheet_name in TABLE_ORDER:
            assert len(
                workbook[sheet_name].tables
            ) == 1
    finally:
        workbook.close()


def test_worksheets_have_frozen_header(
    exported_file: Path,
) -> None:
    """Comprueba la inmovilización de encabezados."""
    workbook = load_workbook(
        exported_file,
        read_only=False,
        data_only=False,
    )

    try:
        for sheet_name in TABLE_ORDER:
            assert (
                workbook[sheet_name].freeze_panes
                == "A2"
            )
    finally:
        workbook.close()


def test_worksheet_gridlines_are_hidden(
    exported_file: Path,
) -> None:
    """Comprueba que las cuadrículas estén ocultas."""
    workbook = load_workbook(
        exported_file,
        read_only=False,
        data_only=False,
    )

    try:
        for sheet_name in TABLE_ORDER:
            assert (
                workbook[
                    sheet_name
                ].sheet_view.showGridLines
                is False
            )
    finally:
        workbook.close()


def test_workbook_header_style_is_applied(
    exported_file: Path,
) -> None:
    """Comprueba el formato de los encabezados."""
    workbook = load_workbook(
        exported_file,
        read_only=False,
        data_only=False,
    )

    try:
        for sheet_name in TABLE_ORDER:
            first_header = workbook[
                sheet_name
            ].cell(
                row=1,
                column=1,
            )

            assert first_header.font.bold is True
            assert first_header.font.color is not None
            assert first_header.fill.fill_type == "solid"
    finally:
        workbook.close()


def test_synthetic_column_is_highlighted(
    exported_file: Path,
    generated_data: GeneratedData,
) -> None:
    """Comprueba el resaltado de datos sintéticos."""
    workbook = load_workbook(
        exported_file,
        read_only=False,
        data_only=False,
    )

    try:
        for sheet_name, dataframe in (
            generated_data.iter_tables()
        ):
            if (
                "datos_sinteticos"
                not in dataframe.columns
            ):
                continue

            column_number = (
                dataframe.columns.get_loc(
                    "datos_sinteticos"
                )
                + 1
            )

            data_cell = workbook[
                sheet_name
            ].cell(
                row=2,
                column=column_number,
            )

            assert data_cell.fill.fill_type == "solid"
    finally:
        workbook.close()


def test_monetary_columns_have_number_format(
    exported_file: Path,
) -> None:
    """Comprueba el formato de monedas."""
    workbook = load_workbook(
        exported_file,
        read_only=False,
        data_only=False,
    )

    try:
        worksheet = workbook[
            "08_Estado_Resultados"
        ]

        headers = {
            cell.value: cell.column
            for cell in worksheet[1]
        }

        formatted_cell = worksheet.cell(
            row=2,
            column=headers["ingresos_netos_cop"],
        )

        assert formatted_cell.number_format == "#,##0"
    finally:
        workbook.close()


def test_percentage_columns_have_percentage_format(
    exported_file: Path,
) -> None:
    """Comprueba el formato porcentual."""
    workbook = load_workbook(
        exported_file,
        read_only=False,
        data_only=False,
    )

    try:
        worksheet = workbook[
            "08_Estado_Resultados"
        ]

        headers = {
            cell.value: cell.column
            for cell in worksheet[1]
        }

        formatted_cell = worksheet.cell(
            row=2,
            column=headers["margen_neto"],
        )

        assert formatted_cell.number_format == "0.00%"
    finally:
        workbook.close()


def test_workbook_metadata_is_present(
    exported_file: Path,
) -> None:
    """Comprueba las propiedades documentales del libro."""
    workbook = load_workbook(
        exported_file,
        read_only=False,
        data_only=False,
    )

    try:
        assert workbook.properties.title == (
            "NovaRetail Financial GenAI - Datos RAW"
        )

        assert workbook.properties.subject == (
            "Datos sintéticos financieros y operativos"
        )

        assert workbook.properties.creator == (
            "ELVER ALIRIO ALVAREZ RAMIREZ"
        )

        description = str(
            workbook.properties.description
        )

        assert (
            "NovaRetail Colombia S.A.S."
            in description
        )
    finally:
        workbook.close()


def test_exported_values_match_generated_data(
    exported_file: Path,
    generated_data: GeneratedData,
) -> None:
    """Comprueba valores representativos después de exportar."""
    exported_products = pd.read_excel(
        exported_file,
        sheet_name="02_Productos",
        engine="openpyxl",
    )

    exported_income = pd.read_excel(
        exported_file,
        sheet_name="08_Estado_Resultados",
        engine="openpyxl",
    )

    exported_balance = pd.read_excel(
        exported_file,
        sheet_name="09_Balance_General",
        engine="openpyxl",
    )

    expected_products = (
        generated_data.products.copy()
    )

    normalized_exported_products = (
        _normalize_date_columns(
            dataframe=exported_products,
            date_columns=["fecha_ingreso"],
        )
    )

    normalized_expected_products = (
        _normalize_date_columns(
            dataframe=expected_products,
            date_columns=["fecha_ingreso"],
        )
    )

    pd.testing.assert_frame_equal(
        normalized_exported_products,
        normalized_expected_products,
        check_dtype=False,
    )

    pd.testing.assert_frame_equal(
        exported_income,
        generated_data.income_statement,
        check_dtype=False,
    )

    pd.testing.assert_frame_equal(
        exported_balance,
        generated_data.balance_sheet,
        check_dtype=False,
    )


def test_export_rejects_invalid_extension(
    generated_data: GeneratedData,
    tmp_path: Path,
) -> None:
    """Comprueba el rechazo de una extensión inválida."""
    invalid_path = (
        tmp_path / "NovaRetail_Datos_RAW.csv"
    )

    with pytest.raises(
        ExcelExportError,
        match="extensión .xlsx",
    ):
        export_to_excel(
            generated_data=generated_data,
            output_path=invalid_path,
        )