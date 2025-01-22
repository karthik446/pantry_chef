from smolagents import CodeAgent, DuckDuckGoSearchTool, HfApiModel, tool
import re
import requests
import json
from typing import Optional
import sys
from bs4 import BeautifulSoup
from w3lib.html import get_base_url
from fractions import Fraction
from pint import UnitRegistry
from difflib import SequenceMatcher

# Initialize the model and tools
model = HfApiModel()
search_tool = DuckDuckGoSearchTool()

# API Configuration
BASE_URL = "http://localhost:8000/api"
AUTH_TOKENS = {"access_token": None, "refresh_token": None}

# Add at the top of the file
visited_urls = set()

# Initialize unit registry for conversions
ureg = UnitRegistry()


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


def initialize_auth() -> bool:
    """Initialize authentication by getting initial access and refresh tokens.

    Returns:
        bool: True if authentication was successful, False otherwise.
    """
    auth_data = {"email": "skarthikc.dev@gmail.com", "password": "cUcsuv-majtyc-9gejfa"}

    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=auth_data)
        response.raise_for_status()
        tokens = response.json()
        AUTH_TOKENS.update(tokens)
        print("Authentication successful!")
        return True
    except Exception as e:
        print(f"Authentication failed: {str(e)}")
        return False


@tool
def get_auth_tokens() -> dict:
    """Gets authentication tokens from the login API.

    Returns:
        dict: A dictionary containing access and refresh tokens or error information.
    """
    auth_data = {"email": "skarthikc.dev@gmail.com", "password": "cUcsuv-majtyc-9gejfa"}

    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=auth_data)
        response.raise_for_status()
        tokens = response.json()
        AUTH_TOKENS.update(tokens)
        return tokens
    except Exception as e:
        print(f"Authentication error: {str(e)}")
        return {"error": str(e)}


@tool
def refresh_auth_token() -> dict:
    """Refreshes the access token using the refresh token.

    Returns:
        dict: A dictionary containing the new access and refresh tokens or error information.
    """
    if not AUTH_TOKENS["refresh_token"]:
        return get_auth_tokens()

    try:
        response = requests.post(
            f"{BASE_URL}/auth/refresh",
            headers={"Authorization": f"Bearer {AUTH_TOKENS['refresh_token']}"},
        )
        response.raise_for_status()
        tokens = response.json()
        AUTH_TOKENS.update(tokens)
        return tokens
    except Exception:
        return get_auth_tokens()


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
    text = re.sub(r"^[A-Za-z]\s+", "", text)  # Remove single letter prefix
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


def similar(a: str, b: str) -> float:
    """Calculate similarity ratio between two strings."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


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
def get_submitted_urls(search_query: str) -> dict:
    """Get list of URLs already submitted for a search query.

    Args:
        search_query: The search query to check (e.g., "chicken stir fry")

    Returns:
        dict: On success: {"urls": List[str]} containing URLs already submitted
              On failure: {"error": str} with error message
    """
    headers = {"Authorization": f"Bearer {AUTH_TOKENS['access_token']}"}
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
        return {"urls": data.get("urls", [])}
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

    headers = {"Authorization": f"Bearer {AUTH_TOKENS['access_token']}"}
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


# Create the agent with all tools
agent = CodeAgent(
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
   a. search_tool.forward()
   b. scrape_recipe()
   c. submit_recipe()
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

# Example usage
if __name__ == "__main__":
    # Initialize authentication before running
    if not initialize_auth():
        print("Failed to authenticate. Exiting...")
        sys.exit(1)

    result = agent.run('Search and submit recipe for "korean chicken spicy"')
    print(result)
