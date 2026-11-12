"""Configuración centralizada de registros del proyecto.

Este módulo configura el registro en consola y archivo utilizando
los parámetros establecidos en config/settings.yaml.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from novaretail.config import load_settings, resolve_project_path


DEFAULT_LOG_FORMAT = (
    "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

VALID_LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


class LoggingConfigurationError(RuntimeError):
    """Error generado cuando la configuración de logging es inválida."""


def _get_logging_settings() -> dict[str, Any]:
    """Obtiene y valida la sección de logging.

    Returns:
        Diccionario con la configuración de registros.

    Raises:
        LoggingConfigurationError: Si falta una configuración obligatoria.
    """
    settings = load_settings()
    logging_settings = settings.get("logging")

    if not isinstance(logging_settings, dict):
        raise LoggingConfigurationError(
            "La sección 'logging' de settings.yaml no es válida."
        )

    required_keys = {
        "level",
        "filename",
        "console_enabled",
        "file_enabled",
    }

    missing_keys = required_keys.difference(logging_settings)

    if missing_keys:
        missing_text = ", ".join(sorted(missing_keys))
        raise LoggingConfigurationError(
            "Faltan parámetros de logging en settings.yaml: "
            f"{missing_text}"
        )

    return logging_settings


def _resolve_log_level(level_name: str) -> int:
    """Convierte el nombre del nivel a una constante de logging.

    Args:
        level_name: Nombre del nivel configurado.

    Returns:
        Nivel de logging correspondiente.

    Raises:
        LoggingConfigurationError: Si el nivel no está permitido.
    """
    normalized_level = level_name.strip().upper()

    if normalized_level not in VALID_LOG_LEVELS:
        valid_values = ", ".join(VALID_LOG_LEVELS)
        raise LoggingConfigurationError(
            f"Nivel de logging no válido: {level_name}. "
            f"Valores permitidos: {valid_values}"
        )

    return VALID_LOG_LEVELS[normalized_level]


def _build_formatter() -> logging.Formatter:
    """Construye el formato común de los registros."""
    return logging.Formatter(
        fmt=DEFAULT_LOG_FORMAT,
        datefmt=DEFAULT_DATE_FORMAT,
    )


def _build_console_handler(
    log_level: int,
    formatter: logging.Formatter,
) -> logging.StreamHandler:
    """Construye el manejador de registros para consola."""
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    return console_handler


def _build_file_handler(
    log_level: int,
    formatter: logging.Formatter,
    log_directory: Path,
    log_filename: str,
) -> RotatingFileHandler:
    """Construye el manejador rotativo para archivo.

    Args:
        log_level: Nivel mínimo de registro.
        formatter: Formato aplicado al registro.
        log_directory: Carpeta de almacenamiento.
        log_filename: Nombre del archivo de registro.

    Returns:
        Manejador rotativo configurado.
    """
    log_directory.mkdir(parents=True, exist_ok=True)
    log_file = log_directory / log_filename

    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    return file_handler


def configure_logging(
    logger_name: str = "novaretail",
    force: bool = False,
) -> logging.Logger:
    """Configura y devuelve el logger principal del proyecto.

    Args:
        logger_name: Nombre del logger principal.
        force: Si es verdadero, reemplaza manejadores existentes.

    Returns:
        Logger configurado.

    Raises:
        LoggingConfigurationError: Si la configuración es inválida.
    """
    logging_settings = _get_logging_settings()

    level_name = str(logging_settings["level"])
    log_level = _resolve_log_level(level_name)

    log_filename = str(logging_settings["filename"]).strip()

    if not log_filename:
        raise LoggingConfigurationError(
            "El nombre del archivo de logging no puede estar vacío."
        )

    console_enabled = bool(
        logging_settings["console_enabled"]
    )
    file_enabled = bool(
        logging_settings["file_enabled"]
    )

    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)
    logger.propagate = False

    if logger.handlers and not force:
        return logger

    if force:
        for existing_handler in logger.handlers[:]:
            existing_handler.close()
            logger.removeHandler(existing_handler)

    formatter = _build_formatter()

    if console_enabled:
        console_handler = _build_console_handler(
            log_level=log_level,
            formatter=formatter,
        )
        logger.addHandler(console_handler)

    if file_enabled:
        settings = load_settings()
        logs_path = settings["paths"]["logs"]
        log_directory = resolve_project_path(logs_path)

        file_handler = _build_file_handler(
            log_level=log_level,
            formatter=formatter,
            log_directory=log_directory,
            log_filename=log_filename,
        )
        logger.addHandler(file_handler)

    if not logger.handlers:
        raise LoggingConfigurationError(
            "No se habilitó ningún destino para los registros."
        )

    logger.debug(
        "Sistema de logging configurado. Nivel: %s",
        level_name.upper(),
    )

    return logger


def _normalize_logger_name(name: str) -> str:
    """Normaliza el nombre de un logger secundario.

    Evita producir nombres duplicados como:
    novaretail.novaretail.generation.products

    Args:
        name: Nombre completo o relativo del módulo.

    Returns:
        Nombre normalizado relativo al logger principal.
    """
    normalized_name = name.strip()

    if normalized_name == "novaretail":
        return ""

    prefix = "novaretail."

    if normalized_name.startswith(prefix):
        return normalized_name[len(prefix):]

    return normalized_name


def get_logger(name: str) -> logging.Logger:
    """Obtiene un logger asociado a un módulo del proyecto.

    Args:
        name: Nombre completo o relativo del módulo solicitante.

    Returns:
        Logger configurado para el módulo.
    """
    main_logger = configure_logging()
    normalized_name = _normalize_logger_name(name)

    if not normalized_name:
        return main_logger

    return main_logger.getChild(normalized_name)