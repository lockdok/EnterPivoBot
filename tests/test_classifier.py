import pytest
from bot.services.classifier import (
     classify_drink,
     get_category_emoji,
     calculate_pure_alcohol_grams,
     CATEGORY_EMOJIS
 )


def test_classify_by_keywords():
    assert classify_drink("Светлое пиво", 4.5) == "пиво"
    assert classify_drink("IPA крафт", 6.8) == "пиво"
    assert classify_drink("Красное сухое вино", 13.0) == "вино"
    assert classify_drink("Шампанское Брют", 11.5) == "вино"
    assert classify_drink("Яблочный сидр", 5.0) == "вино"
    assert classify_drink("Водка Столичная", 40.0) == "крепкий"
    assert classify_drink("Шот виски", 40.0) == "крепкий"
    assert classify_drink("Коньяк Арарат", 40.0) == "крепкий"
    assert classify_drink("Джин-тоник", 7.0) == "слабоалкогольный"
    assert classify_drink("Радлер грейпфрут", 2.5) == "слабоалкогольный"


def test_classify_by_abv_fallback():
    # If name doesn't match known keywords
    assert classify_drink("Неизвестный напиток", 2.0) == "слабоалкогольный"
    assert classify_drink("Крафтовая жижа", 5.5) == "пиво"
    assert classify_drink("Домашний настой", 14.0) == "вино"
    assert classify_drink("Зелье Бабы Яги", 50.0) == "крепкий"
    assert classify_drink("Вода", 0.0) == "другое"


def test_calculate_pure_alcohol_grams():
    # 500 ml of 5% beer: 500 * 0.05 * 0.789 = 19.725 -> 19.73 g
    grams = calculate_pure_alcohol_grams(500.0, 5.0)
    assert grams == 19.73

    # 100 ml of 40% vodka: 100 * 0.40 * 0.789 = 31.56 g
    grams_vodka = calculate_pure_alcohol_grams(100.0, 40.0)
    assert grams_vodka == 31.56


def test_category_emojis():
    assert get_category_emoji("пиво") == "🍺"
    assert get_category_emoji("вино") == "🍷"
    assert get_category_emoji("крепкий") == "🥃"
    assert get_category_emoji("слабоалкогольный") == "🫧"
    assert get_category_emoji("другое") == "🍸"
    assert get_category_emoji("unknown_category") == "🍸"
