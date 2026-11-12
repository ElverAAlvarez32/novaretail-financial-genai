"""Orquestador maestro de generación de datos sintéticos.

Este módulo ejecuta los generadores de NovaRetail en el orden
correcto y reúne las doce tablas previstas para el proyecto.

Los datos generados pertenecen a una empresa completamente ficticia
y se utilizan exclusivamente con fines académicos.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterator

import pandas as pd

from novaretail import __version__
from novaretail.config import (
    load_data_generation_config,
    load_settings,
)
from novaretail.generation.balance_sheet import (
    generate_balance_sheet,
)
from novaretail.generation.budget import generate_budget
from novaretail.generation.cash_flow import generate_cash_flow
from novaretail.generation.customers import generate_customers
from novaretail.generation.financial_statements import (
    generate_income_statement,
)
from novaretail.generation.inventory import generate_inventory
from novaretail.generation.marketing import generate_marketing
from novaretail.generation.orders import generate_orders
from novaretail.generation.products import generate_products
from novaretail.generation.returns import generate_returns
from novaretail.logging_config import get_logger


LOGGER = get_logger(__name__)


TABLE_ORDER = [
    "00_Control",
    "01_Parametros",
    "02_Productos",
    "03_Clientes",
    "04_Pedidos",
    "05_Inventario",
    "06_Devoluciones",
    "07_Marketing",
    "08_Estado_Resultados",
    "09_Balance_General",
    "10_Flujo_Efectivo",
    "11_Presupuesto",
]


@dataclass(frozen=True)
class GeneratedData:
    """Contenedor inmutable de las tablas generadas.

    Attributes:
        control: Identificación y advertencias del conjunto.
        parameters: Parámetros principales de generación.
        products: Catálogo sintético de productos.
        customers: Catálogo sintético de clientes.
        orders: Líneas sintéticas de pedido.
        inventory: Inventario mensual por producto.
        returns: Registros sintéticos de devolución.
        marketing: Métricas mensuales de marketing.
        income_statement: Estado de resultados mensual.
        balance_sheet: Balance general mensual.
        cash_flow: Flujo de efectivo mensual.
        budget: Presupuesto mensual por categoría.
    """

    control: pd.DataFrame
    parameters: pd.DataFrame
    products: pd.DataFrame
    customers: pd.DataFrame
    orders: pd.DataFrame
    inventory: pd.DataFrame
    returns: pd.DataFrame
    marketing: pd.DataFrame
    income_statement: pd.DataFrame
    balance_sheet: pd.DataFrame
    cash_flow: pd.DataFrame
    budget: pd.DataFrame

    def as_dict(self) -> dict[str, pd.DataFrame]:
        """Devuelve las tablas con los nombres de hojas previstos.

        Returns:
            Diccionario ordenado con nombre de hoja y DataFrame.
        """
        return {
            "00_Control": self.control,
            "01_Parametros": self.parameters,
            "02_Productos": self.products,
            "03_Clientes": self.customers,
            "04_Pedidos": self.orders,
            "05_Inventario": self.inventory,
            "06_Devoluciones": self.returns,
            "07_Marketing": self.marketing,
            "08_Estado_Resultados": self.income_statement,
            "09_Balance_General": self.balance_sheet,
            "10_Flujo_Efectivo": self.cash_flow,
            "11_Presupuesto": self.budget,
        }

    def iter_tables(
        self,
    ) -> Iterator[tuple[str, pd.DataFrame]]:
        """Permite recorrer las tablas en el orden establecido.

        Yields:
            Tuplas con nombre de hoja y DataFrame.
        """
        yield from self.as_dict().items()

    def row_summary(self) -> dict[str, int]:
        """Devuelve la cantidad de filas de cada tabla.

        Returns:
            Diccionario con nombres y cantidades de registros.
        """
        return {
            table_name: len(dataframe)
            for table_name, dataframe in self.iter_tables()
        }


def _build_control_table() -> pd.DataFrame:
    """Construye la tabla de control del conjunto.

    Returns:
        DataFrame vertical con metadatos y advertencias.
    """
    settings = load_settings()
    generation_config = load_data_generation_config()

    records = [
        {
            "campo": "nombre_proyecto",
            "valor": settings["project"]["name"],
        },
        {
            "campo": "version_proyecto",
            "valor": __version__,
        },
        {
            "campo": "empresa",
            "valor": settings["company"]["name"],
        },
        {
            "campo": "empresa_ficticia",
            "valor": True,
        },
        {
            "campo": "naturaleza_datos",
            "valor": "Datos sintéticos",
        },
        {
            "campo": "uso",
            "valor": "Exclusivamente académico",
        },
        {
            "campo": "pais_referencia",
            "valor": settings["company"]["country"],
        },
        {
            "campo": "sector",
            "valor": settings["company"]["sector"],
        },
        {
            "campo": "moneda",
            "valor": settings["financial"]["currency"],
        },
        {
            "campo": "unidad_reporte",
            "valor": settings["financial"]["reporting_unit"],
        },
        {
            "campo": "frecuencia",
            "valor": settings["financial"][
                "reporting_frequency"
            ],
        },
        {
            "campo": "periodo_inicial",
            "valor": settings["period"]["start_date"],
        },
        {
            "campo": "periodo_final",
            "valor": settings["period"]["end_date"],
        },
        {
            "campo": "meses_esperados",
            "valor": settings["period"]["expected_months"],
        },
        {
            "campo": "semilla_generacion",
            "valor": generation_config["generation"][
                "random_seed"
            ],
        },
        {
            "campo": "responsable",
            "valor": settings["project"]["owner"],
        },
        {
            "campo": "advertencia",
            "valor": (
                "La empresa, clientes, productos, operaciones y "
                "resultados son ficticios. No deben utilizarse para "
                "tomar decisiones empresariales reales."
            ),
        },
    ]

    return pd.DataFrame(
        records,
        columns=["campo", "valor"],
    )


def _flatten_configuration(
    value: object,
    prefix: str = "",
) -> list[dict[str, object]]:
    """Convierte una configuración anidada en filas simples.

    Args:
        value: Valor, lista o diccionario que será procesado.
        prefix: Ruta acumulada del parámetro.

    Returns:
        Lista con parámetro, valor y tipo.
    """
    records: list[dict[str, object]] = []

    if isinstance(value, dict):
        for key, nested_value in value.items():
            nested_prefix = (
                f"{prefix}.{key}"
                if prefix
                else str(key)
            )

            records.extend(
                _flatten_configuration(
                    value=nested_value,
                    prefix=nested_prefix,
                )
            )

        return records

    if isinstance(value, list):
        formatted_value = " | ".join(
            str(item) for item in value
        )

        records.append(
            {
                "parametro": prefix,
                "valor": formatted_value,
                "tipo": "lista",
            }
        )

        return records

    records.append(
        {
            "parametro": prefix,
            "valor": value,
            "tipo": type(value).__name__,
        }
    )

    return records


def _build_parameters_table() -> pd.DataFrame:
    """Construye una tabla documentada de parámetros.

    Returns:
        DataFrame con parámetros, valores y tipos.
    """
    generation_config = load_data_generation_config()

    parameter_records = _flatten_configuration(
        generation_config
    )

    return pd.DataFrame(
        parameter_records,
        columns=[
            "parametro",
            "valor",
            "tipo",
        ],
    )


def _validate_generated_collection(
    generated_data: GeneratedData,
) -> None:
    """Valida el conjunto completo antes de devolverlo.

    Args:
        generated_data: Contenedor con las tablas generadas.

    Raises:
        ValueError: Si faltan tablas, registros o identificadores.
    """
    tables = generated_data.as_dict()

    if list(tables) != TABLE_ORDER:
        raise ValueError(
            "Las tablas generadas no tienen el orden esperado."
        )

    for table_name, dataframe in tables.items():
        if not isinstance(dataframe, pd.DataFrame):
            raise ValueError(
                f"La tabla {table_name} no es un DataFrame."
            )

        if dataframe.empty:
            raise ValueError(
                f"La tabla {table_name} está vacía."
            )

    expected_months = load_settings()["period"][
        "expected_months"
    ]

    monthly_tables = {
        "08_Estado_Resultados":
            generated_data.income_statement,
        "09_Balance_General":
            generated_data.balance_sheet,
        "10_Flujo_Efectivo":
            generated_data.cash_flow,
    }

    for table_name, dataframe in monthly_tables.items():
        if len(dataframe) != expected_months:
            raise ValueError(
                f"La tabla {table_name} no contiene "
                f"{expected_months} periodos."
            )

    if not generated_data.products[
        "producto_id"
    ].is_unique:
        raise ValueError(
            "Los identificadores de productos no son únicos."
        )

    if not generated_data.customers[
        "cliente_id"
    ].is_unique:
        raise ValueError(
            "Los identificadores de clientes no son únicos."
        )

    if not generated_data.orders[
        "linea_pedido_id"
    ].is_unique:
        raise ValueError(
            "Los identificadores de líneas no son únicos."
        )

    if not generated_data.returns[
        "devolucion_id"
    ].is_unique:
        raise ValueError(
            "Los identificadores de devoluciones no son únicos."
        )

    if not generated_data.marketing[
        "campania_id"
    ].is_unique:
        raise ValueError(
            "Los identificadores de campañas no son únicos."
        )

    if not generated_data.budget[
        "presupuesto_id"
    ].is_unique:
        raise ValueError(
            "Los identificadores presupuestales no son únicos."
        )

    if not (
        generated_data.balance_sheet[
            "diferencia_balance_cop"
        ] == 0
    ).all():
        raise ValueError(
            "El balance general presenta diferencias."
        )

    if not (
        generated_data.cash_flow[
            "diferencia_conciliacion_cop"
        ] == 0
    ).all():
        raise ValueError(
            "El flujo de efectivo presenta diferencias."
        )


def generate_all_data() -> GeneratedData:
    """Ejecuta la generación completa en la secuencia correcta.

    Returns:
        Contenedor con las doce tablas sintéticas verificadas.
    """
    start_time = datetime.now()

    LOGGER.info(
        "Iniciando generación maestra de datos NovaRetail."
    )

    control = _build_control_table()
    parameters = _build_parameters_table()

    products = generate_products()
    customers = generate_customers()

    orders = generate_orders(
        products=products,
        customers=customers,
    )

    returns = generate_returns(
        orders=orders,
    )

    marketing = generate_marketing()

    inventory = generate_inventory(
        products=products,
        orders=orders,
    )

    income_statement = generate_income_statement(
        orders=orders,
        returns=returns,
        marketing=marketing,
    )

    balance_sheet = generate_balance_sheet(
        income_statement=income_statement,
        inventory=inventory,
    )

    cash_flow = generate_cash_flow(
        income_statement=income_statement,
        balance_sheet=balance_sheet,
    )

    budget = generate_budget(
        income_statement=income_statement,
        cash_flow=cash_flow,
    )

    generated_data = GeneratedData(
        control=control,
        parameters=parameters,
        products=products,
        customers=customers,
        orders=orders,
        inventory=inventory,
        returns=returns,
        marketing=marketing,
        income_statement=income_statement,
        balance_sheet=balance_sheet,
        cash_flow=cash_flow,
        budget=budget,
    )

    _validate_generated_collection(
        generated_data=generated_data
    )

    elapsed_seconds = (
        datetime.now() - start_time
    ).total_seconds()

    LOGGER.info(
        "Generación maestra completada en %.2f segundos.",
        elapsed_seconds,
    )

    for table_name, row_count in (
        generated_data.row_summary().items()
    ):
        LOGGER.info(
            "%s: %s registros.",
            table_name,
            row_count,
        )

    return generated_data