import google.generativeai as genai
import os
from dotenv import load_dotenv
import requests
from recipe_scrapers import scrape_html
import json
import time

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-2.0-flash", generation_config={"temperature": 0})


def scrape_recipe_from_url(url: str):
    """
    Scrape and parse a recipe from a URL using recipe-scrapers and Gemini.
    """
    try:
        print(f"Fetching URL: {url}")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        html = response.text

        scraper = scrape_html(html=html, org_url=url, wild_mode=True)
        recipe_json = scraper.to_json()
        print(f"Raw Recipe JSON: {recipe_json}")

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

        response = model.generate_content(prompt)
        # Extract just the JSON content from markdown response
        json_str = response.text.replace("```json\n", "").replace("\n```", "")
        parsed_data = json.loads(json_str)
        return parsed_data

    except Exception as e:
        print(f"Error scraping recipe: {str(e)}")
        return None


if __name__ == "__main__":
    import warnings

    warnings.filterwarnings("ignore")  # Suppress gRPC warnings
    start_time = time.time()

    test_url = "https://www.indianhealthyrecipes.com/carrot-fry-carrot-curry-recipe/"
    result = scrape_recipe_from_url(test_url)
    print("\nFinal Parsed Result:")
    print(result)
    print(f"Time taken: {time.time() - start_time} seconds")
