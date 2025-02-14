from enum import Enum

from pydantic import BaseModel, Field, HttpUrl, field_validator
import re
from typing import List, Optional, Dict


class RecipeMetricsEventType(Enum):
    success = "recipe_scrape.success"
    failure = "recipe_scrape.failure"
    validation_errors = "recipe_scrape.validation_errors"


class RecipeIngredient(BaseModel):
    name: str = Field(..., description="Name of the ingredient")
    quantity: Optional[float] = Field(None, description="Quantity of ingredient")
    unit: Optional[str] = Field(None, description="Unit of measurement")
    notes: Optional[str] = Field(None, description="Additional notes")
    group: Optional[str] = Field(None, description="Ingredient group")


def validate_ingredients(ingredients: List[RecipeIngredient]) -> List[RecipeIngredient]:
    """
    Validate ingredients list, allowing one ingredient to have no quantity/unit.
    """
    skipped_one = False
    valid_ingredients = []

    for ing in ingredients:
        if ing.quantity is None and ing.unit is None:
            if not skipped_one:
                # Allow one ingredient without quantity/unit
                skipped_one = True
                valid_ingredients.append(ing)
            continue
        valid_ingredients.append(ing)

    return valid_ingredients


class Recipe(BaseModel):
    title: str = Field(..., description="Recipe title")
    instructions: str = Field(..., description="Cooking instructions as numbered steps")
    prep_time: int = Field(..., description="Preparation time in minutes", ge=0)
    cook_time: int = Field(..., description="Cooking time in minutes", ge=0)
    total_time: int = Field(..., description="Total time in minutes", ge=0)
    servings: int = Field(..., description="Number of servings", gt=0)
    source_url: HttpUrl = Field(..., description="Original recipe URL")
    notes: Optional[str] = Field(None, description="Additional notes")
    ingredients: List[RecipeIngredient]

    @field_validator("ingredients")
    @classmethod
    def validate_ingredient_list(cls, v):
        seen = set()
        unique_ingredients = []
        for ing in v:
            # Better key that includes weight ranges
            name = ing.name.lower().strip()
            name = re.sub(r"\([^)]*\)", "", name)  # Remove parentheses content
            name = re.sub(
                r"\d+-\d+\s*(?:pounds?|lbs?)", "", name
            )  # Remove weight ranges
            name = re.sub(
                r"^[^a-z]+", "", name
            )  # Remove leading non-letters (fixes "uck")
            key = name.strip()

            if key not in seen:
                seen.add(key)
                # Parse number ranges like "4-5" into average
                if ing.quantity is None and ing.name:
                    match = re.search(r"(\d+)-(\d+)", ing.name)
                    if match:
                        start, end = map(int, match.groups())
                        ing.quantity = (start + end) / 2
                unique_ingredients.append(ing)

        return validate_ingredients(unique_ingredients)
