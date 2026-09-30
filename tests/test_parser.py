import pytest
from bot.services.parser import parse_natural_drink_text


def test_parse_clear_beer():
    res = parse_natural_drink_text("выпил 0.5 пива")
    assert res.is_drinking_intent is True
    assert res.drink_name == "пиво"
    assert res.volume_ml == 500.0
    assert res.abv == 5.0
    assert not res.needs_volume_clarification
    assert not res.needs_abv_clarification


def test_parse_beer_with_explicit_abv():
    res = parse_natural_drink_text("бахнул 0.5 пива 6.5%")
    assert res.is_drinking_intent is True
    assert res.drink_name == "пиво"
    assert res.volume_ml == 500.0
    assert res.abv == 6.5
    assert not res.needs_volume_clarification
    assert not res.needs_abv_clarification


def test_parse_vodka_shot():
    res = parse_natural_drink_text("накатил 100 водки")
    assert res.is_drinking_intent is True
    assert res.drink_name == "водка"
    assert res.volume_ml == 100.0
    assert res.abv == 40.0
    assert not res.needs_volume_clarification
    assert not res.needs_abv_clarification


def test_parse_missing_volume():
    # User just says "выпил пива" without volume
    res = parse_natural_drink_text("выпил пива")
    assert res.is_drinking_intent is True
    assert res.drink_name == "пиво"
    assert res.abv == 5.0
    assert res.needs_volume_clarification is True


def test_parse_custom_liquor_missing_abv():
    # User says "хлопнул 200 настойки"
    res = parse_natural_drink_text("хлопнул 200 настойки")
    assert res.is_drinking_intent is True
    assert res.volume_ml == 200.0
    # Настойка default is 30.0%
    assert res.abv == 30.0


def test_non_drinking_message():
    res = parse_natural_drink_text("Всем привет, как дела?")
    assert res.is_drinking_intent is False

