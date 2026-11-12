"""Generación reproducible del presupuesto mensual sintético.

Este módulo construye el presupuesto y compara los valores
presupuestados con los valores ejecutados de NovaRetail Colombia S.A.S.

Se utilizan ocho categorías por cada uno de los 36 periodos:

- Ventas netas.
- Costo de ventas.
- Marketing.
- Logística.
- Plataforma.
- Personal.
- Administración.
- Inversiones.

Todos los datos son sintéticos y de uso exclusivamente académico.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from novaretail.config import load_data_generation_config
from novaretail.logging_config import get_logger


LOGGER = get_logger(__name__)


BUDGET_COLUMNS = [
    "presupuesto_id",
    "periodo",
    "anio",
    "mes",
    "centro_costo",
    "categoria",
    "naturaleza",
    "valor_presupuestado_cop",
    "valor_ejecutado_cop",
    "variacion_absoluta_cop",
    "variacion_porcentual",
    "estado_desviacion",
    "impacto_presupuestal",
    "responsable_simulado",
    "datos_sinteticos",
]


CATEGORY_DEFINITIONS = {
    "Ventas netas": {
        "source": "ingresos_netos_cop",
        "cost_center": "Comercial",
        "nature": "Ingreso",
        "responsible": "Gerencia comercial simulada",
        "budget_variation": (-0.06, 0.06),
    },
    "Costo de ventas": {
        "source": "costo_mercancia_vendida_cop",
        "cost_center": "Operaciones",
        "nature": "Egreso",
        "responsible": "Jefatura de compras simulada",
        "budget_variation": (-0.05, 0.05),
    },
    "Marketing": {
        "source": "gastos_marketing_cop",
        "cost_center": "Marketing",
        "nature": "Egreso",
        "responsible": "Jefatura de marketing simulada",
        "budget_variation": (-0.08, 0.08),
    },
    "Logística": {
        "source": "gastos_logistica_cop",
        "cost_center": "Logística",
        "nature": "Egreso",
        "responsible": "Jefatura logística simulada",
        "budget_variation": (-0.07, 0.07),
    },
    "Plataforma": {
        "source": "gastos_plataforma_cop",
        "cost_center": "Tecnología",
        "nature": "Egreso",
        "responsible": "Jefatura de tecnología simulada",
        "budget_variation": (-0.05, 0.05),
    },
    "Personal": {
        "source": "gastos_personal_cop",
        "cost_center": "Talento humano",
        "nature": "Egreso",
        "responsible": "Jefatura de talento humano simulada",
        "budget_variation": (-0.04, 0.04),
    },
    "Administración": {
        "source": "gastos_administrativos_cop",
        "cost_center": "Administración",
        "nature": "Egreso",
        "responsible": "Gerencia administrativa simulada",
        "budget_variation": (-0.05, 0.05),
    },
    "Inversiones": {
        "source": "compras_activos_fijos_cop",
        "cost_center": "Inversiones",
        "nature": "Egreso",
        "responsible": "Gerencia financiera simulada",
        "budget_variation": (-0.10, 0.10),
    },
}


ACCEPTABLE_DEVIATION_RATE = 0.05
MODERATE_DEVIATION_RATE = 0.10


def _validate_input_data(
    income_statement: pd.DataFrame,
    cash_flow: pd.DataFrame,
) -> None:
    """Valida las tablas utilizadas para generar el presupuesto.

    Args:
        income_statement: Estado de resultados mensual.
        cash_flow: Flujo de efectivo mensual.

    Raises:
        ValueError: Si faltan columnas o periodos requeridos.
    """
    required_income_columns = {
        "periodo",
        "anio",
        "mes",
        "ingresos_netos_cop",
        "costo_mercancia_vendida_cop",
        "gastos_marketing_cop",
        "gastos_logistica_cop",
        "gastos_plataforma_cop",
        "gastos_personal_cop",
        "gastos_administrativos_cop",
        "datos_sinteticos",
    }

    required_cash_flow_columns = {
        "periodo",
        "compras_activos_fijos_cop",
        "datos_sinteticos",
    }

    missing_income_columns = required_income_columns.difference(
        income_statement.columns
    )

    missing_cash_flow_columns = required_cash_flow_columns.difference(
        cash_flow.columns
    )

    if missing_income_columns:
        missing_text = ", ".join(
            sorted(missing_income_columns)
        )
        raise ValueError(
            "Faltan columnas en el estado de resultados: "
            f"{missing_text}"
        )

    if missing_cash_flow_columns:
        missing_text = ", ".join(
            sorted(missing_cash_flow_columns)
        )
        raise ValueError(
            f"Faltan columnas en el flujo de efectivo: {missing_text}"
        )

    if income_statement.empty:
        raise ValueError(
            "El estado de resultados está vacío."
        )

    if cash_flow.empty:
        raise ValueError(
            "El flujo de efectivo está vacío."
        )

    if income_statement["periodo"].duplicated().any():
        raise ValueError(
            "El estado de resultados contiene periodos duplicados."
        )

    if cash_flow["periodo"].duplicated().any():
        raise ValueError(
            "El flujo de efectivo contiene periodos duplicados."
        )

    if set(income_statement["periodo"]) != set(
        cash_flow["periodo"]
    ):
        raise ValueError(
            "Los periodos del estado de resultados y del "
            "flujo de efectivo no coinciden."
        )

    if not income_statement["datos_sinteticos"].all():
        raise ValueError(
            "El estado de resultados debe identificarse "
            "como sintético."
        )

    if not cash_flow["datos_sinteticos"].all():
        raise ValueError(
            "El flujo de efectivo debe identificarse como sintético."
        )


def _calculate_budget_value(
    executed_value: int,
    minimum_variation: float,
    maximum_variation: float,
    rng: np.random.Generator,
) -> int:
    """Calcula el valor presupuestado de una categoría.

    Args:
        executed_value: Valor ejecutado del periodo.
        minimum_variation: Variación mínima permitida.
        maximum_variation: Variación máxima permitida.
        rng: Generador aleatorio reproducible.

    Returns:
        Valor presupuestado positivo.
    """
    variation = float(
        rng.uniform(
            minimum_variation,
            maximum_variation,
        )
    )

    budget_value = int(
        round(
            executed_value
            * (1 + variation)
        )
    )

    return max(budget_value, 1)


def _safe_percentage(
    numerator: int | float,
    denominator: int | float,
) -> float:
    """Calcula un porcentaje evitando divisiones por cero.

    Args:
        numerator: Valor de la variación.
        denominator: Valor presupuestado.

    Returns:
        Porcentaje redondeado a cuatro decimales.
    """
    if denominator == 0:
        return 0.0

    return round(
        float(numerator) / float(denominator),
        4,
    )


def _classify_deviation(
    deviation_rate: float,
) -> str:
    """Clasifica la magnitud absoluta de una desviación.

    Args:
        deviation_rate: Variación porcentual calculada.

    Returns:
        Clasificación de la desviación.
    """
    absolute_rate = abs(deviation_rate)

    if absolute_rate <= ACCEPTABLE_DEVIATION_RATE:
        return "Dentro del rango"

    if absolute_rate <= MODERATE_DEVIATION_RATE:
        return "Desviación moderada"

    return "Desviación significativa"


def _classify_budget_impact(
    nature: str,
    absolute_variation: int,
) -> str:
    """Clasifica el efecto financiero de la desviación.

    Para ingresos, ejecutar más que el presupuesto es favorable.
    Para egresos, ejecutar menos que el presupuesto es favorable.

    Args:
        nature: Naturaleza de la categoría.
        absolute_variation: Ejecutado menos presupuestado.

    Returns:
        Clasificación favorable, desfavorable o neutral.
    """
    if absolute_variation == 0:
        return "Neutral"

    if nature == "Ingreso":
        return (
            "Favorable"
            if absolute_variation > 0
            else "Desfavorable"
        )

    return (
        "Favorable"
        if absolute_variation < 0
        else "Desfavorable"
    )


def generate_budget(
    income_statement: pd.DataFrame,
    cash_flow: pd.DataFrame,
    random_seed: int | None = None,
) -> pd.DataFrame:
    """Genera el presupuesto mensual y sus desviaciones.

    Args:
        income_statement: Estado de resultados mensual.
        cash_flow: Flujo de efectivo mensual.
        random_seed: Semilla alternativa de generación.

    Returns:
        DataFrame con presupuesto, ejecución y desviaciones.

    Raises:
        ValueError: Si las entradas o resultados son inválidos.
    """
    _validate_input_data(
        income_statement=income_statement,
        cash_flow=cash_flow,
    )

    configuration = load_data_generation_config()

    configured_seed = int(
        configuration["generation"]["random_seed"]
    )

    seed = (
        configured_seed + 800
        if random_seed is None
        else random_seed
    )

    rng = np.random.default_rng(seed)

    ordered_income = (
        income_statement.sort_values("periodo")
        .reset_index(drop=True)
        .copy()
    )

    investment_data = cash_flow[
        [
            "periodo",
            "compras_activos_fijos_cop",
        ]
    ]

    budget_base = ordered_income.merge(
        investment_data,
        on="periodo",
        how="left",
        validate="one_to_one",
    )

    records: list[dict] = []
    budget_number = 0

    LOGGER.info(
        "Iniciando generación del presupuesto para "
        "%s periodos y %s categorías.",
        len(budget_base),
        len(CATEGORY_DEFINITIONS),
    )

    for row in budget_base.itertuples(index=False):
        for category, definition in CATEGORY_DEFINITIONS.items():
            budget_number += 1

            source_column = str(
                definition["source"]
            )

            executed_value = int(
                getattr(row, source_column)
            )

            minimum_variation, maximum_variation = (
                definition["budget_variation"]
            )

            budgeted_value = _calculate_budget_value(
                executed_value=executed_value,
                minimum_variation=float(minimum_variation),
                maximum_variation=float(maximum_variation),
                rng=rng,
            )

            absolute_variation = (
                executed_value - budgeted_value
            )

            percentage_variation = _safe_percentage(
                numerator=absolute_variation,
                denominator=budgeted_value,
            )

            deviation_status = _classify_deviation(
                deviation_rate=percentage_variation,
            )

            budget_impact = _classify_budget_impact(
                nature=str(definition["nature"]),
                absolute_variation=absolute_variation,
            )

            record = {
                "presupuesto_id": (
                    f"PRE-{budget_number:05d}"
                ),
                "periodo": row.periodo,
                "anio": int(row.anio),
                "mes": int(row.mes),
                "centro_costo": definition[
                    "cost_center"
                ],
                "categoria": category,
                "naturaleza": definition["nature"],
                "valor_presupuestado_cop": (
                    budgeted_value
                ),
                "valor_ejecutado_cop": executed_value,
                "variacion_absoluta_cop": (
                    absolute_variation
                ),
                "variacion_porcentual": (
                    percentage_variation
                ),
                "estado_desviacion": deviation_status,
                "impacto_presupuestal": budget_impact,
                "responsable_simulado": definition[
                    "responsible"
                ],
                "datos_sinteticos": True,
            }

            records.append(record)

    budget = pd.DataFrame(
        records,
        columns=BUDGET_COLUMNS,
    )

    _validate_generated_budget(
        budget=budget,
        expected_periods=len(budget_base),
        expected_categories=len(CATEGORY_DEFINITIONS),
    )

    LOGGER.info(
        "Presupuesto generado correctamente: %s registros.",
        len(budget),
    )

    return budget


def _validate_generated_budget(
    budget: pd.DataFrame,
    expected_periods: int,
    expected_categories: int,
) -> None:
    """Valida el presupuesto generado.

    Args:
        budget: Presupuesto mensual generado.
        expected_periods: Cantidad esperada de periodos.
        expected_categories: Categorías por periodo.

    Raises:
        ValueError: Si una regla de integridad falla.
    """
    expected_records = (
        expected_periods * expected_categories
    )

    if len(budget) != expected_records:
        raise ValueError(
            "La cantidad de registros presupuestales "
            "no coincide con la esperada."
        )

    if budget["presupuesto_id"].duplicated().any():
        raise ValueError(
            "Se detectaron identificadores presupuestales "
            "duplicados."
        )

    if not budget["presupuesto_id"].str.match(
        r"^PRE-\d{5}$"
    ).all():
        raise ValueError(
            "Existen identificadores presupuestales inválidos."
        )

    duplicated_records = budget.duplicated(
        subset=["periodo", "categoria"]
    )

    if duplicated_records.any():
        raise ValueError(
            "Existe más de un registro para una categoría "
            "dentro del mismo periodo."
        )

    if (budget["valor_presupuestado_cop"] <= 0).any():
        raise ValueError(
            "Los valores presupuestados deben ser positivos."
        )

    if (budget["valor_ejecutado_cop"] < 0).any():
        raise ValueError(
            "Los valores ejecutados no pueden ser negativos."
        )

    expected_absolute_variation = (
        budget["valor_ejecutado_cop"]
        - budget["valor_presupuestado_cop"]
    )

    if not expected_absolute_variation.equals(
        budget["variacion_absoluta_cop"]
    ):
        raise ValueError(
            "La variación absoluta presenta inconsistencias."
        )

    expected_percentage_variation = (
        budget["variacion_absoluta_cop"]
        / budget["valor_presupuestado_cop"]
    ).round(4)

    if not expected_percentage_variation.equals(
        budget["variacion_porcentual"]
    ):
        raise ValueError(
            "La variación porcentual presenta inconsistencias."
        )

    expected_categories_set = set(
        CATEGORY_DEFINITIONS
    )

    generated_categories_set = set(
        budget["categoria"].unique()
    )

    if generated_categories_set != expected_categories_set:
        raise ValueError(
            "Las categorías presupuestales no coinciden."
        )

    valid_deviation_states = {
        "Dentro del rango",
        "Desviación moderada",
        "Desviación significativa",
    }

    if not set(
        budget["estado_desviacion"].unique()
    ).issubset(valid_deviation_states):
        raise ValueError(
            "Se generaron estados de desviación inválidos."
        )

    valid_budget_impacts = {
        "Favorable",
        "Desfavorable",
        "Neutral",
    }

    if not set(
        budget["impacto_presupuestal"].unique()
    ).issubset(valid_budget_impacts):
        raise ValueError(
            "Se generaron impactos presupuestales inválidos."
        )

    if not budget["datos_sinteticos"].all():
        raise ValueError(
            "Todos los registros deben identificarse "
            "como sintéticos."
        )