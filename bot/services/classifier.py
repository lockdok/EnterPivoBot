"""Drink category classifier based on name keywords and ABV."""

BEER_KEYWORDS = {
    "пиво", "эль", "лагер", "стаут", "портер", "пейл", "пшеничное", "крафт", "светлое", "тёмное", "темное",
    "ale", "lager", "stout", "porter", "beer", "ipa", "wheat", "pilsner", "пилснер", "weizen",
}
WINE_KEYWORDS = {
    "вино", "шампанское", "просекко", "сидр", "мидори", "каберне", "мерло", "совиньон", "шардоне",
    "розе", "херес", "вермут", "мартини", "глинтвейн", "портвейн",
    "wine", "champagne", "prosecco", "cider", "rose",
}
SPIRITS_KEYWORDS = {
    "водка", "коньяк", "виски", "ром", "текила", "джин", "абсент", "ликер", "бренди", "самогон",
    "настойка", "граппа", "кальвадос", "арманьяк", "бурбон", "скотч",
    "vodka", "whiskey", "whisky", "cognac", "rum", "tequila", "gin", "absinthe", "liqueur", "brandy",
}
SOFT_KEYWORDS = {
    "пивной напиток", "радлер", "джин-тоник", "коктейль", "энергетик", "алкоэнергетик",
    "мохито", "лонг", "spritzer",
}

CATEGORY_EMOJIS: dict[str, str] = {
    "пиво": "🍺",
    "вино": "🍷",
    "крепкий": "🥃",
    "слабоалкогольный": "🫧",
    "другое": "🍸",
}


def classify_drink(drink_name: str, abv: float) -> str:
    """Classify a drink into a category based on name keywords and ABV.

    Returns one of: 'пиво', 'вино', 'крепкий', 'слабоалкогольный', 'другое'.
    """
    name_lower = drink_name.lower().strip()

    # Explicit compound/cocktail keyword matching takes priority
    for kw in SOFT_KEYWORDS:
        if kw in name_lower:
            return "слабоалкогольный"

    for kw in SPIRITS_KEYWORDS:
        if kw in name_lower:
            return "крепкий"

    for kw in BEER_KEYWORDS:
        if kw in name_lower:
            return "пиво"

    for kw in WINE_KEYWORDS:
        if kw in name_lower:
            return "вино"

    # Fall back to ABV ranges
    if abv <= 0:
        return "другое"
    if abv <= 3.0:
        return "слабоалкогольный"
    if abv <= 9.0:
        return "пиво"
    if abv <= 20.0:
        return "вино"
    return "крепкий"


def get_category_emoji(category: str) -> str:
    """Return the emoji for a drink category."""
    return CATEGORY_EMOJIS.get(category, "🍸")


def calculate_pure_alcohol_grams(volume_ml: float, abv: float) -> float:
    """Calculate grams of pure alcohol.

    Formula: volume_ml × (abv / 100) × 0.789 (density of ethanol)
    """
    return round(volume_ml * (abv / 100) * 0.789, 2)

