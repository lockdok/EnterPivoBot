"""Service for alcohol calculations and drink characteristics."""
import re
from typing import Optional, Tuple, Dict, List

VODKA_STANDARD_ABV = 40.0

# Canonical drink mapping: canonical_name -> (list_of_stems, default_abv)
DRINK_CANONICAL: Dict[str, Tuple[List[str], float]] = {
    # Beers & Ciders
    "пиво": (["пив", "пенн", "лагер", "стаут", "эль"], 5.0),
    "сидр": (["сидр"], 4.5),
    "медовуха": (["медовух"], 5.5),
    
    # Wines
    "вино": (["вин", "каберне", "мерло", "шардоне"], 12.5),
    "шампанское": (["шампан", "игрист", "просекко", "кава"], 11.5),
    "портвейн": (["портвейн", "портвей"], 19.0),
    "вермут": (["вермут", "мартини"], 15.0),
    
    # Strong spirits
    "водка": (["водк", "водоч", "беленьк"], 40.0),
    "виски": (["виск", "скотч", "бурбон"], 40.0),
    "коньяк": (["коньяк", "коньяч", "бренди"], 40.0),
    "ром": (["ром", "ромыч", "бакарди"], 40.0),
    "джин": (["джин"], 40.0),
    "текила": (["текил"], 38.0),
    "самбука": (["самбук"], 40.0),
    "абсент": (["абсент"], 70.0),
    "самогон": (["самогон", "сэм"], 50.0),
    "чача": (["чач"], 50.0),
    "настойка": (["настойк", "наливк"], 30.0),
    "бальзам": (["бальзам"], 40.0),
    "ликер": (["ликер", "ликёр", "бейлис", "егер", "ягер"], 25.0),
    
    # Mixed
    "коктейль": (["коктейл", "аперол"], 12.0),
}

# Compatibility dictionary
KNOWN_DRINKS = {name: info[1] for name, info in DRINK_CANONICAL.items()}


def calculate_vodka_equivalent(volume_ml: float, abv: float) -> float:
    """
    Calculate the equivalent volume of 40% vodka.
    Formula: (volume_ml * abv) / 40.0
    """
    if volume_ml <= 0 or abv <= 0:
        return 0.0
    vodka_ml = (volume_ml * abv) / VODKA_STANDARD_ABV
    return round(vodka_ml, 1)


def get_default_abv_for_drink(drink_name: str) -> Optional[float]:
    """Return default ABV % for recognized drink or None if unknown."""
    cleaned = drink_name.lower().strip()
    for canonical, (stems, abv) in DRINK_CANONICAL.items():
        if canonical in cleaned:
            return abv
        for stem in stems:
            if re.search(r"\b" + re.escape(stem) + r"\w*", cleaned):
                return abv
    return None


def get_default_volume_for_drink(drink_name: str) -> Optional[float]:
    """Return common standard volume (ml) for specific drink types if vessel wasn't specified."""
    cleaned = drink_name.lower().strip()
    if any(k in cleaned for k in ["пиво", "сидр", "медовуха"]):
        return 500.0  # 0.5L
    if any(k in cleaned for k in ["вино", "шампанское", "просекко"]):
        return 150.0  # 150ml glass
    if any(k in cleaned for k in ["водка", "коньяк", "виски", "текила", "ром", "джин", "самбука", "абсент"]):
        return 50.0   # 50ml shot
    return None


def parse_vessel_volume(text: str, drink_name: Optional[str] = None) -> Optional[float]:
    """Parse common Russian vessel keywords into milliliters."""
    lower = text.lower()

    if re.search(r"\b(полторашк\w*)\b", lower):
        return 1500.0

    if re.search(r"\b(пол-литр\w*|поллитр\w*|полулитр\w*)\b", lower):
        return 500.0

    if re.search(r"\b(чекушк\w*)\b", lower):
        return 250.0

    if re.search(r"\b(мерзавчик\w*|шкалик\w*)\b", lower):
        return 100.0

    if re.search(r"\b(стопк\w*|рюмк\w*|шот\w*)\b", lower):
        match = re.search(r"(\d+)\s*(?:стоп|рюмк|шот)", lower)
        count = int(match.group(1)) if match else 1
        return count * 50.0

    if re.search(r"\b(бокал\w*)\b", lower):
        match = re.search(r"(\d+)\s*бокал", lower)
        count = int(match.group(1)) if match else 1
        if drink_name and any(k in drink_name for k in ["пиво", "сидр"]):
            return count * 500.0
        return count * 150.0

    if re.search(r"\b(кружк\w*)\b", lower):
        match = re.search(r"(\d+)\s*круж", lower)
        count = int(match.group(1)) if match else 1
        return count * 500.0

    if re.search(r"\b(банк\w*)\b", lower):
        match = re.search(r"(\d+)\s*бан", lower)
        count = int(match.group(1)) if match else 1
        return count * 450.0

    if re.search(r"\b(бутылк\w*|пузыр\w*)\b", lower):
        match = re.search(r"(\d+)\s*(?:бутыл|пузыр)", lower)
        count = int(match.group(1)) if match else 1
        if drink_name and any(k in drink_name for k in ["вино", "шампанское"]):
            return count * 750.0
        return count * 500.0

    if re.search(r"\b(пинт\w*)\b", lower):
        match = re.search(r"(\d+)\s*пинт", lower)
        count = int(match.group(1)) if match else 1
        return count * 500.0

    return None

