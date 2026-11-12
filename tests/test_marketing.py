"""Pruebas automáticas para el generador de marketing sintético."""

from __future__ import annotations

import pandas as pd
import pytest

from novaretail.config import load_data_generation_config
from novaretail.generation.marketing import (
    MARKETING_COLUMNS,
    generate_marketing,
)


@pytest.fixture(scope="module")
def marketing() -> pd.DataFrame:
    """Genera una sola vez los registros de marketing."""
    return generate_marketing()


def test_marketing_has_expected_columns(
    marketing: pd.DataFrame,
) -> None:
    """Comprueba el nombre y orden de las columnas."""
    assert marketing.columns.tolist() == MARKETING_COLUMNS


def test_marketing_has_expected_dimensions(
    marketing: pd.DataFrame,
) -> None:
    """Comprueba la cantidad esperada de registros."""
    configuration = load_data_generation_config()

    expected_months = pd.date_range(
        start=configuration["period"]["start_date"],
        end=configuration["period"]["end_date"],
        freq="MS",
    ).size

    expected_channels = configuration["volumes"][
        "marketing_channels"
    ]

    expected_records = expected_months * expected_channels

    assert marketing.shape == (
        expected_records,
        len(MARKETING_COLUMNS),
    )


def test_marketing_contains_expected_periods(
    marketing: pd.DataFrame,
) -> None:
    """Comprueba la cobertura de los 36 periodos."""
    configuration = load_data_generation_config()

    expected_periods = pd.date_range(
        start=configuration["period"]["start_date"],
        end=configuration["period"]["end_date"],
        freq="MS",
    ).strftime("%Y-%m")

    generated_periods = sorted(
        marketing["periodo"].unique()
    )

    assert generated_periods == sorted(
        expected_periods.tolist()
    )


def test_marketing_contains_authorized_channels(
    marketing: pd.DataFrame,
) -> None:
    """Comprueba que solo existan canales configurados."""
    configuration = load_data_generation_config()

    expected_channels = set(
        configuration["marketing"]["channels"]
    )

    generated_channels = set(
        marketing["canal"].unique()
    )

    assert generated_channels == expected_channels


def test_each_period_contains_all_channels(
    marketing: pd.DataFrame,
) -> None:
    """Comprueba la cantidad de canales en cada periodo."""
    configuration = load_data_generation_config()

    expected_channel_count = configuration["volumes"][
        "marketing_channels"
    ]

    channels_per_period = marketing.groupby(
        "periodo"
    )["canal"].nunique()

    assert (
        channels_per_period == expected_channel_count
    ).all()


def test_campaign_identifiers_are_unique(
    marketing: pd.DataFrame,
) -> None:
    """Comprueba la integridad de los identificadores."""
    assert marketing["campania_id"].notna().all()
    assert marketing["campania_id"].is_unique
    assert marketing["campania_id"].str.match(
        r"^CAM-\d{6}-\d{2}$"
    ).all()


def test_marketing_has_one_record_per_period_and_channel(
    marketing: pd.DataFrame,
) -> None:
    """Comprueba la unicidad de periodo y canal."""
    duplicated_records = marketing.duplicated(
        subset=["periodo", "canal"]
    )

    assert not duplicated_records.any()


def test_marketing_investment_is_positive(
    marketing: pd.DataFrame,
) -> None:
    """Comprueba que la inversión sea positiva."""
    assert (
        marketing["inversion_cop"] > 0
    ).all()


def test_marketing_impressions_are_positive(
    marketing: pd.DataFrame,
) -> None:
    """Comprueba que existan impresiones."""
    assert (
        marketing["impresiones"] > 0
    ).all()


def test_clicks_do_not_exceed_impressions(
    marketing: pd.DataFrame,
) -> None:
    """Comprueba la relación entre clics e impresiones."""
    assert (
        marketing["clics"]
        <= marketing["impresiones"]
    ).all()


def test_sessions_do_not_exceed_clicks(
    marketing: pd.DataFrame,
) -> None:
    """Comprueba la relación entre sesiones y clics."""
    assert (
        marketing["sesiones"]
        <= marketing["clics"]
    ).all()


def test_conversions_do_not_exceed_sessions(
    marketing: pd.DataFrame,
) -> None:
    """Comprueba la relación entre conversiones y sesiones."""
    assert (
        marketing["conversiones"]
        <= marketing["sesiones"]
    ).all()


def test_attributed_orders_do_not_exceed_conversions(
    marketing: pd.DataFrame,
) -> None:
    """Comprueba pedidos atribuidos frente a conversiones."""
    assert (
        marketing["pedidos_atribuidos"]
        <= marketing["conversiones"]
    ).all()


def test_attributed_revenue_is_positive(
    marketing: pd.DataFrame,
) -> None:
    """Comprueba que los ingresos atribuidos sean positivos."""
    assert (
        marketing["ingresos_atribuidos_cop"] > 0
    ).all()


def test_cost_per_click_is_correct(
    marketing: pd.DataFrame,
) -> None:
    """Comprueba el cálculo del costo por clic."""
    expected_cost = (
        marketing["inversion_cop"]
        / marketing["clics"]
    ).round(2)

    pd.testing.assert_series_equal(
        marketing["costo_por_clic_cop"],
        expected_cost,
        check_names=False,
    )


def test_click_rate_is_correct(
    marketing: pd.DataFrame,
) -> None:
    """Comprueba la tasa de clics."""
    expected_rate = (
        marketing["clics"]
        / marketing["impresiones"]
    ).round(4)

    pd.testing.assert_series_equal(
        marketing["tasa_clics"],
        expected_rate,
        check_names=False,
    )


def test_conversion_rate_is_correct(
    marketing: pd.DataFrame,
) -> None:
    """Comprueba la tasa de conversión."""
    expected_rate = (
        marketing["conversiones"]
        / marketing["sesiones"]
    ).round(4)

    pd.testing.assert_series_equal(
        marketing["tasa_conversion"],
        expected_rate,
        check_names=False,
    )


def test_acquisition_cost_is_correct(
    marketing: pd.DataFrame,
) -> None:
    """Comprueba el costo de adquisición."""
    expected_cost = (
        marketing["inversion_cop"]
        / marketing["pedidos_atribuidos"]
    ).round(2)

    pd.testing.assert_series_equal(
        marketing["costo_adquisicion_cop"],
        expected_cost,
        check_names=False,
    )


def test_advertising_return_is_correct(
    marketing: pd.DataFrame,
) -> None:
    """Comprueba el retorno publicitario."""
    expected_return = (
        marketing["ingresos_atribuidos_cop"]
        / marketing["inversion_cop"]
    ).round(4)

    pd.testing.assert_series_equal(
        marketing["retorno_publicitario"],
        expected_return,
        check_names=False,
    )


def test_click_rates_are_inside_valid_range(
    marketing: pd.DataFrame,
) -> None:
    """Comprueba que las tasas de clics estén entre cero y uno."""
    assert marketing["tasa_clics"].between(
        0.0,
        1.0,
        inclusive="both",
    ).all()


def test_conversion_rates_are_inside_valid_range(
    marketing: pd.DataFrame,
) -> None:
    """Comprueba que las conversiones estén entre cero y uno."""
    assert marketing["tasa_conversion"].between(
        0.0,
        1.0,
        inclusive="both",
    ).all()


def test_all_marketing_records_are_synthetic(
    marketing: pd.DataFrame,
) -> None:
    """Comprueba la identificación de datos sintéticos."""
    assert marketing["datos_sinteticos"].all()


def test_marketing_is_reproducible(
    marketing: pd.DataFrame,
) -> None:
    """Comprueba que la misma semilla produzca el mismo resultado."""
    second_marketing = generate_marketing()

    pd.testing.assert_frame_equal(
        marketing,
        second_marketing,
    )


def test_different_seed_changes_marketing(
    marketing: pd.DataFrame,
) -> None:
    """Comprueba que otra semilla cambie los resultados."""
    alternative_marketing = generate_marketing(
        random_seed=20261605,
    )

    assert not marketing.equals(
        alternative_marketing
    )