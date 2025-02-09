### Sprint Duration: 1 week (Adjustable)

### Sprint Backlog (Tasks Checklist):

** Known Issues: **

*  The RabbitMQ consumer and producer are working.. but only for recipe_searches queue.  

## Diagnosing RabbitMQ `workflow_commands` Queue Issue

**Known Issue:**  While RabbitMQ is set up with `workflow_commands`, `recipe_searches`, and `workflow_queue` queues, only `recipe_searches` appears to be functioning correctly. Messages published to `workflow_commands` are not being processed as expected by the `RecipeAgentService`.

**Potential Causes & Troubleshooting Steps:**

This issue could stem from problems in several areas:

**1. Consumer Configuration in `RecipeAgentService`:**

*   **Cause:** The `RecipeAgentService` might not be correctly configured to consume from the `workflow_commands` queue.  It might be listening to the wrong queue name, using incorrect connection parameters, or the consumer logic itself might have errors.
    *   **Checks:**
        *   **Verify Queue Name:** Double-check the queue name in the `workflow_consumer.py` code (where the consumer is set up) against the actual queue name in RabbitMQ management UI (`workflow_commands`). Ensure there are no typos or case mismatches.
        *   **Connection Details:** Confirm that the RabbitMQ connection parameters (host, port, username, password, virtual host) in `workflow_consumer.py` are correct and match the RabbitMQ setup. Environment variables used for these parameters should be correctly set in the Kubernetes deployment.
        *   **Consumer Logic Errors:** Review the consumer callback function in `workflow_consumer.py` (specifically the `process_workflow_command` function). Look for any logical errors, exceptions that might be silently caught, or issues preventing message acknowledgement.  Ensure proper logging is in place within the callback to track message processing.
        *   **Multiple Consumers:**  Accidentally running multiple instances of the consumer code that are competing for messages or misconfigured. Ensure only one consumer instance is expected to be running and processing `workflow_commands`.

**2. Producer Configuration (Message Publishing):**

*   **Cause:** Messages intended for `workflow_commands` might be incorrectly published to a different exchange or routing key, or not published at all.
    *   **Checks:**
        *   **Publishing Code Review:** Examine the code that publishes messages intended for `workflow_commands`. Verify the exchange name, routing key (if applicable), and queue name used during publishing are indeed targeting the `workflow_commands` queue.
        *   **Message Format:** Ensure the message payload being published to `workflow_commands` conforms to the expected schema (`workflow_initiate` message schema defined in `docs/dev/message-schemas.md`). Validation errors on the consumer side could lead to messages being rejected or ignored.
        *   **Manual Publishing Test:** Use the RabbitMQ management UI or `rabbitmqadmin` CLI tool to manually publish a test message directly to the `workflow_commands` queue. This bypasses the producer code and isolates the consumer side for testing. Observe if the `RecipeAgentService` consumer processes this manually published message.

**3. RabbitMQ Queue Configuration:**

*   **Cause:**  While the queue configurations seem similar (quorum, durability), there might be subtle differences or misconfigurations affecting `workflow_commands`.
    *   **Checks:**
        *   **Queue Properties Comparison:**  Carefully compare all properties of `workflow_commands` and `recipe_searches` queues in the RabbitMQ management UI. Look for any discrepancies in permissions, policies, or other settings beyond the listed `x-queue-type`, `x-max-length`, etc.
        *   **Queue Bindings (Exchanges):** Verify if `workflow_commands` queue is correctly bound to the expected exchange.  If direct exchange is used, ensure the routing key matches the queue name.
        *   **Queue State:** Check the RabbitMQ management UI for the `workflow_commands` queue's state. Is it idle? Are there messages piling up and unacknowledged? Are there any error indicators associated with the queue?

**4. Network Connectivity & Firewall:**

*   **Cause:** Network issues or firewall rules might be preventing communication between the `RecipeAgentService` and RabbitMQ specifically on ports or protocols used for `workflow_commands` queue interactions. (Less likely if `recipe_searches` is working, but worth a quick check).
    *   **Checks:**
        *   **Kubernetes Network Policies:** Review Kubernetes network policies to ensure they are not inadvertently blocking traffic between the `RecipeAgentService` pod and the RabbitMQ service on the relevant ports.
        *   **Firewall Rules:** If firewalls are in place outside Kubernetes, verify rules allow communication between the Recipe Agent Service and RabbitMQ on the necessary ports.


**Sprint 2 Context:**

This issue directly impacts Sprint 2, as `workflow_commands` queue is intended to be the entry point for initiating the `recipe_workflow_full` workflow, including triggering the recipe scraping and saving steps planned for this sprint. Resolving this queue issue is a prerequisite for making progress on core Sprint 2 tasks.

By systematically checking these potential causes, you should be able to pinpoint the reason why the `workflow_commands` queue is not functioning as expected and implement the necessary fix. Start with the consumer configuration and message publishing aspects, as these are often the most common sources of such issues.



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