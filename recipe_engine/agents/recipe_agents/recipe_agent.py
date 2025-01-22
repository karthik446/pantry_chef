from smolagents import CodeAgent, DuckDuckGoSearchTool, HfApiModel, tool
from typing import Dict, Any
from services.auth import AuthService
from config.settings import settings
from loguru import logger
import requests
import re
import json
import sys
from bs4 import BeautifulSoup
from w3lib.html import get_base_url
from .utils import find_print_link, clean_instructions, parse_ingredient, clean_text

# Global instances
auth_service = None
BASE_URL = "http://localhost:8000/api"

model = HfApiModel()
search_tool = DuckDuckGoSearchTool()

visited_urls = set()


@tool
def scrape_recipe(url: str) -> dict:
    """Scrapes recipe data from a given URL using HTML parsing.

    Args:
        url: The URL of the recipe page to scrape.

    Returns:
        dict: A dictionary containing the recipe data with the following fields:
            - title: str, The recipe title
            - instructions: str, Step by step cooking instructions
            - prep_time: Optional[int], Preparation time in minutes
            - cook_time: Optional[int], Cooking time in minutes
            - servings: Optional[int], Number of servings
            - source_url: str, Original recipe URL
            - ingredients: List[dict], List of ingredients with name, quantity, unit and category

        Or a dictionary with an 'error' key if scraping failed.
    """
    global visited_urls

    if url in visited_urls:
        return {"error": "URL already processed in this session"}
    visited_urls.add(url)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        # Don't retry on 404s - page definitely doesn't exist
        if response.status_code == 404:
            return {"error": f"Page not found: {url}"}
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Try to find print version first
        print_link = find_print_link(soup)
        if print_link:
            print_url = print_link.get("href")
            if print_url:
                if not print_url.startswith("http"):
                    base_url = get_base_url(response.text, response.url)
                    print_url = requests.compat.urljoin(base_url, print_url)
                response = requests.get(print_url, headers=headers)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")

        recipe = {
            "title": None,
            "instructions": "",
            "prep_time": None,
            "cook_time": None,
            "servings": None,
            "source_url": url,
            "ingredients": [],
        }

        # Extract title
        title_selectors = [
            "h1",
            "h1.recipe-title",
            ".recipe-title",
            ".recipe-header h1",
            ".recipe-name",
            '[itemprop="name"]',
            ".wprm-recipe-name",
            ".tasty-recipes-title",
            # Add Home Chef selectors
            ".recipe-title-container h1",
            ".recipe-details h1",
            ".meal-name",
        ]
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                recipe["title"] = title_elem.text.strip()
                break

        # Extract ingredients
        ingredient_selectors = [
            '[itemprop="recipeIngredient"]',
            ".recipe-ingredients li",
            ".ingredients li",
            ".wprm-recipe-ingredient",
            ".tasty-recipes-ingredients li",
            ".ingredient",
            "[data-ingredient]",
            # Add Food & Wine selectors
            ".ingredients-list-item",  # Food & Wine
            ".ingredient-list li",  # Food & Wine alternative
            ".recipe-ingredients__list-item",  # Common format
            ".recipe__ingredients li",  # Another common format
            ".recipe-ingredients__item",
            # Generic ingredient lists
            "ul.ingredients li",
            ".ingredients ul li",
            '[class*="ingredient" i] li',  # Case-insensitive contains "ingredient"
        ]

        ingredients_found = False
        for selector in ingredient_selectors:
            ingredients = soup.select(selector)
            if ingredients:
                recipe["ingredients"] = [
                    parse_ingredient(ing.text.strip())
                    for ing in ingredients
                    if ing.text.strip()
                ]
                ingredients_found = bool(recipe["ingredients"])
                if ingredients_found:
                    break

        # Extract instructions
        instructions_found = False
        for selector in [
            '[itemprop="recipeInstructions"]',
            ".recipe-instructions",
            ".instructions",
            ".wprm-recipe-instructions",
            ".tasty-recipes-instructions",
            ".preparation",
            "[data-instructions]",
        ]:
            instructions = soup.select(selector)
            if instructions:
                steps = []
                for inst in instructions:
                    # Handle both list items and paragraphs
                    if inst.name == "ol":
                        steps.extend([li.text.strip() for li in inst.find_all("li")])
                    else:
                        steps.append(inst.text.strip())

                steps = [
                    clean_instructions(s)
                    for s in steps
                    if s and "Dotdash Meredith Food Studios" not in s
                ]
                if steps:
                    recipe["instructions"] = "\n".join(steps)
                    instructions_found = True
                    break

        # Extract times
        for time_type in ["prep", "cook", "total"]:
            for selector in [
                f'[itemprop="{time_type}Time"]',
                f".{time_type}-time",
                f".wprm-recipe-{time_type}-time",
                f".tasty-recipes-{time_type}-time",
            ]:
                time_elem = soup.select_one(selector)
                if time_elem:
                    # Try to extract minutes from the text
                    text = time_elem.text.lower()
                    if "minute" in text or "min" in text:
                        try:
                            minutes = int("".join(filter(str.isdigit, text)))
                            recipe[f"{time_type}_time"] = minutes
                            break
                        except ValueError:
                            continue

        # Extract servings
        for selector in [
            '[itemprop="recipeYield"]',
            ".recipe-servings",
            ".servings",
            ".wprm-recipe-servings",
            ".tasty-recipes-yield",
        ]:
            servings_elem = soup.select_one(selector)
            if servings_elem:
                try:
                    servings = int("".join(filter(str.isdigit, servings_elem.text)))
                    recipe["servings"] = servings
                    break
                except ValueError:
                    continue

        # Validate recipe
        if not recipe["title"]:
            return {"error": "Could not find recipe title"}
        if not ingredients_found:
            return {"error": "Could not find recipe ingredients"}
        if not instructions_found:
            return {"error": "Could not find recipe instructions"}

        # Clean up instructions
        instructions = clean_instructions(recipe["instructions"])

        # Validate instructions aren't truncated
        if len(instructions) < 50:  # Too short
            return {"error": "Instructions too short"}
        if instructions.endswith(("...", "…")):  # Truncated
            return {"error": "Instructions truncated"}

        # Validate servings is reasonable
        if servings and (servings <= 0 or servings > 24):
            servings = None  # Reset invalid servings

        # Clean up ingredients
        cleaned_ingredients = []
        seen_ingredients = set()
        for ing in recipe["ingredients"]:
            # Skip duplicates
            ingredient_key = f"{ing['name']}_{ing['quantity']}_{ing['unit']}"
            if ingredient_key in seen_ingredients:
                continue
            seen_ingredients.add(ingredient_key)

            # Clean up ingredient name
            ing["name"] = clean_text(ing["name"])
            if ing["name"].startswith(
                ("s ", "n ", "d ", "t ")
            ):  # Common scraping artifacts
                ing["name"] = ing["name"][2:]

            # Validate quantity
            if ing["quantity"] and (ing["quantity"] <= 0 or ing["quantity"] > 100):
                ing["quantity"] = None

            cleaned_ingredients.append(ing)

        recipe = {
            "title": recipe["title"],
            "instructions": instructions,
            "ingredients": cleaned_ingredients,
            "prep_time": recipe["prep_time"],
            "cook_time": recipe["cook_time"],
            "total_time": (recipe["prep_time"] or 0) + (recipe["cook_time"] or 0),
            "servings": servings,
            "source_url": url,
        }

        # Final validation
        if (
            not recipe["title"]
            or not recipe["instructions"]
            or not recipe["ingredients"]
        ):
            return {"error": "Missing required recipe data"}

        # If we couldn't find times in the HTML, estimate from instructions
        if not recipe.get("prep_time") or not recipe.get("cook_time"):
            # Pass the full page text for time estimation
            estimated_times = estimate_recipe_times(response.text)
            recipe["prep_time"] = recipe.get("prep_time") or estimated_times.get(
                "prep_time"
            )
            recipe["cook_time"] = recipe.get("cook_time") or estimated_times.get(
                "cook_time"
            )
            recipe["total_time"] = (recipe["prep_time"] or 0) + (
                recipe["cook_time"] or 0
            )

        return recipe

    except requests.Timeout:
        print(f"Debug - Timeout accessing URL: {url}")
        return {"error": f"Timeout accessing URL: {url}"}
    except requests.RequestException as e:
        print(f"Debug - Request error for URL {url}: {str(e)}")
        # Don't include full URL in error message to avoid retrying
        if "404" in str(e):
            return {"error": "Page not found"}
        return {"error": str(e)}
    except Exception as e:
        print(f"Debug - Unexpected error scraping {url}: {str(e)}")
        return {"error": f"Unexpected error: {str(e)}"}


@tool
def estimate_recipe_times(recipe_text: str) -> dict:
    """Extract prep, cook and total times from recipe text using AI.

    Args:
        recipe_text: The full recipe text/HTML to analyze for timing information

    Returns:
        dict: Times in minutes with structure:
            {
                "prep_time": int or None,  # Preparation time in minutes
                "cook_time": int or None,  # Cooking time in minutes
                "total_time": int or None  # Total time in minutes
            }
    """
    formatted_prompt = f"""Look at this recipe text and find the preparation time, cooking time, and total time.
Look for explicit time mentions like "Prep Time: 5 mins" or "Cook: 40 mins".
Return ONLY a JSON object with the times in minutes.

Recipe Text:
{recipe_text}

Return your response in this EXACT format (just the JSON, no other text):
{{"prep_time": 15, "cook_time": 30, "total_time": 45}}

Use null instead of numbers if you can't find a time.
Example with null: {{"prep_time": null, "cook_time": 20, "total_time": 20}}"""

    try:
        messages = [{"role": "user", "content": formatted_prompt}]
        raw_response = model(messages)

        if hasattr(raw_response, "content"):
            response_text = raw_response.content
        else:
            response_text = str(raw_response)

        response_text = response_text.strip()

        # Find the first JSON-like structure in the response
        json_match = re.search(r"\{[^}]+\}", response_text)
        if not json_match:
            return {"prep_time": None, "cook_time": None, "total_time": None}

        response_text = json_match.group(0)

        try:
            times = json.loads(response_text)

            # Convert values to integers or None, with better error handling
            times = {
                "prep_time": (
                    int(times["prep_time"])
                    if times.get("prep_time")
                    and times["prep_time"] not in (None, "null", "NULL", "Null")
                    else None
                ),
                "cook_time": (
                    int(times["cook_time"])
                    if times.get("cook_time")
                    and times["cook_time"] not in (None, "null", "NULL", "Null")
                    else None
                ),
                "total_time": (
                    int(times["total_time"])
                    if times.get("total_time")
                    and times["total_time"] not in (None, "null", "NULL", "Null")
                    else None
                ),
            }

            print(
                f"Found recipe times: prep={times['prep_time']}m, cook={times['cook_time']}m, total={times['total_time']}m"
            )
            return times

        except json.JSONDecodeError as e:
            print(f"Failed to parse time response: {response_text}")
            return {"prep_time": None, "cook_time": None, "total_time": None}

    except Exception as e:
        print(f"Error extracting times: {str(e)}")
        return {"prep_time": None, "cook_time": None, "total_time": None}


@tool
def get_submitted_urls(search_query: str) -> dict:
    """Get list of URLs already submitted for a search query.

    Args:
        search_query: The search query to check (e.g., "chicken stir fry")

    Returns:
        dict: On success: {"urls": List[str]} containing URLs already submitted
              On failure: {"error": str} with error message
    """
    headers = {"Authorization": f"Bearer {auth_service.get_access_token()}"}
    encoded_query = requests.utils.quote(search_query)

    try:
        response = requests.get(
            f"{BASE_URL}/recipes/admin/urls?search_query={encoded_query}",
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

        if not data:
            return {"urls": []}
        # Extract just the URLs from the response
        return {"urls": data or []}
    except Exception as e:
        print(f"Error getting submitted URLs: {str(e)}")
        return {"error": str(e)}


@tool
def search_and_submit_recipe(query: str) -> dict:
    """Search for a recipe and submit it to the API.

    Args:
        query: The search query to find a recipe (e.g., "korean chicken spicy")

    Returns:
        dict: The API response or error information
    """
    # Get already submitted URLs for this query
    submitted_urls_result = get_submitted_urls(query)

    if "error" in submitted_urls_result:
        print(
            f"Warning - Could not get submitted URLs: {submitted_urls_result['error']}"
        )
        submitted_urls = []
    else:
        submitted_urls = submitted_urls_result["urls"]

    # Extract domains from submitted URLs to exclude them from search
    exclude_domains = []
    for url in submitted_urls:
        try:
            domain = re.search(r"https?://(?:www\.)?([^/]+)", url).group(1)
            exclude_domains.append(f"-site:{domain}")
        except:
            continue

    # Add exclusions to search query
    search_query = f"{query} recipe -gallery -collection {' '.join(exclude_domains)}"

    # Search for the recipe
    search_results = search_tool.forward(search_query)
    if not search_results:
        return {"error": "No results found"}

    # Extract URLs from search results
    urls = re.findall(r"\[(.*?)\]\((https?://[^\s)]+)\)", search_results)
    if not urls:
        return {"error": "No recipe URLs found in search results"}

    # Skip these domains/paths that we know aren't recipe pages
    skip_patterns = [
        "/account/",
        "/login",
        "/signup",
        "/register",
        "/gallery/",
        "/collection/",
        "/photos/",
        "/category/",
        "pinterest.com",
        "facebook.com",
        "instagram.com",
        "youtube.com",
    ]

    errors = []
    for title, url in urls:
        # Skip non-recipe URLs
        if any(pattern in url.lower() for pattern in skip_patterns):
            continue

        # Skip already submitted URLs
        if url in submitted_urls:
            print(f"Debug - Skipping previously submitted URL: {url}")
            continue

        if url not in visited_urls:
            print(f"Debug - Trying recipe URL: {url}")
            recipe = scrape_recipe(url)

            if "error" in recipe:
                error_msg = recipe["error"]
                print(f"Debug - Skipping URL {url}: {error_msg}")
                # Don't add 404 errors to retry list
                if "not found" not in error_msg.lower():
                    errors.append({"url": url, "error": error_msg})
                continue

            # Validate recipe
            if not recipe.get("title"):
                msg = "No recipe title found"
                print(f"Debug - Skipping URL {url}: {msg}")
                errors.append({"url": url, "error": msg})
                continue

            if not recipe.get("instructions"):
                msg = "No instructions found"
                print(f"Debug - Skipping URL {url}: {msg}")
                errors.append({"url": url, "error": msg})
                continue

            if not recipe.get("ingredients"):
                msg = "No ingredients found"
                print(f"Debug - Skipping URL {url}: {msg}")
                errors.append({"url": url, "error": msg})
                continue

            # Validate recipe matches search query
            query_terms = set(query.lower().split())
            title_terms = set(recipe["title"].lower().split())
            matches = len(query_terms.intersection(title_terms))

            if matches >= len(query_terms) / 2:
                recipe["created_from_search_query"] = query
                result = submit_recipe(recipe)
                if "error" not in result:
                    print("Recipe submitted successfully!")
                    # Exit after successful submission
                    sys.exit(0)  # Clean exit
                return result
            else:
                msg = "Recipe title doesn't match search query"
                print(f"Debug - Skipping URL {url}: {msg}")
                errors.append({"url": url, "error": msg})

    # If we get here, no recipes worked
    return {
        "error": "Could not find a valid recipe in any of the search results",
        "details": errors,
    }


@tool
def submit_recipe(recipe_data: dict) -> dict:
    """Submits a recipe to the API with authentication.

    Args:
        recipe_data: Dictionary containing recipe information including:
            - title: str, Recipe title
            - instructions: str, Cooking instructions
            - ingredients: List[dict], List of ingredients
            - prep_time: Optional[int], Preparation time in minutes
            - cook_time: Optional[int], Cooking time in minutes
            - servings: Optional[int], Number of servings
            - source_url: str, Original recipe URL

    Returns:
        dict: The API response after successful submission,
              or error information if submission failed.
    """
    # Don't submit if recipe_data contains an error
    if "error" in recipe_data:
        print(f"Debug - Skipping submission due to error: {recipe_data['error']}")
        return recipe_data

    headers = {"Authorization": f"Bearer {auth_service.get_access_token()}"}
    print("Debug - Submitting Recipe:", json.dumps(recipe_data, indent=2))

    try:
        response = requests.post(
            f"{BASE_URL}/recipes/admin", json=recipe_data, headers=headers
        )

        if response.status_code == 403:
            print("Authentication expired. Please restart the script.")
            sys.exit(1)

        response.raise_for_status()
        return response.json()
    except Exception as e:
        if "403" in str(e):
            print("Authentication expired. Please restart the script.")
            sys.exit(1)
        print(f"Recipe submission error: {str(e)}")
        return {"error": str(e)}


class RecipeAgent:
    """Agent responsible for searching and scraping recipes. IT Works"""

    def __init__(self):
        """Initialize the recipe agent with its tools and model."""
        global auth_service

        auth_service = AuthService(settings.API_BASE_URL)

        # Initialize the underlying CodeAgent with tools
        self.agent = CodeAgent(
            tools=[search_tool, scrape_recipe, submit_recipe, search_and_submit_recipe],
            model=model,
            max_steps=5,
            additional_authorized_imports=[
                "re",
                "markdownify",
                "requests",
                "json",
                "bs4",
                "extruct",
                "w3lib",
            ],
            system_prompt="""You are a helpful agent that can search for, scrape, and store recipes.

IMPORTANT - FOLLOW THESE RULES:
1. ONLY use the provided tools - DO NOT write your own implementations
2. Use search_and_submit_recipe() as your primary tool
3. If that fails, you may try the individual tools in this order:
   a. scrape_recipe()
   b. submit_recipe()
4. DO NOT create mock implementations or example code
5. DO NOT submit recipes that contain errors

Example of correct usage:
```python
# This is the preferred way
result = search_and_submit_recipe("chocolate souffle")
if "error" in result:
    print(f"Error: {result['error']}")
```

Available tools:
- search_and_submit_recipe(query: str) -> dict
- search_tool.forward(query: str) -> str
- scrape_recipe(url: str) -> dict
- submit_recipe(recipe_data: dict) -> dict

{{authorized_imports}}
{{managed_agents_descriptions}}""",
        )

        # Initialize auth
        if not auth_service.initialize_auth():
            raise Exception("Failed to initialize authentication")

    def run(self, query: str) -> Dict[str, Any]:
        """Run the recipe agent with a search query.

        Args:
            query: The search query for finding recipes

        Returns:
            dict: Results from the agent's execution
        """
        return self.agent.run(query)
