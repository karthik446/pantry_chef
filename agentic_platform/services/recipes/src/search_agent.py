import logging
import time
from typing import List, Optional, Tuple
from duckduckgo_search import DDGS
from datetime import datetime
from event_models import MetricsEvent


def search_recipes(
    search_query: str,
    excluded_domains: Optional[List[str]] = None,
    num_urls: int = 10,
    max_retries: int = 3,
    retry_delay: float = 1.0,
) -> Tuple[List[str], MetricsEvent]:
    """
    Searches for recipes using DuckDuckGo Search API, with domain exclusion and retry logic.
    Returns both the recipe URLs and a metrics event for tracking duration.

    Args:
        search_query: The search query to use for recipe search.
        excluded_domains: A list of domains to exclude from the search results (optional).
        num_urls: The maximum number of recipe URLs to return (default: 10).
        max_retries: Maximum number of retry attempts (default: 3).
        retry_delay: Delay between retries in seconds (default: 1.0).

    Returns:
        A tuple containing a list of recipe URLs and a metrics event for tracking duration.
    """
    start_time = time.time()

    logging.info(
        f"Searching for recipes with query: {search_query}, "
        f"excluding domains: {excluded_domains}, num_urls: {num_urls}"
    )

    # Build the search query with domain exclusions
    if excluded_domains:
        exclusion_string = " ".join([f"-site:{domain}" for domain in excluded_domains])
        search_query = f"{search_query} {exclusion_string}"

    search_query = f"{search_query} recipe -gallery -collection"
    logging.info(f"Final search query: {search_query}")

    ddgs = DDGS()
    recipe_urls = []

    for attempt in range(max_retries):
        try:
            results = list(
                ddgs.text(
                    keywords=search_query,
                    region="wt-wt",
                    safesearch="off",
                    max_results=num_urls * 2,
                )
            )

            if results:
                for result in results:
                    url = result.get("link") or result.get("href")
                    if url and not any(
                        domain in url for domain in (excluded_domains or [])
                    ):
                        recipe_urls.append(url)

                if recipe_urls:
                    recipe_urls = recipe_urls[:num_urls]
                    logging.info(f"Found {len(recipe_urls)} recipe URLs")
                    logging.debug(f"URLs found: {recipe_urls}")
                    break
                else:
                    logging.warning(
                        f"No valid URLs found in results on attempt {attempt + 1}"
                    )

        except Exception as e:
            logging.error(
                f"Error during recipe search (attempt {attempt + 1}/{max_retries}): {str(e)}"
            )
            if attempt < max_retries - 1:
                logging.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                continue
            else:
                logging.error("Max retries reached, returning empty list")

    end_time = time.time()
    duration = end_time - start_time

    # Create metrics event
    metrics_event = MetricsEvent(
        event_type="recipe_search.duration",
        duration=duration,
        timestamp=datetime.utcnow(),
        metadata={
            "search_query": search_query,
            "num_urls_requested": num_urls,
            "num_urls_found": len(recipe_urls),
            "attempts": attempt + 1,
        },
    )

    if not recipe_urls:
        logging.warning("No valid results found after all retry attempts")

    return recipe_urls, metrics_event
