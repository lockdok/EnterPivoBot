"""Parser for natural language alcohol consumption reports."""
import re
from dataclasses import dataclass
from typing import Optional
from .calculator import DRINK_CANONICAL, get_default_abv_for_drink, parse_vessel_volume

DRINK_VERBS = [
    r"\bвыпил[аои]?\b",
    r"\bнакатил[аои]?\b",
    r"\bбухнул[аои]?\b",
    r"\bбахнул[аои]?\b",
    r"\bхлопнул[аои]?\b",
    r"\bд[её]рнул[аои]?\b",
    r"\bопрокинул[аои]?\b",
    r"\bпринял[аои]?\b",
    r"\bвсадил[аои]?\b",
    r"\bуговорил[аои]?\b",
    r"\bоприходовал[аои]?\b",
    r"\bмахнул[аои]?\b",
    r"\bтяпнул[аои]?\b",
    r"\bзасадил[аои]?\b",
    r"\bхлебнул[аои]?\b",
    r"\bраздавил[аои]?\b",
    r"\bупотребил[аои]?\b",
]

VERB_REGEX = re.compile("|".join(DRINK_VERBS), re.IGNORECASE)


@dataclass
class ParsedDrink:
    is_drinking_intent: bool
    drink_name: Optional[str] = None
    volume_ml: Optional[float] = None
    abv: Optional[float] = None
    needs_volume_clarification: bool = False
    needs_abv_clarification: bool = False


def extract_drink_name(text: str) -> Optional[str]:
    """Find known alcohol names or synonyms in the text and return canonical name."""
    lower = text.lower()
    for canonical_name, (stems, _) in DRINK_CANONICAL.items():
        if canonical_name in lower:
            return canonical_name
        for stem in stems:
            if re.search(r"\b" + re.escape(stem) + r"\w*", lower):
                return canonical_name
    return None


def extract_volume_ml(text: str, drink_name: Optional[str] = None) -> Optional[float]:
    """Extract liquid volume in milliliters from text."""
    lower = text.lower()

    # 1. Check vessels first (бокал, банка, шот, полторашка, etc.)
    vessel_vol = parse_vessel_volume(lower, drink_name)
    if vessel_vol is not None:
        return vessel_vol

    # 2. Liters with explicit unit: e.g. "0.5 л", "0,5л", "1.5 литра", "2 литра"
    match_l = re.search(r"(?<![.,\d])(\d+(?:[.,]\d+)?)\s*(?:л|литр\w*)\b", lower)
    if match_l:
        val = float(match_l.group(1).replace(",", "."))
        return val * 1000.0

    # 3. Milliliters: e.g. "500 мл", "500мл"
    match_ml = re.search(r"(?<![.,\d])(\d+(?:[.,]\d+)?)\s*(?:мл|миллилитр\w*)\b", lower)
    if match_ml:
        return float(match_ml.group(1).replace(",", "."))

    # 4. Grams: e.g. "100 г", "100г", "150 грамм", "150 гр"
    match_g = re.search(r"(?<![.,\d])(\d+(?:[.,]\d+)?)\s*(?:г|гр|грамм\w*)\b", lower)
    if match_g:
        return float(match_g.group(1).replace(",", "."))

    # 5. Small decimal numbers representing liters without unit: e.g. "0.5 пива", "0,33 пива", "1.5 пива"
    match_decimal = re.search(r"(?<![.,\d])(0[.,][234567]\d?|1[.,][05]|2[.,]0)\b", lower)
    if match_decimal:
        val = float(match_decimal.group(1).replace(",", "."))
        return val * 1000.0

    # 6. Integer count before beverage: e.g. "2 пива", "3 пиваса" -> count * 500ml
    match_count_drink = re.search(r"(?<![.,\d])([1-9]\d?)\s*(?:пив\w*|сидр\w*)", lower)
    if match_count_drink:
        count = int(match_count_drink.group(1))
        return count * 500.0

    # 7. Bare numbers: e.g. "выпил 100 водки" or "выпил 500 пива"
    match_bare = re.search(r"(?<![.,\d])(\d{2,4})(?![.,\d])", lower)
    if match_bare:
        val = float(match_bare.group(1))
        if 20 <= val <= 3000:
            return val

    return None


def extract_abv(text: str, drink_name: Optional[str] = None) -> Optional[float]:
    """Extract ABV % from text or fallback to beverage default."""
    lower = text.lower()

    # Percentage: e.g. "5%", "4.5%", "12,5 %"
    match_pct = re.search(r"(\d+(?:[.,]\d+)?)\s*%", lower)
    if match_pct:
        return float(match_pct.group(1).replace(",", "."))

    # Degrees: e.g. "40 градусов", "40°", "40 град"
    match_deg = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:°|град\w*)", lower)
    if match_deg:
        return float(match_deg.group(1).replace(",", "."))

    # Fallback to drink default if known
    if drink_name:
        default_abv = get_default_abv_for_drink(drink_name)
        if default_abv is not None:
            return default_abv

    return None


def parse_natural_drink_text(text: str) -> ParsedDrink:
    """
    Parse a message to detect drinking intent and extract parameters.
    Returns ParsedDrink object with flags for required clarifications.
    """
    cleaned = text.strip()
    has_verb = bool(VERB_REGEX.search(cleaned))
    drink_name = extract_drink_name(cleaned)

    # Intent is detected if there is a drinking verb or explicit drink mention in a logging-like context
    is_intent = has_verb or (drink_name is not None and bool(re.search(r"(\d+|\bбокал\w*|\bбутылк\w*|\bшот\w*|\bрюмк\w*|\+)", cleaned, re.IGNORECASE)))

    if not is_intent:
        return ParsedDrink(is_drinking_intent=False)

    volume_ml = extract_volume_ml(cleaned, drink_name)
    abv = extract_abv(cleaned, drink_name)

    effective_drink = drink_name or "алкоголь"

    needs_volume = volume_ml is None or volume_ml <= 0
    needs_abv = abv is None or abv <= 0

    return ParsedDrink(
        is_drinking_intent=True,
        drink_name=effective_drink,
        volume_ml=volume_ml,
        abv=abv,
        needs_volume_clarification=needs_volume,
        needs_abv_clarification=needs_abv
    )

