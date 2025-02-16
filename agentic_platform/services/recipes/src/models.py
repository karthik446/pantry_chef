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
    source_url: str = Field(..., description="Original recipe URL")
    notes: Optional[str] = Field(None, description="Additional notes")
    ingredients: List[RecipeIngredient]

    def model_dump(self, **kwargs):
        data = super().model_dump(**kwargs)
        # Convert HttpUrl to string
        data["source_url"] = str(data["source_url"])
        # Rename ingredients to recipe_ingredients to match Go DTO
        data["recipe_ingredients"] = [
            {
                "ingredient_name": ing["name"],
                "quantity": ing["quantity"],
                "unit": ing["unit"],
            }
            for ing in data.pop("ingredients")
        ]
        return data
