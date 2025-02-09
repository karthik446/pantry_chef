### Sprint Duration: 1 week (Adjustable)

### Sprint Backlog (Tasks Checklist):

**1. Recipe Scraping Agent Implementation:**

*   [ ] **Task 1.1: Create recipe_scraper.py (New File)**
*   [ ] Create a new file agentic_platform/services/recipes/src/recipe_scraper.py.
*   [ ] Define a function scrape_recipe(url: str) -> dict that takes a URL and returns a dictionary containing the scraped recipe data (or an error indication). This function will be largely based on the existing scrape_recipe function in recipe_agent_old.py, but adapted for asynchronous operation and improved error handling. Except that we will try to use an ai model to scrape the recipe if the code scraper fails. 
*   [ ] Implement robust error handling (timeouts, request exceptions, parsing errors).
*   [ ] Return a dictionary in the format expected by the API (matching dtos.CreateRecipeDTO in handler.go). Include error key if scraping fails.
*   Estimated Effort: 1.5 days

*   [ ] **Task 1.2: Implement Helper Functions in recipe_scraper.py**
*   [ ] Port the helper functions from recipe_agent_old.py to recipe_scraper.py: find_print_link, clean_instructions, parse_ingredient, clean_text.
*   [ ] Adapt these functions as needed for the new scraper.
*   Estimated Effort: 1 day

*   [ ] **Task 1.3: Implement Asynchronous Scraping in workflow_consumer.py**
*   [ ] Create a new function scrape_recipes_parallel(urls: list[str]) -> list[dict] in workflow_consumer.py.
*   [ ] Use asyncio.gather to concurrently scrape multiple URLs using scrape_recipe.
*   [ ] Handle errors from individual scrapes gracefully (e.g., log the error and continue with other URLs).
*   [ ] Return a list of dictionaries, each representing a scraped recipe (or containing an error).
*   Estimated Effort: 1 day

*   [ ] **Task 1.4: Integrate Scraper with Workflow in workflow_consumer.py**
*   [ ] Modify _execute_recipe_search_step to use scrape_recipes_parallel instead of calling search_recipes directly.
*   [ ] After getting the list of URLs, call scrape_recipes_parallel to scrape the recipes.
*   [ ] Process the results, handling both successful scrapes and errors.
*   Estimated Effort: 0.5 days

**2. Authentication and API Interaction with Redis Caching:**

*   [ ] **Task 2.1: Implement Redis Cache Client**
*   [ ] Add redis-py dependency to RecipeAgentService requirements.txt.
*   [ ] Implement a Redis client in workflow_consumer.py to store and retrieve auth tokens.
*   [ ] Configure Redis connection details using environment variables.
*   Estimated Effort: 0.5 days

*   [ ] **Task 2.2: Abstract Authentication Logic**
*   [ ] Create an abstract authentication class/interface in a new file agentic_platform/services/recipes/src/auth_client.py.
*   [ ] Implement a concrete authentication class (e.g., APIKeyAuthClient) that uses an API key for authentication and stores/retrieves tokens from Redis.
*   [ ] Design the authentication logic to be easily extensible for other auth methods in the future.
*   Estimated Effort: 1 day

*   [ ] **Task 2.3: Implement API Submission with Authentication in workflow_consumer.py**
*   [ ] Modify submit_recipe_to_api to use the abstracted authentication client to obtain and include the auth token in API requests.
*   [ ] Implement token refresh logic if the API returns an authentication error (using the Redis cached token).
*   [ ] Handle API response (success/failure) and log appropriately, including authentication-related errors.
*   Estimated Effort: 1 day

**3. Testing and Refinement:**

*   [ ] **Task 3.1: Unit Tests for recipe_scraper.py**
*   [ ] Create tests/test_recipe_scraper.py.
*   [ ] Write unit tests for scrape_recipe, find_print_link, clean_instructions, parse_ingredient, and clean_text.
*   [ ] Use mock objects/responses to simulate different scenarios (successful scrapes, various website structures, errors).
*   Estimated Effort: 1.5 days

*   [ ] **Task 3.2: Unit Tests for auth_client.py**
*   [ ] Create tests/test_auth_client.py.
*   [ ] Write unit tests for the abstract authentication class and the concrete APIKeyAuthClient, focusing on token retrieval, caching, and refresh logic.
*   [ ] Mock Redis interactions for testing.
*   Estimated Effort: 0.5 days

*   [ ] **Task 3.3: Refactor search_agent.py**
*   [ ] Remove the hardcoded recipe website base URLs.
*   [ ] Ensure the search query construction with excluded domains is robust.
*   Estimated Effort: 0.5 days

**Sprint Goal Review & Testing:**

*   [ ] **Task 4.1: End-to-End Testing**
*   [ ] Deploy the updated service.
*   [ ] Manually trigger workflows and verify:
    *   Recipe search results are retrieved.
    *   Recipes are scraped correctly.
    *   Data is submitted to the API with correct authentication.
    *   Workflow state is updated correctly.
    *   Logging provides sufficient information, including auth-related events.
    *   Redis caching of auth tokens is working as expected.
*   Estimated Effort: 1 day

**Timeline (Example 7-day week):**

*   **Day 1:** Task 1.1, 2.1
*   **Day 2:** Task 1.2, 2.2
*   **Day 3:** Task 1.3, 2.3
*   **Day 4:** Task 1.4, 1.5
*   **Day 5:** Task 3.1
*   **Day 6:** Task 3.2, 3.3
*   **Day 7:** Task 4.1, Buffer, bug fixing, documentation, sprint review.