"""Generación reproducible de clientes sintéticos.

Este módulo crea perfiles ficticios y seudonimizados para el caso
académico NovaRetail Colombia S.A.S.

No se generan nombres, documentos de identidad, direcciones,
teléfonos, correos electrónicos ni información bancaria.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from novaretail.config import load_data_generation_config
from novaretail.logging_config import get_logger


LOGGER = get_logger(__name__)

CUSTOMER_COLUMNS = [
    "cliente_id",
    "fecha_registro",
    "segmento",
    "ciudad",
    "departamento",
    "tipo_cliente",
    "canal_adquisicion",
    "rango_edad",
    "estado_cliente",
    "acepta_marketing",
    "datos_sinteticos",
]


LOCATIONS = [
    ("Medellín", "Antioquia"),
    ("Bogotá", "Bogotá D.C."),
    ("Cali", "Valle del Cauca"),
    ("Barranquilla", "Atlántico"),
    ("Cartagena", "Bolívar"),
    ("Bucaramanga", "Santander"),
    ("Pereira", "Risaralda"),
    ("Manizales", "Caldas"),
    ("Santa Marta", "Magdalena"),
    ("Cúcuta", "Norte de Santander"),
    ("Ibagué", "Tolima"),
    ("Villavicencio", "Meta"),
]


LOCATION_PROBABILITIES = [
    0.22,
    0.24,
    0.12,
    0.08,
    0.06,
    0.06,
    0.05,
    0.04,
    0.03,
    0.03,
    0.04,
    0.03,
]


CUSTOMER_TYPES = [
    "Persona",
    "Microempresa",
    "Pequeña empresa",
]


CUSTOMER_TYPE_PROBABILITIES = [
    0.86,
    0.10,
    0.04,
]


ACQUISITION_CHANNELS = [
    "Búsqueda pagada",
    "Redes sociales",
    "Correo electrónico",
    "Afiliados",
    "Tráfico orgánico",
    "Tráfico directo",
]


ACQUISITION_PROBABILITIES = [
    0.23,
    0.25,
    0.08,
    0.07,
    0.22,
    0.15,
]


AGE_RANGES = [
    "18-24",
    "25-34",
    "35-44",
    "45-54",
    "55-64",
    "65 o más",
]


AGE_RANGE_PROBABILITIES = [
    0.15,
    0.32,
    0.25,
    0.16,
    0.08,
    0.04,
]


CUSTOMER_STATES = [
    "Activo",
    "Inactivo",
    "En observación",
]


CUSTOMER_STATE_PROBABILITIES = [
    0.82,
    0.13,
    0.05,
]


SEGMENT_PROBABILITIES = {
    "Nuevo": 0.30,
    "Ocasional": 0.36,
    "Frecuente": 0.24,
    "Alto valor": 0.10,
}


def _validate_configuration(configuration: dict) -> None:
    """Valida los parámetros necesarios para generar clientes.

    Args:
        configuration: Configuración cargada desde YAML.

    Raises:
        ValueError: Si la configuración no permite generar clientes.
    """
    customer_count = configuration["volumes"]["customers"]
    configured_segments = configuration[
        "customer_segments"
    ]["values"]

    if not isinstance(customer_count, int) or customer_count <= 0:
        raise ValueError(
            "La cantidad de clientes debe ser un entero positivo."
        )

    if not configured_segments:
        raise ValueError(
            "Debe existir al menos un segmento de clientes."
        )

    missing_segments = set(
        configured_segments
    ).difference(SEGMENT_PROBABILITIES)

    if missing_segments:
        missing_text = ", ".join(sorted(missing_segments))
        raise ValueError(
            "Existen segmentos sin probabilidad configurada: "
            f"{missing_text}"
        )

    probability_total = sum(
        SEGMENT_PROBABILITIES[segment]
        for segment in configured_segments
    )

    if not np.isclose(probability_total, 1.0):
        raise ValueError(
            "Las probabilidades de los segmentos deben sumar 1."
        )

    if not np.isclose(sum(LOCATION_PROBABILITIES), 1.0):
        raise ValueError(
            "Las probabilidades de ubicación deben sumar 1."
        )

    if not np.isclose(
        sum(CUSTOMER_TYPE_PROBABILITIES),
        1.0,
    ):
        raise ValueError(
            "Las probabilidades de tipo de cliente deben sumar 1."
        )

    if not np.isclose(
        sum(ACQUISITION_PROBABILITIES),
        1.0,
    ):
        raise ValueError(
            "Las probabilidades de canal deben sumar 1."
        )

    if not np.isclose(
        sum(AGE_RANGE_PROBABILITIES),
        1.0,
    ):
        raise ValueError(
            "Las probabilidades de edad deben sumar 1."
        )

    if not np.isclose(
        sum(CUSTOMER_STATE_PROBABILITIES),
        1.0,
    ):
        raise ValueError(
            "Las probabilidades de estado deben sumar 1."
        )


def generate_customers(
    random_seed: int | None = None,
) -> pd.DataFrame:
    """Genera perfiles sintéticos y seudonimizados de clientes.

    Args:
        random_seed: Semilla alternativa. Cuando no se suministra,
            se utiliza la semilla general más un desplazamiento fijo.

    Returns:
        DataFrame con los clientes sintéticos.

    Raises:
        ValueError: Si la configuración o los datos generados
            incumplen los controles definidos.
    """
    configuration = load_data_generation_config()
    _validate_configuration(configuration)

    configured_seed = int(
        configuration["generation"]["random_seed"]
    )

    seed = (
        configured_seed + 100
        if random_seed is None
        else random_seed
    )

    rng = np.random.default_rng(seed)

    customer_count = configuration["volumes"]["customers"]
    configured_segments = configuration[
        "customer_segments"
    ]["values"]

    segment_probabilities = [
        SEGMENT_PROBABILITIES[segment]
        for segment in configured_segments
    ]

    start_date = pd.Timestamp(
        configuration["period"]["start_date"]
    )
    end_date = pd.Timestamp(
        configuration["period"]["end_date"]
    )

    available_days = (end_date - start_date).days

    records: list[dict] = []

    LOGGER.info(
        "Iniciando generación de %s clientes sintéticos.",
        customer_count,
    )

    for customer_number in range(1, customer_count + 1):
        location_index = int(
            rng.choice(
                len(LOCATIONS),
                p=LOCATION_PROBABILITIES,
            )
        )

        city, department = LOCATIONS[location_index]

        segment = str(
            rng.choice(
                configured_segments,
                p=segment_probabilities,
            )
        )

        customer_type = str(
            rng.choice(
                CUSTOMER_TYPES,
                p=CUSTOMER_TYPE_PROBABILITIES,
            )
        )

        acquisition_channel = str(
            rng.choice(
                ACQUISITION_CHANNELS,
                p=ACQUISITION_PROBABILITIES,
            )
        )

        age_range = str(
            rng.choice(
                AGE_RANGES,
                p=AGE_RANGE_PROBABILITIES,
            )
        )

        customer_state = str(
            rng.choice(
                CUSTOMER_STATES,
                p=CUSTOMER_STATE_PROBABILITIES,
            )
        )

        registration_day = int(
            rng.integers(0, available_days + 1)
        )

        registration_date = start_date + pd.Timedelta(
            days=registration_day
        )

        accepts_marketing = bool(
            rng.choice(
                [True, False],
                p=[0.68, 0.32],
            )
        )

        record = {
            "cliente_id": f"CLI-{customer_number:05d}",
            "fecha_registro": registration_date.date(),
            "segmento": segment,
            "ciudad": city,
            "departamento": department,
            "tipo_cliente": customer_type,
            "canal_adquisicion": acquisition_channel,
            "rango_edad": age_range,
            "estado_cliente": customer_state,
            "acepta_marketing": accepts_marketing,
            "datos_sinteticos": True,
        }

        records.append(record)

    customers = pd.DataFrame(
        records,
        columns=CUSTOMER_COLUMNS,
    )

    _validate_generated_customers(
        customers=customers,
        expected_count=customer_count,
        start_date=start_date,
        end_date=end_date,
        allowed_segments=set(configured_segments),
    )

    LOGGER.info(
        "Clientes generados correctamente: %s registros.",
        len(customers),
    )

    return customers


def _validate_generated_customers(
    customers: pd.DataFrame,
    expected_count: int,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    allowed_segments: set[str],
) -> None:
    """Valida los clientes generados antes de devolverlos.

    Args:
        customers: DataFrame generado.
        expected_count: Cantidad esperada.
        start_date: Fecha mínima permitida.
        end_date: Fecha máxima permitida.
        allowed_segments: Segmentos autorizados.

    Raises:
        ValueError: Si los registros incumplen algún control.
    """
    if len(customers) != expected_count:
        raise ValueError(
            "La cantidad de clientes generada no coincide "
            "con la configuración."
        )

    if customers["cliente_id"].isna().any():
        raise ValueError(
            "Se detectaron identificadores de cliente vacíos."
        )

    if customers["cliente_id"].duplicated().any():
        raise ValueError(
            "Se detectaron identificadores de cliente duplicados."
        )

    if not customers["cliente_id"].str.match(
        r"^CLI-\d{5}$"
    ).all():
        raise ValueError(
            "Existen identificadores con formato inválido."
        )

    generated_segments = set(
        customers["segmento"].unique()
    )

    if not generated_segments.issubset(allowed_segments):
        raise ValueError(
            "Se generaron segmentos no autorizados."
        )

    registration_dates = pd.to_datetime(
        customers["fecha_registro"]
    )

    valid_dates = registration_dates.between(
        start_date,
        end_date,
        inclusive="both",
    )

    if not valid_dates.all():
        raise ValueError(
            "Se detectaron fechas de registro fuera del periodo."
        )

    if customers["ciudad"].isna().any():
        raise ValueError(
            "Se detectaron ciudades vacías."
        )

    if customers["departamento"].isna().any():
        raise ValueError(
            "Se detectaron departamentos vacíos."
        )

    if not customers["datos_sinteticos"].all():
        raise ValueError(
            "Todos los clientes deben identificarse como sintéticos."
        )