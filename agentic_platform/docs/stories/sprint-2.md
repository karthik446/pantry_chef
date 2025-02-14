### Sprint Duration: 1 week (Adjustable)

### Sprint Backlog (Tasks Checklist):

** Known Issues: **

*   The RabbitMQ consumer and producer are working.. but only for recipe_searches queue.

## Diagnosing RabbitMQ `workflow_commands` Queue Issue

**Known Issue:** While RabbitMQ is set up with `workflow_commands`, `recipe_searches`, and `workflow_queue` queues, only `recipe_searches` appears to be functioning correctly. Messages published to `workflow_commands` are not being processed as expected by the `RecipeAgentService`.

Fixed it by adding a new `workflow_orchestrator.py` file to the `services/recipes` directory and also for every new deploy the port forwarding should be re-run.


**tech debt sprint**

The focus of this tech debt sprint is to implement an asynchronous consumer using `aio-pika` with base classes for `WorkflowCommandConsumer` (formerly `recipe_consumer`) and `MetricsConsumer`, and ensure both can connect to their respective queues (`recipe_searches` and `metrics_queue`). This will also help us resolve the known issue of only one queue working.

*   [x] **Task 1: Implement Asynchronous `BaseConsumer` (New File `consumer.py`):**
    *   [x] Create a new file `agentic_platform/services/recipes/src/consumer.py`.
    *   [x] Implement the `BaseConsumer` class with asynchronous connection logic using `aio-pika`.
    *   [x] The `BaseConsumer` should:
        *   [x] Accept a `queue_name` in its constructor.
        *   [x] Establish an asynchronous connection to RabbitMQ using `aio_pika.connect_robust`.
        *   [x] Declare the queue using the provided `queue_name`.
        *   [x] Define abstract methods for `process_message` and error handling.
    *   Estimated Effort: 1.5 days

*   [ ] **Task 2: Implement `WorkflowCommandConsumer`:**
    *   [x] Create a `WorkflowCommandConsumer` class that inherits from `BaseConsumer`.
    *   [x] The `WorkflowCommandConsumer` should:
        *   [x] Call the `BaseConsumer` constructor with the `recipe_searches` queue name (obtained from the environment variable `WORKFLOW_COMMANDS_QUEUE_NAME`).
        *   [x] Implement the `process_message` method to handle workflow commands (as it currently does).
        *   [x] Implement the error handling logic.
    *   Estimated Effort: 1 day

*   [x] **Task 3: Implement `MetricsConsumer`:**
    *   [x] Create a `MetricsConsumer` class that inherits from `BaseConsumer`.
    *   [x] The `MetricsConsumer` should:
        *   [x] Call the `BaseConsumer` constructor with the `metrics_queue` name (obtained from the environment variable `METRICS_QUEUE_NAME`).
        *   [x] Implement the `process_message` method to handle metrics messages (logging, etc.).
        *   [x] Implement the error handling logic.
    *   Estimated Effort: 1 day

*   [x] **Task 4: Update `workflow_consumer.py`:**
    *   [x] Modify `workflow_consumer.py` to:
        *   [x] Import the `BaseConsumer`, `WorkflowCommandConsumer`, and `MetricsConsumer` classes.
        *   [x] Instantiate both `WorkflowCommandConsumer` and `MetricsConsumer`.
        *   [x] Start both consumers in an `asyncio` event loop.
    *   Estimated Effort: 0.5 days

*   [x] **Task 5: Test Deployment and Multiple Queue Connections:**
    *   [x] Deploy the updated service to a test environment.
    *   [x] Verify that both `WorkflowCommandConsumer` and `MetricsConsumer` connect to their respective queues.
    *   [x] Publish test messages to both queues and ensure they are processed correctly.
    *   Estimated Effort: 0.5 days

**1. Recipe Scraping Agent Implementation:**

*   [ ] **Task 1.1: Define Scraping Event Types**
    *   [x] create class RecipeMetricsEventType(Enum):
    *   [ ] Define metadata structure for each event type
    *   [ ] Add logging for each event type
    *   Estimated Effort: 0.5 days

*   [ ] **Task 1.2: Enhance Library Scraping Method**
    *   [ ] Wrap recipe-scrapers library with metrics collection
    *   [ ] Implement Recipe/MetricsEvents tuple return
    *   [ ] Add duration tracking
    *   [ ] Add detailed failure metadata
    *   Estimated Effort: 1 day

*   [ ] **Task 1.3: Enhance Custom Scraping Method**
    *   [ ] Structure custom scraping with metrics collection
    *   [ ] Implement Recipe/MetricsEvents tuple return
    *   [ ] Track parsing attempts in metadata
    *   [ ] Add failure categorization
    *   Estimated Effort: 1 day

*   [ ] **Task 1.4: Implement AI Scraping Method**
    *   [ ] Structure AI scraping with metrics collection
    *   [ ] Track token usage in metrics
    *   [ ] Add timeout handling
    *   [ ] Implement proper validation
    *   Estimated Effort: 1 day

*   [ ] **Task 1.5: Implement Sequential Scraping Logic**
    *   [ ] Implement priority-based method execution
    *   [ ] Collect and combine metrics from all attempts
    *   [ ] Add comprehensive logging
    *   [ ] Test parallel processing scenarios
    *   Estimated Effort: 1 day

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

**3. Consumer Refactoring and Queue Handling:**

*   [ ] **Task 3.1: Refactor Consumer with BaseConsumer (New File consumer.py)**
*   [ ] Create a new file agentic_platform/services/recipes/src/consumer.py.
*   [ ] Implement the BaseConsumer class with asynchronous connection using aio-pika.
*   [ ] Ensure the consumer creates queues programmatically based on environment variables.
*   Estimated Effort: 1.5 days

*   [ ] **Task 3.2: Implement WorkflowCommandConsumer and MetricsConsumer**
*   [ ] Implement WorkflowCommandConsumer and MetricsConsumer, inheriting from BaseConsumer.
*   [ ] Adapt message processing logic for each consumer.
*   Estimated Effort: 1 day

**4. Testing and Refinement:**

*   [ ] **Task 4.1: Unit Tests for recipe_scraper.py**
*   [ ] Create tests/test_recipe_scraper.py.
*   [ ] Write unit tests for scrape_recipe, find_print_link, clean_instructions, parse_ingredient, and clean_text.
*   [ ] Use mock objects/responses to simulate different scenarios (successful scrapes, various website structures, errors).
*   Estimated Effort: 1.5 days

*   [ ] **Task 4.2: Unit Tests for auth_client.py**
*   [ ] Create tests/test_auth_client.py.
*   [ ] Write unit tests for the abstract authentication class and the concrete APIKeyAuthClient, focusing on token retrieval, caching, and refresh logic.
*   [ ] Mock Redis interactions for testing.
*   Estimated Effort: 0.5 days

*   [ ] **Task 4.3: Refactor search_agent.py**
*   [ ] Remove the hardcoded recipe website base URLs.
*   [ ] Ensure the search query construction with excluded domains is robust.
*   Estimated Effort: 0.5 days

*   [ ] **Task 4.4: Test Deployment and Multiple Queue Connections**
*   [ ] Deploy the updated service to a test environment.
*   [ ] Verify that both WorkflowCommandConsumer and MetricsConsumer connect to their respective queues.
*   [ ] Publish test messages to both queues and ensure they are processed correctly.
*   Estimated Effort: 0.5 days

**Sprint Goal Review & Testing:**

*   [ ] **Task 5.1: End-to-End Testing**
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
*   **Day 4:** Task 1.4, 3.1
*   **Day 5:** Task 3.2, 4.1
*   **Day 6:** Task 4.2, 4.3, 4.4
*   **Day 7:** Task 5.1, Buffer, bug fixing, documentation, sprint review.