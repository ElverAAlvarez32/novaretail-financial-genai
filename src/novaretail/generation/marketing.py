"""Generación reproducible de métricas sintéticas de marketing.

Este módulo crea información mensual por canal de adquisición para
NovaRetail Colombia S.A.S. Todos los valores son ficticios y se
utilizan exclusivamente con fines académicos.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from novaretail.config import load_data_generation_config
from novaretail.logging_config import get_logger


LOGGER = get_logger(__name__)

MARKETING_COLUMNS = [
    "periodo",
    "canal",
    "campania_id",
    "inversion_cop",
    "impresiones",
    "clics",
    "sesiones",
    "conversiones",
    "pedidos_atribuidos",
    "ingresos_atribuidos_cop",
    "costo_por_clic_cop",
    "tasa_clics",
    "tasa_conversion",
    "costo_adquisicion_cop",
    "retorno_publicitario",
    "datos_sinteticos",
]


CHANNEL_PARAMETERS = {
    "Búsqueda pagada": {
        "investment_weight": 0.28,
        "cost_per_thousand_impressions": (16_000, 27_000),
        "click_rate": (0.025, 0.055),
        "session_rate": (0.84, 0.96),
        "conversion_rate": (0.025, 0.055),
        "average_order_value": (180_000, 430_000),
    },
    "Redes sociales": {
        "investment_weight": 0.25,
        "cost_per_thousand_impressions": (9_000, 19_000),
        "click_rate": (0.012, 0.035),
        "session_rate": (0.78, 0.92),
        "conversion_rate": (0.012, 0.038),
        "average_order_value": (120_000, 360_000),
    },
    "Correo electrónico": {
        "investment_weight": 0.08,
        "cost_per_thousand_impressions": (4_000, 10_000),
        "click_rate": (0.035, 0.085),
        "session_rate": (0.88, 0.98),
        "conversion_rate": (0.035, 0.075),
        "average_order_value": (160_000, 410_000),
    },
    "Afiliados": {
        "investment_weight": 0.10,
        "cost_per_thousand_impressions": (11_000, 22_000),
        "click_rate": (0.018, 0.045),
        "session_rate": (0.82, 0.94),
        "conversion_rate": (0.020, 0.050),
        "average_order_value": (140_000, 390_000),
    },
    "Tráfico orgánico": {
        "investment_weight": 0.17,
        "cost_per_thousand_impressions": (5_000, 12_000),
        "click_rate": (0.030, 0.070),
        "session_rate": (0.88, 0.98),
        "conversion_rate": (0.025, 0.060),
        "average_order_value": (150_000, 420_000),
    },
    "Tráfico directo": {
        "investment_weight": 0.12,
        "cost_per_thousand_impressions": (5_000, 11_000),
        "click_rate": (0.040, 0.090),
        "session_rate": (0.90, 0.99),
        "conversion_rate": (0.030, 0.070),
        "average_order_value": (170_000, 450_000),
    },
}


def _validate_configuration(configuration: dict) -> None:
    """Valida los parámetros utilizados por el generador.

    Args:
        configuration: Configuración de generación del proyecto.

    Raises:
        ValueError: Si existen canales o valores inválidos.
    """
    configured_channels = configuration["marketing"]["channels"]
    expected_channel_count = configuration["volumes"][
        "marketing_channels"
    ]

    if len(configured_channels) != expected_channel_count:
        raise ValueError(
            "La cantidad de canales no coincide con la configuración."
        )

    missing_channels = set(configured_channels).difference(
        CHANNEL_PARAMETERS
    )

    if missing_channels:
        missing_text = ", ".join(sorted(missing_channels))
        raise ValueError(
            "Existen canales sin parámetros definidos: "
            f"{missing_text}"
        )

    weight_total = sum(
        CHANNEL_PARAMETERS[channel]["investment_weight"]
        for channel in configured_channels
    )

    if not np.isclose(weight_total, 1.0):
        raise ValueError(
            "Los pesos de inversión de marketing deben sumar 1."
        )

    minimum_investment = configuration["marketing"][
        "minimum_monthly_investment_cop"
    ]
    maximum_investment = configuration["marketing"][
        "maximum_monthly_investment_cop"
    ]

    if minimum_investment <= 0:
        raise ValueError(
            "La inversión mensual mínima debe ser positiva."
        )

    if maximum_investment <= minimum_investment:
        raise ValueError(
            "La inversión máxima debe superar la inversión mínima."
        )


def _calculate_monthly_investment(
    period: pd.Timestamp,
    configuration: dict,
    rng: np.random.Generator,
) -> int:
    """Calcula la inversión total simulada de un mes.

    Args:
        period: Periodo mensual analizado.
        configuration: Parámetros de generación.
        rng: Generador aleatorio reproducible.

    Returns:
        Inversión mensual total expresada en COP.
    """
    minimum_investment = int(
        configuration["marketing"][
            "minimum_monthly_investment_cop"
        ]
    )
    maximum_investment = int(
        configuration["marketing"][
            "maximum_monthly_investment_cop"
        ]
    )

    growth_rate = float(
        configuration["sales"]["annual_growth_rate"][
            period.year
        ]
    )

    seasonal_factor = float(
        configuration["sales"]["seasonal_factors"][
            period.month
        ]
    )

    central_investment = (
        minimum_investment
        + maximum_investment
    ) / 2

    variation = float(
        rng.normal(loc=1.0, scale=0.07)
    )

    estimated_investment = (
        central_investment
        * (1 + growth_rate)
        * seasonal_factor
        * variation
    )

    return int(
        np.clip(
            round(estimated_investment),
            minimum_investment,
            maximum_investment,
        )
    )


def _safe_ratio(
    numerator: int | float,
    denominator: int | float,
) -> float:
    """Calcula una razón evitando divisiones por cero.

    Args:
        numerator: Numerador.
        denominator: Denominador.

    Returns:
        Razón redondeada a cuatro decimales.
    """
    if denominator == 0:
        return 0.0

    return round(
        float(numerator) / float(denominator),
        4,
    )


def generate_marketing(
    random_seed: int | None = None,
) -> pd.DataFrame:
    """Genera métricas mensuales sintéticas de marketing.

    Args:
        random_seed: Semilla alternativa de generación.

    Returns:
        DataFrame con métricas por canal y mes.

    Raises:
        ValueError: Si la configuración o el resultado son inválidos.
    """
    configuration = load_data_generation_config()
    _validate_configuration(configuration)

    configured_seed = int(
        configuration["generation"]["random_seed"]
    )

    seed = (
        configured_seed + 500
        if random_seed is None
        else random_seed
    )

    rng = np.random.default_rng(seed)

    start_date = pd.Timestamp(
        configuration["period"]["start_date"]
    )
    end_date = pd.Timestamp(
        configuration["period"]["end_date"]
    )

    channels = configuration["marketing"]["channels"]

    periods = pd.date_range(
        start=start_date,
        end=end_date,
        freq="MS",
    )

    records: list[dict] = []

    LOGGER.info(
        "Iniciando generación de marketing para %s canales "
        "y %s periodos.",
        len(channels),
        len(periods),
    )

    for period in periods:
        total_monthly_investment = (
            _calculate_monthly_investment(
                period=period,
                configuration=configuration,
                rng=rng,
            )
        )

        period_text = period.strftime("%Y-%m")

        for channel_number, channel in enumerate(
            channels,
            start=1,
        ):
            parameters = CHANNEL_PARAMETERS[channel]

            channel_variation = float(
                rng.uniform(0.92, 1.08)
            )

            investment = int(
                round(
                    total_monthly_investment
                    * parameters["investment_weight"]
                    * channel_variation
                )
            )

            investment = max(investment, 1)

            minimum_cpm, maximum_cpm = parameters[
                "cost_per_thousand_impressions"
            ]

            cpm = float(
                rng.uniform(
                    minimum_cpm,
                    maximum_cpm,
                )
            )

            impressions = max(
                int(round(investment / cpm * 1_000)),
                1,
            )

            minimum_click_rate, maximum_click_rate = (
                parameters["click_rate"]
            )

            click_rate = float(
                rng.uniform(
                    minimum_click_rate,
                    maximum_click_rate,
                )
            )

            clicks = max(
                int(round(impressions * click_rate)),
                1,
            )

            minimum_session_rate, maximum_session_rate = (
                parameters["session_rate"]
            )

            session_rate = float(
                rng.uniform(
                    minimum_session_rate,
                    maximum_session_rate,
                )
            )

            sessions = max(
                int(round(clicks * session_rate)),
                1,
            )

            (
                minimum_conversion_rate,
                maximum_conversion_rate,
            ) = parameters["conversion_rate"]

            conversion_rate = float(
                rng.uniform(
                    minimum_conversion_rate,
                    maximum_conversion_rate,
                )
            )

            conversions = max(
                int(round(sessions * conversion_rate)),
                1,
            )

            attributed_orders = max(
                int(
                    round(
                        conversions
                        * rng.uniform(0.88, 0.98)
                    )
                ),
                1,
            )

            (
                minimum_order_value,
                maximum_order_value,
            ) = parameters["average_order_value"]

            average_order_value = float(
                rng.uniform(
                    minimum_order_value,
                    maximum_order_value,
                )
            )

            attributed_revenue = int(
                round(
                    attributed_orders
                    * average_order_value
                )
            )

            cost_per_click = round(
                investment / clicks,
                2,
            )

            click_through_rate = _safe_ratio(
                clicks,
                impressions,
            )

            calculated_conversion_rate = _safe_ratio(
                conversions,
                sessions,
            )

            acquisition_cost = round(
                investment / attributed_orders,
                2,
            )

            advertising_return = round(
                attributed_revenue / investment,
                4,
            )

            record = {
                "periodo": period_text,
                "canal": channel,
                "campania_id": (
                    f"CAM-{period.strftime('%Y%m')}-"
                    f"{channel_number:02d}"
                ),
                "inversion_cop": investment,
                "impresiones": impressions,
                "clics": clicks,
                "sesiones": sessions,
                "conversiones": conversions,
                "pedidos_atribuidos": attributed_orders,
                "ingresos_atribuidos_cop": (
                    attributed_revenue
                ),
                "costo_por_clic_cop": cost_per_click,
                "tasa_clics": click_through_rate,
                "tasa_conversion": (
                    calculated_conversion_rate
                ),
                "costo_adquisicion_cop": (
                    acquisition_cost
                ),
                "retorno_publicitario": (
                    advertising_return
                ),
                "datos_sinteticos": True,
            }

            records.append(record)

    marketing = pd.DataFrame(
        records,
        columns=MARKETING_COLUMNS,
    )

    _validate_generated_marketing(
        marketing=marketing,
        expected_periods=len(periods),
        expected_channels=len(channels),
        allowed_channels=set(channels),
    )

    LOGGER.info(
        "Marketing generado correctamente: %s registros.",
        len(marketing),
    )

    return marketing


def _validate_generated_marketing(
    marketing: pd.DataFrame,
    expected_periods: int,
    expected_channels: int,
    allowed_channels: set[str],
) -> None:
    """Valida las métricas de marketing generadas.

    Args:
        marketing: Información generada.
        expected_periods: Cantidad esperada de periodos.
        expected_channels: Cantidad esperada de canales.
        allowed_channels: Canales autorizados.

    Raises:
        ValueError: Si una regla de integridad falla.
    """
    expected_records = (
        expected_periods * expected_channels
    )

    if len(marketing) != expected_records:
        raise ValueError(
            "La cantidad de registros de marketing no coincide "
            "con periodos por canales."
        )

    if marketing["campania_id"].duplicated().any():
        raise ValueError(
            "Se detectaron identificadores de campaña duplicados."
        )

    generated_channels = set(
        marketing["canal"].unique()
    )

    if not generated_channels.issubset(
        allowed_channels
    ):
        raise ValueError(
            "Se generaron canales no autorizados."
        )

    positive_columns = [
        "inversion_cop",
        "impresiones",
        "clics",
        "sesiones",
        "conversiones",
        "pedidos_atribuidos",
        "ingresos_atribuidos_cop",
        "costo_por_clic_cop",
        "costo_adquisicion_cop",
        "retorno_publicitario",
    ]

    for column in positive_columns:
        if (marketing[column] <= 0).any():
            raise ValueError(
                f"La columna {column} contiene valores "
                "iguales o inferiores a cero."
            )

    if (
        marketing["clics"]
        > marketing["impresiones"]
    ).any():
        raise ValueError(
            "Los clics no pueden superar las impresiones."
        )

    if (
        marketing["sesiones"]
        > marketing["clics"]
    ).any():
        raise ValueError(
            "Las sesiones no pueden superar los clics."
        )

    if (
        marketing["conversiones"]
        > marketing["sesiones"]
    ).any():
        raise ValueError(
            "Las conversiones no pueden superar las sesiones."
        )

    if (
        marketing["pedidos_atribuidos"]
        > marketing["conversiones"]
    ).any():
        raise ValueError(
            "Los pedidos atribuidos no pueden superar "
            "las conversiones."
        )

    if not marketing["tasa_clics"].between(
        0,
        1,
        inclusive="both",
    ).all():
        raise ValueError(
            "Existen tasas de clics fuera del rango permitido."
        )

    if not marketing["tasa_conversion"].between(
        0,
        1,
        inclusive="both",
    ).all():
        raise ValueError(
            "Existen tasas de conversión fuera del rango."
        )

    if not marketing["datos_sinteticos"].all():
        raise ValueError(
            "Todos los registros deben identificarse "
            "como sintéticos."
        )