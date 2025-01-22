from fractions import Fraction
from typing import Optional
from bs4 import BeautifulSoup
import re
from difflib import SequenceMatcher


def fraction_to_float(fraction_str: str) -> Optional[float]:
    """Convert fraction string to float.

    Args:
        fraction_str: String containing a fraction (e.g., "1/2", "2 1/2")

    Returns:
        Float value of the fraction or None if invalid
    """
    try:
        if "/" in fraction_str:
            if " " in fraction_str:
                whole, frac = fraction_str.split(" ", 1)
                return float(whole) + float(Fraction(frac))
            return float(Fraction(fraction_str))
        return float(fraction_str)
    except (ValueError, ZeroDivisionError):
        return None


def find_print_link(soup) -> Optional[BeautifulSoup]:
    """Helper function to find print recipe link in a BeautifulSoup object.

    Args:
        soup: BeautifulSoup object of the recipe page.

    Returns:
        BeautifulSoup object of the print link if found, None otherwise.
    """
    # First try by string content
    print_link = soup.find(
        "a",
        string=lambda x: x
        and any(
            phrase in x.lower()
            for phrase in [
                "print recipe",
                "print this recipe",
                "print",
                "printer-friendly",
                "printable version",
            ]
        ),
    )

    # If not found, try by href
    if not print_link:
        print_link = soup.find(
            "a",
            href=lambda x: x and ("print" in x.lower() or "wprm_print" in x.lower()),
        )

    return print_link


def clean_text(text: str) -> str:
    """Clean text by removing unicode and normalizing whitespace.

    Args:
        text: Raw text to clean

    Returns:
        Cleaned text with normalized characters and spacing
    """
    # Replace unicode fractions
    fraction_map = {
        "¼": "1/4",
        "½": "1/2",
        "¾": "3/4",
        "⅓": "1/3",
        "⅔": "2/3",
        "⅛": "1/8",
        "⅜": "3/8",
        "⅝": "5/8",
        "⅞": "7/8",
    }
    for unicode_frac, ascii_frac in fraction_map.items():
        text = text.replace(unicode_frac, ascii_frac)

    # Replace other unicode characters
    text = text.replace("\u2019", "'")  # Smart quotes
    text = text.replace("\u2018", "'")
    text = text.replace("\u201c", '"')
    text = text.replace("\u201d", '"')
    text = text.replace("\u00b0", " degrees ")  # Degree symbol
    text = text.replace("\u00a0", " ")  # Non-breaking space

    # Normalize whitespace
    text = " ".join(text.split())

    return text.strip()


def parse_ingredient(text: str) -> dict:
    """Parse ingredient text into structured data."""
    text = clean_text(text)

    # Extract quantity in parentheses if present
    parentheses_match = re.search(r"\((.*?)\)", text)
    notes = parentheses_match.group(1) if parentheses_match else None
    if notes:
        text = text.replace(f"({notes})", "").strip()

    # Fix common scraping artifacts
    if text.startswith(("s ", "n ", "d ", "t ")):  # Common scraping artifacts
        text = text[2:]
    text = re.sub(r"^(\d+)\s*oves\b", r"\1 cloves", text)  # Fix "oves" -> "cloves"
    text = re.sub(r"^reen\b", "green", text)  # Fix "reen" -> "green"

    # Common unit patterns
    units = {
        # Volume
        "cup": "cup",
        "cups": "cup",
        "c.": "cup",
        "tablespoon": "tablespoon",
        "tbsp": "tablespoon",
        "tbs": "tablespoon",
        "teaspoon": "teaspoon",
        "tsp": "teaspoon",
        # Weight
        "pound": "pound",
        "lb": "pound",
        "lbs": "pound",
        "ounce": "ounce",
        "oz": "ounce",
        "gram": "gram",
        "g": "gram",
        "kilogram": "kilogram",
        "kg": "kilogram",
        # Count
        "whole": "whole",
        "large": "whole",
        "medium": "whole",
        "small": "whole",
        "piece": "piece",
        "pieces": "piece",
        "slice": "slice",
        "slices": "slice",
        "clove": "clove",
        "cloves": "clove",
    }

    # Build regex pattern for units
    unit_pattern = "|".join(units.keys())

    # Try to match quantity, unit, and name
    match = re.match(
        rf"^([\d\s./+-]+)?\s*({unit_pattern})?\s*(.+)$", text, re.IGNORECASE
    )

    if match:
        qty_str, unit, name = match.groups()

        # Parse quantity
        quantity = None
        if qty_str:
            qty_str = qty_str.strip()
            try:
                if "/" in qty_str:
                    if " " in qty_str:
                        whole, frac = qty_str.split(" ", 1)
                        quantity = float(whole) + float(Fraction(frac))
                    else:
                        quantity = float(Fraction(qty_str))
                else:
                    quantity = float(qty_str)
            except (ValueError, ZeroDivisionError):
                pass

        # Normalize unit
        if unit:
            unit = unit.lower().strip()
            unit = units.get(unit)

        # Clean up name
        name = name.strip()
        if notes:
            name = f"{name} ({notes})"

        # Determine category
        category = "Other"
        categories = {
            "Produce": [
                "onion",
                "garlic",
                "carrot",
                "tomato",
                "lettuce",
                "pepper",
                "vegetable",
                "fruit",
            ],
            "Meat & Seafood": [
                "chicken",
                "beef",
                "pork",
                "fish",
                "shrimp",
                "meat",
                "turkey",
            ],
            "Dairy": ["cheese", "milk", "cream", "butter", "yogurt", "egg"],
            "Dry Goods": ["flour", "sugar", "salt", "spice", "herb", "rice", "pasta"],
            "Baking": ["baking powder", "baking soda", "yeast", "vanilla"],
            "Canned Goods": ["can", "jar", "sauce", "paste", "broth", "stock"],
            "Oils & Vinegars": ["oil", "vinegar", "cooking spray"],
        }

        for cat, keywords in categories.items():
            if any(keyword in name.lower() for keyword in keywords):
                category = cat
                break

        return {"name": name, "quantity": quantity, "unit": unit, "category": category}

    return {"name": text, "quantity": None, "unit": None, "category": "Other"}


def parse_time(text: str) -> Optional[int]:
    """Convert time text to minutes.

    Args:
        text: Time text (e.g., "1 hour 20 minutes", "45 mins")

    Returns:
        Number of minutes or None if invalid
    """
    if not text:
        return None

    text = text.lower()
    minutes = 0

    # Extract hours
    hour_patterns = [r"(\d+)\s*(?:hour|hr)s?", r"(\d+)\s*h\b"]
    for pattern in hour_patterns:
        match = re.search(pattern, text)
        if match:
            minutes += int(match.group(1)) * 60

    # Extract minutes
    minute_patterns = [r"(\d+)\s*(?:minute|min)s?", r"(\d+)\s*m\b"]
    for pattern in minute_patterns:
        match = re.search(pattern, text)
        if match:
            minutes += int(match.group(1))

    return minutes if minutes > 0 else None


def similar(a: str, b: str) -> float:
    """Calculate similarity ratio between two strings."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def clean_instructions(text: str) -> str:
    """Clean up recipe instructions."""
    text = clean_text(text)

    # Remove duplicate headers
    text = re.sub(r"(?i)^instructions\s*:?\s*", "", text)
    text = re.sub(r"(?i)directions\s*:?\s*", "", text)

    # Split into steps and clean each one
    steps = []
    seen = set()

    # First split on newlines
    raw_steps = text.split("\n")

    # Then split on numbered steps if present
    if any(re.match(r"^\d+\.", step.strip()) for step in raw_steps):
        raw_steps = [
            step
            for line in raw_steps
            for step in re.split(r"(?m)^\d+\.", line)
            if step.strip()
        ]

    for step in raw_steps:
        step = step.strip()
        # Skip unwanted content
        if (
            step
            and step not in seen
            and not any(
                skip in step.lower()
                for skip in [
                    "dotdash meredith food studios",
                    "credit:",
                    "photo by",
                    "advertisement",
                    "step by step",
                    "watch how to make",
                    "nutrition facts",
                    "recipe video above",
                    "print recipe",
                    "save recipe",
                    "preparation",
                    "instructions:",
                    "directions:",
                ]
            )
        ):
            # Clean up the step
            step = re.sub(r"\s+", " ", step)  # Normalize whitespace
            step = re.sub(r"([.!?])\s*([A-Z])", r"\1\n\2", step)  # Add line breaks
            step = step.replace(" degrees F", "°F")  # Clean up temperatures
            step = step.replace(" degrees C", "°C")

            # Only add if not too similar to existing step
            if not any(similar(step, existing) > 0.8 for existing in steps):
                steps.append(step)
                seen.add(step)

    return "\n".join(steps)
