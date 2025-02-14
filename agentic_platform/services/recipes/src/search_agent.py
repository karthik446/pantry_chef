import logging
from smolagents import DuckDuckGoSearchTool


def search_recipes(
    search_query: str, excluded_domains: list = None, num_urls: int = 10
) -> list:
    """
    Searches for recipes using DuckDuckGo via smolagents, with domain exclusion in the search query.

    This function uses the DuckDuckGoSearchTool from smolagents to perform a web search
    and extract recipe URLs from the search results, excluding specified domains
    by incorporating them into the search query.

    Args:
        search_query: The search query to use for recipe search.
        excluded_domains: A list of domains to exclude from the search results (optional).
        num_urls: The maximum number of recipe URLs to return (default: 10).

    Returns:
        A list of recipe URLs extracted from search results, excluding specified domains,
        limited to the specified number of URLs.
    """
    logging.info(
        f"Searching for recipes with query: {search_query} using DuckDuckGoSearchTool, excluding domains: {excluded_domains}, num_urls: {num_urls}"
    )

    search_tool = DuckDuckGoSearchTool()  # Initialize the DuckDuckGoSearchTool

    # Build the search query with domain exclusions
    if excluded_domains:
        exclusion_string = " ".join(
            [f"-site:{domain}" for domain in excluded_domains]
        )  # Create a string of "-site:domain" exclusions
        search_query = (
            f"{search_query} {exclusion_string}"  # Add exclusions to the search query
        )

    search_query = f"{search_query} recipe -gallery -collection"
    logging.info(f"Search query: {search_query}")
    try:
        search_results = search_tool.forward(
            search_query
        )  # Perform web search using DuckDuckGoSearchTool
        logging.debug(
            f"Search Results: {search_results}"
        )  # Log raw search results for debugging

        recipe_urls = []
        if search_results and isinstance(
            search_results, str
        ):  # Check if search results are valid
            results_list = search_results.split("\n")
            # Filter out non-URL lines and headers
            recipe_urls = [
                url
                for url in results_list
                if url
                and not url.startswith("#")
                and not url.isspace()
                and ("http://" in url or "https://" in url)
            ]
            recipe_urls = recipe_urls[:num_urls]  # Limit to requested number of URLs

        logging.info(f"Found recipe URLs: {recipe_urls}")
        return recipe_urls

    except Exception as e:
        logging.error(f"Error during recipe search with DuckDuckGoSearchTool: {e}")
        return []  # Return empty list in case of error
