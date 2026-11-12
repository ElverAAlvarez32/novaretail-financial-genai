"""Generación reproducible del catálogo sintético de productos.

Este módulo crea productos ficticios para NovaRetail Colombia S.A.S.
Los registros generados se utilizan exclusivamente con fines académicos.

Una parte del catálogo se encuentra disponible desde el inicio del
periodo y otra parte se incorpora gradualmente como nuevos lanzamientos.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from novaretail.config import load_data_generation_config
from novaretail.logging_config import get_logger


LOGGER = get_logger(__name__)

PRODUCT_COLUMNS = [
    "producto_id",
    "nombre_generico",
    "categoria",
    "subcategoria",
    "marca_ficticia",
    "precio_lista_cop",
    "costo_estandar_cop",
    "margen_objetivo",
    "proveedor_id",
    "fecha_ingreso",
    "estado_producto",
    "datos_sinteticos",
]


SUBCATEGORIES = {
    "Tecnología": [
        "Audio",
        "Accesorios móviles",
        "Periféricos",
        "Almacenamiento",
        "Dispositivos inteligentes",
    ],
    "Hogar": [
        "Organización",
        "Decoración",
        "Iluminación",
        "Limpieza",
        "Textiles",
    ],
    "Cocina": [
        "Utensilios",
        "Electrodomésticos pequeños",
        "Almacenamiento de alimentos",
        "Vajilla",
        "Preparación",
    ],
    "Cuidado personal": [
        "Cuidado capilar",
        "Cuidado facial",
        "Higiene",
        "Bienestar",
        "Accesorios personales",
    ],
    "Oficina": [
        "Papelería",
        "Ergonomía",
        "Organización de escritorio",
        "Escritura",
        "Accesorios de oficina",
    ],
    "Accesorios": [
        "Viaje",
        "Bolsos",
        "Organizadores",
        "Accesorios tecnológicos",
        "Uso cotidiano",
    ],
}


GENERIC_NAMES = {
    "Tecnología": [
        "Audífonos",
        "Cargador",
        "Teclado",
        "Mouse",
        "Memoria portátil",
        "Soporte para dispositivo",
        "Parlante",
        "Adaptador",
    ],
    "Hogar": [
        "Organizador",
        "Lámpara",
        "Cojín",
        "Canasta",
        "Set de limpieza",
        "Repisa",
        "Contenedor",
        "Cobija",
    ],
    "Cocina": [
        "Juego de utensilios",
        "Recipiente",
        "Cafetera",
        "Sartén",
        "Set de cuchillos",
        "Vaso térmico",
        "Balanza",
        "Tabla de cocina",
    ],
    "Cuidado personal": [
        "Cepillo",
        "Secador",
        "Masajeador",
        "Espejo",
        "Kit de cuidado",
        "Organizador personal",
        "Máquina de cuidado",
        "Difusor",
    ],
    "Oficina": [
        "Cuaderno",
        "Silla ergonómica",
        "Organizador de escritorio",
        "Lámpara de escritorio",
        "Set de escritura",
        "Base para portátil",
        "Archivador",
        "Calculadora",
    ],
    "Accesorios": [
        "Bolso",
        "Estuche",
        "Organizador de viaje",
        "Soporte",
        "Billetera",
        "Mochila",
        "Portadocumentos",
        "Accesorio multipropósito",
    ],
}


FICTIONAL_BRANDS = [
    "NovaHome",
    "NovaTech",
    "NovaLife",
    "NovaOffice",
    "NovaEssentials",
    "AndesLab",
    "Urbania",
    "Prisma",
]


PRODUCT_STATES = [
    "Activo",
    "Activo",
    "Activo",
    "Activo",
    "En lanzamiento",
    "Descontinuado",
]


INITIAL_CATALOG_RATE = 0.70


def _round_to_thousand(value: float) -> int:
    """Redondea un valor monetario al millar más cercano.

    Args:
        value: Valor monetario sin redondear.

    Returns:
        Valor entero redondeado al millar más cercano.
    """
    return int(round(value / 1_000) * 1_000)


def _validate_configuration(
    configuration: dict,
) -> None:
    """Valida los parámetros necesarios para generar productos.

    Args:
        configuration: Configuración cargada desde YAML.

    Raises:
        ValueError: Si un parámetro requerido es inválido.
    """
    product_count = configuration["volumes"]["products"]
    categories = configuration["product_catalog"]["categories"]

    minimum_price = configuration["pricing"][
        "minimum_product_price_cop"
    ]
    maximum_price = configuration["pricing"][
        "maximum_product_price_cop"
    ]
    minimum_margin = configuration["pricing"][
        "minimum_gross_margin_rate"
    ]
    maximum_margin = configuration["pricing"][
        "maximum_gross_margin_rate"
    ]

    if not isinstance(product_count, int) or product_count <= 0:
        raise ValueError(
            "La cantidad de productos debe ser un entero positivo."
        )

    if not categories:
        raise ValueError(
            "Debe existir al menos una categoría de productos."
        )

    unknown_categories = set(categories).difference(
        SUBCATEGORIES
    )

    if unknown_categories:
        unknown_text = ", ".join(
            sorted(unknown_categories)
        )
        raise ValueError(
            "Existen categorías sin subcategorías configuradas: "
            f"{unknown_text}"
        )

    if minimum_price <= 0:
        raise ValueError(
            "El precio mínimo debe ser mayor que cero."
        )

    if maximum_price <= minimum_price:
        raise ValueError(
            "El precio máximo debe ser mayor que el precio mínimo."
        )

    if not 0 < minimum_margin < maximum_margin < 1:
        raise ValueError(
            "Los márgenes deben cumplir: "
            "0 < mínimo < máximo < 1."
        )

    if not 0 < INITIAL_CATALOG_RATE <= 1:
        raise ValueError(
            "La proporción del catálogo inicial debe estar "
            "entre cero y uno."
        )


def _generate_entry_date(
    product_number: int,
    initial_product_count: int,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    rng: np.random.Generator,
) -> pd.Timestamp:
    """Genera la fecha de ingreso de un producto.

    Los productos del catálogo inicial reciben como fecha de ingreso
    el primer día del proyecto. Los productos restantes ingresan
    gradualmente durante el periodo de análisis.

    Args:
        product_number: Número consecutivo del producto.
        initial_product_count: Cantidad del catálogo inicial.
        start_date: Fecha inicial del proyecto.
        end_date: Fecha final del proyecto.
        rng: Generador aleatorio reproducible.

    Returns:
        Fecha de ingreso del producto.
    """
    if product_number <= initial_product_count:
        return start_date

    first_launch_date = start_date + pd.offsets.MonthBegin(1)
    available_days = (end_date - first_launch_date).days

    day_offset = int(
        rng.integers(0, available_days + 1)
    )

    return first_launch_date + pd.Timedelta(
        days=day_offset
    )


def generate_products(
    random_seed: int | None = None,
) -> pd.DataFrame:
    """Genera el catálogo sintético de productos.

    Args:
        random_seed: Semilla alternativa. Cuando no se suministra,
            se utiliza la definida en data_generation.yaml.

    Returns:
        DataFrame con el catálogo sintético validado.

    Raises:
        ValueError: Si la configuración contiene valores inválidos.
    """
    configuration = load_data_generation_config()
    _validate_configuration(configuration)

    configured_seed = configuration["generation"]["random_seed"]
    seed = configured_seed if random_seed is None else random_seed
    rng = np.random.default_rng(seed)

    product_count = configuration["volumes"]["products"]
    categories = configuration["product_catalog"]["categories"]

    minimum_price = configuration["pricing"][
        "minimum_product_price_cop"
    ]
    maximum_price = configuration["pricing"][
        "maximum_product_price_cop"
    ]
    minimum_margin = configuration["pricing"][
        "minimum_gross_margin_rate"
    ]
    maximum_margin = configuration["pricing"][
        "maximum_gross_margin_rate"
    ]

    start_date = pd.Timestamp(
        configuration["period"]["start_date"]
    )
    end_date = pd.Timestamp(
        configuration["period"]["end_date"]
    )

    initial_product_count = int(
        round(product_count * INITIAL_CATALOG_RATE)
    )

    initial_product_count = max(
        initial_product_count,
        len(categories),
    )

    records: list[dict] = []

    LOGGER.info(
        "Iniciando generación de %s productos sintéticos.",
        product_count,
    )

    LOGGER.info(
        "Catálogo inicial disponible en %s: %s productos.",
        start_date.date(),
        initial_product_count,
    )

    for product_number in range(1, product_count + 1):
        category = str(rng.choice(categories))
        subcategory = str(
            rng.choice(SUBCATEGORIES[category])
        )
        generic_name = str(
            rng.choice(GENERIC_NAMES[category])
        )
        brand = str(rng.choice(FICTIONAL_BRANDS))

        raw_price = float(
            rng.uniform(
                minimum_price,
                maximum_price,
            )
        )

        list_price = max(
            _round_to_thousand(raw_price),
            minimum_price,
        )

        target_margin = float(
            rng.uniform(
                minimum_margin,
                maximum_margin,
            )
        )

        standard_cost = _round_to_thousand(
            list_price * (1 - target_margin)
        )

        calculated_margin = round(
            (list_price - standard_cost) / list_price,
            4,
        )

        entry_date = _generate_entry_date(
            product_number=product_number,
            initial_product_count=initial_product_count,
            start_date=start_date,
            end_date=end_date,
            rng=rng,
        )

        supplier_number = int(rng.integers(1, 26))
        product_state = str(rng.choice(PRODUCT_STATES))

        product_id = f"PROD-{product_number:04d}"
        supplier_id = f"PROV-{supplier_number:03d}"

        record = {
            "producto_id": product_id,
            "nombre_generico": (
                f"{generic_name} {brand} {product_number:03d}"
            ),
            "categoria": category,
            "subcategoria": subcategory,
            "marca_ficticia": brand,
            "precio_lista_cop": list_price,
            "costo_estandar_cop": standard_cost,
            "margen_objetivo": calculated_margin,
            "proveedor_id": supplier_id,
            "fecha_ingreso": entry_date.date(),
            "estado_producto": product_state,
            "datos_sinteticos": True,
        }

        records.append(record)

    products = pd.DataFrame(
        records,
        columns=PRODUCT_COLUMNS,
    )

    _validate_generated_products(
        products=products,
        expected_count=product_count,
        minimum_price=minimum_price,
        maximum_price=maximum_price,
        minimum_margin=minimum_margin,
        maximum_margin=maximum_margin,
        project_start_date=start_date,
        initial_product_count=initial_product_count,
    )

    LOGGER.info(
        "Catálogo generado correctamente: %s productos.",
        len(products),
    )

    return products


def _validate_generated_products(
    products: pd.DataFrame,
    expected_count: int,
    minimum_price: int,
    maximum_price: int,
    minimum_margin: float,
    maximum_margin: float,
    project_start_date: pd.Timestamp,
    initial_product_count: int,
) -> None:
    """Valida el catálogo generado antes de devolverlo.

    Args:
        products: Catálogo generado.
        expected_count: Cantidad esperada de productos.
        minimum_price: Precio mínimo configurado.
        maximum_price: Precio máximo configurado.
        minimum_margin: Margen mínimo configurado.
        maximum_margin: Margen máximo configurado.
        project_start_date: Fecha inicial del proyecto.
        initial_product_count: Cantidad esperada en el catálogo inicial.

    Raises:
        ValueError: Si el catálogo incumple controles básicos.
    """
    if len(products) != expected_count:
        raise ValueError(
            "La cantidad generada no coincide con la configuración."
        )

    if products["producto_id"].duplicated().any():
        raise ValueError(
            "Se detectaron identificadores de producto duplicados."
        )

    if products["producto_id"].isna().any():
        raise ValueError(
            "Se detectaron identificadores de producto vacíos."
        )

    price_is_valid = products["precio_lista_cop"].between(
        minimum_price,
        maximum_price,
        inclusive="both",
    )

    if not price_is_valid.all():
        raise ValueError(
            "Se detectaron precios fuera del rango permitido."
        )

    cost_is_valid = (
        products["costo_estandar_cop"]
        < products["precio_lista_cop"]
    )

    if not cost_is_valid.all():
        raise ValueError(
            "Se detectaron costos iguales o superiores al precio."
        )

    margin_tolerance = 0.01

    margin_is_valid = products["margen_objetivo"].between(
        minimum_margin - margin_tolerance,
        maximum_margin + margin_tolerance,
        inclusive="both",
    )

    if not margin_is_valid.all():
        raise ValueError(
            "Se detectaron márgenes fuera del rango permitido."
        )

    entry_dates = pd.to_datetime(
        products["fecha_ingreso"]
    )

    initial_catalog_size = int(
        (entry_dates == project_start_date).sum()
    )

    if initial_catalog_size != initial_product_count:
        raise ValueError(
            "La cantidad de productos del catálogo inicial "
            "no coincide con la esperada."
        )

    if initial_catalog_size == 0:
        raise ValueError(
            "Debe existir un catálogo disponible desde "
            "la fecha inicial."
        )

    if not products["datos_sinteticos"].all():
        raise ValueError(
            "Todos los productos deben identificarse "
            "como sintéticos."
        )