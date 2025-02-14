from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any
import time
import logging
from dotenv import load_dotenv

from recipe_scrapers import scrape_html
from pydantic import ValidationError
import requests
import google.generativeai as genai
import os
import json
import asyncio
import aiohttp
import re

from models import Recipe, RecipeMetricsEventType, RecipeIngredient
from event_models import MetricsEvent

load_dotenv()


class RecipeScraperWorkflowStep:
    """
    Handles recipe scraping with metrics collection and multiple scraping strategies.
    """

    def __init__(
        self,
        model: genai.GenerativeModel,
        logger: Optional[logging.Logger] = None,
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.model = model

    async def scrape_recipes(
        self, urls: List[str]
    ) -> List[Tuple[Optional[Recipe], List[MetricsEvent]]]:
        """
        Scrape multiple recipes in parallel.
        """
        async with aiohttp.ClientSession() as session:
            tasks = [self.scrape_recipe(url, session) for url in urls]
            return await asyncio.gather(*tasks)

    async def scrape_recipe(
        self, url: str, session: Optional[aiohttp.ClientSession] = None
    ) -> Tuple[Optional[Recipe], List[MetricsEvent]]:
        """
        Main entry point for recipe scraping.
        """
        metrics: List[MetricsEvent] = []
        start_time = time.time()

        # Clean the URL first
        cleaned_url = self._clean_url(url)
        if not cleaned_url:
            self.logger.error(f"Invalid URL format: {url}")
            metrics.append(
                self._create_metrics_event(
                    RecipeMetricsEventType.failure,
                    duration=time.time() - start_time,
                    metadata={"url": url, "error": "Invalid URL format"},
                )
            )
            return None, metrics

        try:
            # Use cleaned URL for scraping
            parsed_data = await self._try_gemini_scrape(cleaned_url, session)
            if not parsed_data:
                metrics.append(
                    self._create_metrics_event(
                        RecipeMetricsEventType.failure,
                        duration=time.time() - start_time,
                        metadata={"url": cleaned_url, "method": "gemini"},
                    )
                )
                return None, metrics

            # Create Recipe object from parsed data
            recipe_data = parsed_data["recipe"]
            recipe_data["ingredients"] = parsed_data["ingredients"]

            # Filter ingredients and update notes
            recipe_data = self._filter_ingredients_and_update_notes(recipe_data)

            # Validate recipe data
            is_valid, validation_errors = self._validate_recipe(recipe_data)
            if not is_valid:
                metrics.append(
                    self._create_metrics_event(
                        RecipeMetricsEventType.validation_errors,
                        metadata={
                            "url": cleaned_url,
                            "validation_errors": validation_errors,
                        },
                    )
                )
                return None, metrics

            recipe = Recipe(**recipe_data)
            metrics.append(
                self._create_metrics_event(
                    RecipeMetricsEventType.success,
                    duration=time.time() - start_time,
                    metadata={"method": "gemini", "url": cleaned_url},
                )
            )
            return recipe, metrics

        except Exception as e:
            self.logger.error(f"Error scraping recipe from {cleaned_url}: {str(e)}")
            metrics.append(
                self._create_metrics_event(
                    RecipeMetricsEventType.failure,
                    duration=time.time() - start_time,
                    metadata={
                        "url": cleaned_url,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )
            )
            return None, metrics

    async def _try_gemini_scrape(
        self, url: str, session: Optional[aiohttp.ClientSession] = None
    ) -> Optional[Dict]:
        """
        Attempts to scrape recipe using Gemini-based approach.
        """
        try:
            self.logger.info(f"Starting scrape for URL: {url}")
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }

            try:
                if session:
                    async with session.get(url, headers=headers) as response:
                        html = await response.text()
                else:
                    response = requests.get(url, headers=headers)
                    html = response.text
                self.logger.debug(f"Successfully fetched HTML from {url}")
            except Exception as e:
                self.logger.error(f"Failed to fetch URL {url}: {str(e)}")
                return None

            try:
                scraper = scrape_html(html=html, org_url=url, wild_mode=True)
                recipe_json = scraper.to_json()
                self.logger.debug(f"Successfully scraped recipe JSON from {url}")
            except Exception as e:
                self.logger.error(f"Failed to scrape HTML from {url}: {str(e)}")
                return None

            try:
                prompt = f"""
                Parse this recipe JSON into our required format. Return ONLY a JSON with two keys: 'recipe' and 'ingredients'.

                Recipe JSON:
                {recipe_json}

                For ingredients, use this EXACT format and separate quantity/unit from name:
                [
                    {{"name": "boneless chicken thigh fillets", "quantity": 450.0, "unit": "g", "notes": "1 pound", "group": None}},
                    {{"name": "sweet potato", "quantity": 100.0, "unit": "g", "notes": "3.5 ounces, peeled and thinly sliced", "group": None}}
                ]

                Rules for ingredients:
                - Extract quantity and unit from the ingredient name
                - Put the pure ingredient name without measurements in "name"
                - Convert fractions to decimals
                - Include any additional info in notes
                - Keep the original group if present

                For recipe, include these fields:
                {{
                    "title": str,
                    "instructions": str,
                    "prep_time": int (in minutes),
                    "cook_time": int (in minutes),
                    "total_time": int (in minutes),
                    "servings": int,
                    "source_url": str,
                    "notes": str or None
                }}

                Use None (not null) for any missing fields.
                """

                response = self.model.generate_content(prompt)
                json_str = response.text.replace("```json\n", "").replace("\n```", "")
                parsed_data = json.loads(json_str)
                self.logger.debug(f"Successfully parsed recipe data from {url}")
                return parsed_data
            except Exception as e:
                self.logger.error(
                    f"Failed to parse recipe with Gemini for {url}: {str(e)}"
                )
                self.logger.error(
                    f"Gemini response: {response.text if 'response' in locals() else 'No response'}"
                )
                return None

        except Exception as e:
            self.logger.error(f"Gemini scraping failed for {url}: {str(e)}")
            return None

    def _create_metrics_event(
        self,
        event_type: RecipeMetricsEventType,
        duration: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MetricsEvent:
        """
        Helper method to create MetricsEvent with consistent structure.
        """
        return MetricsEvent(
            event_type=event_type.value,
            duration=duration,
            metadata=metadata or {},
            timestamp=datetime.utcnow(),
        )

    def _validate_recipe(self, recipe_data: dict) -> Tuple[bool, List[str]]:
        """
        Validates recipe data against Recipe model.

        Returns:
            Tuple of (is_valid, list_of_validation_errors)
        """
        try:
            Recipe(**recipe_data)
            return True, []
        except ValidationError as e:
            errors = [f"{error['loc'][0]}: {error['msg']}" for error in e.errors()]
            return False, errors

    def _filter_ingredients_and_update_notes(self, recipe_data: Dict) -> Dict:
        """
        Filter out ingredients without quantity/unit and add them to notes.
        """
        valid_ingredients = []
        notes_ingredients = []

        for ing in recipe_data["ingredients"]:
            if ing["quantity"] is None and ing["unit"] is None:
                notes_ingredients.append(ing["name"])
            else:
                valid_ingredients.append(ing)

        # Update recipe notes
        notes = recipe_data.get("notes") or ""
        if notes_ingredients:
            additional_notes = "Additional ingredients (to taste): " + ", ".join(
                notes_ingredients
            )
            recipe_data["notes"] = (
                f"{notes}\n{additional_notes}" if notes else additional_notes
            )

        recipe_data["ingredients"] = valid_ingredients
        return recipe_data

    def _clean_url(self, url: str) -> Optional[str]:
        """Clean markdown formatted URLs and ensure we have valid http/https URLs."""
        self.logger.debug(f"Cleaning URL: {url}")
        import re

        # Try to extract URL from markdown format [title](url)
        markdown_match = re.search(r"\[(.*?)\]\((https?://[^)]+)\)", url)
        if markdown_match:
            cleaned = markdown_match.group(2)  # Get the URL part
            self.logger.debug(f"Extracted URL from markdown: {cleaned}")
            return cleaned

        # If not markdown, check if it's a plain http/https URL
        if url.startswith(("http://", "https://")):
            self.logger.debug(f"URL is already clean: {url}")
            return url

        self.logger.error(f"Could not extract valid URL from: {url}")
        return None


async def main():
    """
    Test function to run recipe scraper workflow step in isolation.
    """
    try:
        # Test URLs - mix of likely successes and failures
        test_urls = ["https://www.indianhealthyrecipes.com/tandoori-chicken-recipe/"]
        #     "https://www.foodnetwork.com/recipes/ina-garten/perfect-roast-chicken-recipe-1940592",
        #     "https://www.simplyrecipes.com/recipes/homemade_pizza/",
        #     "https://invalid-recipe-url.com/recipe",  # Should fail
        # ]
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model = genai.GenerativeModel(
            "gemini-2.0-flash", generation_config={"temperature": 0}
        )
        # Initialize scraper
        scraper = RecipeScraperWorkflowStep(model)

        # Process each URL
        for url in test_urls:
            print(f"\nTesting URL: {url}")
            recipe, metrics = await scraper.scrape_recipe(url)

            # Print results
            if recipe:
                print("\nRecipe extracted successfully:")
                print(f"Title: {recipe.title}")
                print(f"ingredients: {recipe.ingredients}")
                print(f"Ingredients count: {len(recipe.ingredients)}")
                print(f"Instructions length: {len(recipe.instructions)}")
            else:
                print("\nFailed to extract recipe")

            print("\nMetrics collected:")
            for metric in metrics:
                print(f"- Type: {metric.event_type}")
                print(f"  Duration: {metric.duration}")
                print(f"  Metadata: {metric.metadata}")

    except Exception as e:
        print(f"Error in main: {e}")
        raise


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
