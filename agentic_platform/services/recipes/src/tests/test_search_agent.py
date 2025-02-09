from src.search_agent import search_recipes


def test_search_recipes_basic():
    results = search_recipes("chocolate cake")
    assert isinstance(results, list)
    assert len(results) > 0


def test_search_recipes_excluded_domains():
    results = search_recipes("chocolate cake", excluded_domains=["example.com"])
    assert isinstance(results, list)
    # Add more assertions to check if the excluded domains are actually excluded
