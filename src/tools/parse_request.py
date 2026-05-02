from __future__ import annotations

import re
from typing import Optional

from pydantic import BaseModel

from src.tools.base import Err, Ok, Result, ToolError, tool_with_retry

CUISINE_MAP: dict[str, str] = {
    "sri lankan": "sri_lankan",
    "sri_lankan": "sri_lankan",
    "srilankan": "sri_lankan",
    "lanka": "sri_lankan",
    "ceylon": "sri_lankan",
    "indian": "indian",
    "india": "indian",
    "curry": "indian",
    "biryani": "indian",
    "tandoori": "indian",
    "chinese": "chinese",
    "china": "chinese",
    "dim sum": "chinese",
    "dimsum": "chinese",
    "italian": "italian",
    "italy": "italian",
    "pizza": "italian",
    "pasta": "italian",
    "risotto": "italian",
    "american": "american",
    "burger": "american",
    "bbq": "american",
    "barbeque": "american",
    "japanese": "japanese",
    "japan": "japanese",
    "sushi": "japanese",
    "ramen": "japanese",
    "thai": "thai",
    "thailand": "thai",
}

DIETARY_EXCLUDE_KEYWORDS: dict[str, str] = {
    "no seafood": "seafood",
    "no fish": "seafood",
    "no shrimp": "seafood",
    "no prawn": "seafood",
    "no pork": "pork",
    "no ham": "pork",
    "no bacon": "pork",
    "no dairy": "dairy",
    "no milk": "dairy",
    "no cheese": "dairy",
    "no gluten": "gluten",
    "no meat": "meat",
    "no beef": "beef",
    "no chicken": "chicken",
    "no egg": "egg",
    "no eggs": "egg",
    "no nuts": "nuts",
}

DIETARY_REQUIRE_KEYWORDS: dict[str, str] = {
    "vegan": "vegan",
    "vegetarian": "vegetarian",
    "veggie": "vegetarian",
    "plant-based": "vegan",
    "plant based": "vegan",
    "halal": "halal",
    "kosher": "kosher",
    "gluten free": "gluten_free",
    "gluten-free": "gluten_free",
}

SPICE_MAP: dict[str, str] = {
    "mild": "mild",
    "not spicy": "mild",
    "not too spicy": "mild",
    "medium": "medium",
    "spicy": "hot",
    "very spicy": "hot",
    "extra spicy": "hot",
    "hot": "hot",
}


class ParseRequestInput(BaseModel):
    raw_text: str
    default_city: str = "Colombo"


CATEGORY_MAP: dict[str, str] = {
    "dessert": "dessert",
    "desserts": "dessert",
    "sweet": "dessert",
    "sweets": "dessert",
    "starter": "starter",
    "starters": "starter",
    "appetizer": "starter",
    "appetizers": "starter",
    "entree": "starter",
    "drink": "drink",
    "drinks": "drink",
    "beverage": "drink",
    "beverages": "drink",
    "juice": "drink",
    "main": "main",
    "mains": "main",
    "main course": "main",
    "main dish": "main",
    "main dishes": "main",
    "side": "side",
    "sides": "side",
    "side dish": "side",
    "side dishes": "side",
}


class ParseRequestOutput(BaseModel):
    budget_lkr: float
    party_size: int
    cuisines: list[str]
    categories: list[str]
    dietary_exclude: list[str]
    dietary_require: list[str]
    spice_preference: Optional[str]
    city: str


@tool_with_retry(timeout_s=10, retries=2)
def parse_request(inp: ParseRequestInput) -> Result[ParseRequestOutput, ToolError]:
    """Extract structured order parameters from raw natural-language text.

    Uses regex and keyword matching for deterministic field extraction.
    Budget, party size, and known keywords are parsed without LLM involvement
    so the tool is fast, testable, and injection-resistant.

    Args:
        inp: Raw user text and optional default city override.

    Returns:
        Ok(ParseRequestOutput) with extracted fields, or
        Err(ToolError) if budget cannot be determined.

    Example:
        >>> result = parse_request(ParseRequestInput(
        ...     raw_text="LKR 3000 for 2 people, spicy Sri Lankan, no seafood"
        ... ))
        >>> result.is_ok()
        True
    """
    text = inp.raw_text.lower().strip()

    if len(text) > 5000:
        return Err(ToolError(tool="parse_request", kind="validation", message="Input too long"))
    if len(text) < 3:
        return Err(ToolError(tool="parse_request", kind="validation", message="Request is too short to parse"))

    budget = _extract_budget(text)
    if budget is None or budget <= 0:
        budget = 99999.0  # no budget stated - no limit

    party_size = _extract_party_size(text)
    cuisines = _extract_cuisines(text)
    categories = _extract_categories(text)
    dietary_exclude = _extract_dietary_exclude(text)
    dietary_require = _extract_dietary_require(text)
    spice = _extract_spice(text)
    city = _extract_city(text, inp.default_city)

    return Ok(ParseRequestOutput(
        budget_lkr=budget,
        party_size=party_size,
        cuisines=cuisines,
        categories=categories,
        dietary_exclude=dietary_exclude,
        dietary_require=dietary_require,
        spice_preference=spice,
        city=city,
    ))


def _extract_budget(text: str) -> Optional[float]:
    # Currency prefix then number + optional k — lookahead ensures we stop at word boundary
    m = re.search(r"(?:lkr|rs\.?|rupees?)\s*([0-9][0-9,]*(?:\.[0-9]+)?)(k)?(?=[\s,.]|$)", text)
    if m:
        val = float(m.group(1).replace(",", ""))
        if m.group(2) == "k":
            val *= 1000
        return val

    # Number + optional k then currency word
    m = re.search(r"([0-9][0-9,]*(?:\.[0-9]+)?)(k)?\s*(?:lkr|rupees?|rs\.?)(?=[\s,.]|$)", text)
    if m:
        val = float(m.group(1).replace(",", ""))
        if m.group(2) == "k":
            val *= 1000
        return val

    # Context keyword then optional currency prefix then number
    m = re.search(
        r"(?:have|budget|spend)\s+(?:(?:lkr|rs\.?|rupees?)\s*)?([0-9][0-9,]*(?:\.[0-9]+)?)(k)?(?=[\s,.]|$)",
        text,
    )
    if m:
        val = float(m.group(1).replace(",", ""))
        if m.group(2) == "k":
            val *= 1000
        return val

    # Bare 3-6 digit number as last resort (only in budget-like contexts)
    if any(w in text for w in ("budget", "have", "spend", "rupee", "lkr", "rs")):
        m = re.search(r"\b([1-9][0-9]{2,5})\b", text)
        if m:
            return float(m.group(1))

    return None


def _extract_party_size(text: str) -> int:
    patterns = [
        r"for\s+([0-9]+|two|three|four|five|six)\s+(?:people|persons?|pax|of\s+us)",
        r"([0-9]+|two|three|four|five|six)\s+(?:people|persons?|pax)",
        r"party\s+of\s+([0-9]+|two|three|four|five|six)",
        # "for two" / "for 2" at end of phrase or before punctuation
        r"for\s+([0-9]+|two|three|four|five|six)(?=\s*[,.]|\s*$)",
    ]
    word_map = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6}
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            raw = m.group(1)
            return word_map[raw] if raw in word_map else int(raw)
    return 1


def _extract_cuisines(text: str) -> list[str]:
    found: set[str] = set()
    for keyword, cuisine in CUISINE_MAP.items():
        if keyword in text:
            found.add(cuisine)
    return sorted(found)


def _extract_dietary_exclude(text: str) -> list[str]:
    found: set[str] = set()
    for keyword, tag in DIETARY_EXCLUDE_KEYWORDS.items():
        if keyword in text:
            found.add(tag)
    return sorted(found)


def _extract_dietary_require(text: str) -> list[str]:
    found: set[str] = set()
    for keyword, tag in DIETARY_REQUIRE_KEYWORDS.items():
        if keyword in text:
            found.add(tag)
    return sorted(found)


def _extract_spice(text: str) -> Optional[str]:
    for keyword, level in SPICE_MAP.items():
        if keyword in text:
            return level
    return None


def _extract_categories(text: str) -> list[str]:
    found: set[str] = set()
    for keyword, category in CATEGORY_MAP.items():
        if keyword in text:
            found.add(category)
    return sorted(found)


def _extract_city(text: str, default: str) -> str:
    cities = {"colombo": "Colombo", "kandy": "Kandy", "galle": "Galle", "negombo": "Negombo"}
    for key, name in cities.items():
        if key in text:
            return name
    return default
