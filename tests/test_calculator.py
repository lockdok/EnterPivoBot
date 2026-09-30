import pytest
from bot.services.calculator import calculate_vodka_equivalent, get_default_abv_for_drink, parse_vessel_volume


def test_vodka_equivalent_beer():
    # 500 ml beer 5% -> (500 * 5) / 40 = 62.5 ml vodka
    assert calculate_vodka_equivalent(500, 5.0) == 62.5


def test_vodka_equivalent_wine():
    # 150 ml wine 12.5% -> (150 * 12.5) / 40 = 46.875 -> 46.9 ml vodka
    assert calculate_vodka_equivalent(150, 12.5) == 46.9


def test_vodka_equivalent_spirits():
    # 100 ml vodka 40% -> 100 ml vodka
    assert calculate_vodka_equivalent(100, 40.0) == 100.0
    # 50 ml absinthe 70% -> (50 * 70) / 40 = 87.5 ml vodka
    assert calculate_vodka_equivalent(50, 70.0) == 87.5


def test_vodka_equivalent_zero_or_negative():
    assert calculate_vodka_equivalent(0, 40.0) == 0.0
    assert calculate_vodka_equivalent(500, 0) == 0.0
    assert calculate_vodka_equivalent(-500, 40.0) == 0.0


def test_default_abv_lookup():
    assert get_default_abv_for_drink("пиво") == 5.0
    assert get_default_abv_for_drink("вино") == 12.5
    assert get_default_abv_for_drink("водка") == 40.0
    assert get_default_abv_for_drink("виски") == 40.0
    assert get_default_abv_for_drink("неведомая жижа") is None


def test_parse_vessel_volume():
    assert parse_vessel_volume("выпил бокал вина", "вино") == 150.0
    assert parse_vessel_volume("выпил бокал пива", "пиво") == 500.0
    assert parse_vessel_volume("накатил рюмку водки", "водка") == 50.0
    assert parse_vessel_volume("бахнул чекушку", "водка") == 250.0
    assert parse_vessel_volume("выпил банку пива", "пиво") == 450.0
    assert parse_vessel_volume("раздавил бутылку вина", "вино") == 750.0

