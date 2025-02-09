# AS of 2025-02-09
## Recipe Agent Platform System Design

This document outlines the system design for the Recipe Agent Platform MVP, focusing on the `recipe_workflow_full` workflow.

### 1. High-Level Architecture

```
+---------------------+     +---------------------+     +---------------------+
| Pantry Chef API (Go) | <-- | Recipe Agent Service | --> | Message Broker      |
| (Data Storage, API) |     | (Python Workflow     |     | (RabbitMQ)          |
+---------------------+     | Orchestration, Agents)|     +---------------------+
      ^                               |                         ^
      |                               |                         |
      |                               v                         |
      +---------------------+     +---------------------+     |
      | PostgreSQL Database | <-- | Redis Cache         |-----+
      | (Persistent Data)   |     | (Auth Token Cache)  |
      +---------------------+     +---------------------+

```

**Components:**

*   **Pantry Chef API (Go):**
    *   Responsible for data persistence (recipes, ingredients, etc.) in the PostgreSQL database.
    *   Provides REST API endpoints for creating, reading, updating, and deleting recipe data.
    *   Handles authentication and authorization for API access.
    *   Deployed as a Kubernetes service.
*   **Recipe Agent Service (Python):**
    *   **Core Workflow Orchestrator:** Manages the `recipe_workflow_full` and potentially other workflows.
    *   **Message Consumer:** Consumes `workflow_commands` from RabbitMQ to initiate workflows.
    *   **Search Agent:** Uses tools like DuckDuckGo to find recipe URLs based on search queries.
    *   **Recipe Scraping Agent:**  Scrapes recipe data from URLs using a combination of code-based parsing and AI-powered fallback.
    *   **API Client:** Interacts with the Pantry Chef API to save scraped recipe data.
    *   **State Management:** Manages workflow state (initially in-memory, with potential for Redis persistence later).
    *   Deployed as a Kubernetes pod.
*   **Message Broker (RabbitMQ):**
    *   Facilitates asynchronous communication between services.
    *   Queues:
        *   `workflow_commands`: Receives workflow initiation commands.
        *   `recipe_searches`:  (Potentially used for decoupling search, currently search is within Recipe Agent Service).
        *   `recipe_search_done`: (Potentially used for decoupling search).
        *   `recipe_scrape_needed`: (Future, could be used to decouple scraping).
        *   `nutrition_for_ingredient`: (Future, for nutrition service).
    *   Deployed as a Kubernetes service.
*   **PostgreSQL Database:**
    *   Persistent storage for recipe data, ingredient data, user data, etc.
    *   Managed by Kubernetes or a cloud-managed database service.
*   **Redis Cache:**
    *   Used for caching authentication tokens to improve API interaction efficiency and reduce API load.
    *   Potentially used for caching frequently accessed data or workflow state in the future.
    *   Deployed as a Kubernetes service.

### 2. `recipe_workflow_full` Workflow

```
[Workflow Initiation]
    |
    v
[Recipe Agent Service receives 'workflow_initiate' message on 'workflow_commands' queue]
    |
    v
[Recipe Agent Service creates Workflow Instance (in-memory)]
    |
    v
[Recipe Agent Service executes 'recipe_search' step]
    |
    v
[Search Agent (within Recipe Agent Service) uses DuckDuckGoSearchTool to find recipe URLs]
    |
    v
[Recipe Agent Service executes 'recipe_scraping' step (Sprint 2 focus)]
    |
    v
[Recipe Scraping Agent (within Recipe Agent Service) scrapes URLs in parallel]
    |   +-----> [Code-Based Scraper (BeautifulSoup, aiohttp)] --> [Successful Scrape]
    |   |
    +-----> [AI-Powered Scraper (LLM Fallback)] -------------> [Successful Scrape or Error]
    |
    v
[Recipe Agent Service processes scraped recipe data]
    |
    v
[Recipe Agent Service executes 'save_recipe' step]
    |
    v
[Recipe Agent Service (API Client) calls Pantry Chef API to save recipe (authenticated)] (Sprint 2 focus)
    |
    v
[Pantry Chef API saves recipe to PostgreSQL]
    |
    v
[Recipe Agent Service updates Workflow Instance status to 'completed']
    |
    v
[Workflow Completed]
```

**Workflow Steps:**

1.  **Workflow Initiation:** A `workflow_initiate` message is published to the `workflow_commands` queue. (See `agentic_platform/docs/stories/sprint-plan-1.md` for message schema and handling).
2.  **Recipe Search:** The `Recipe Agent Service` consumes the message, initiates a workflow instance, and executes the `recipe_search` step using the `search_recipes` function (see `agentic_platform/services/recipes/src/search_agent.py` startLine: 5 endLine: 7).
3.  **Recipe Scraping (Sprint 2):**
    *   The `Recipe Agent Service` executes the `recipe_scraping` step.
    *   For each recipe URL obtained from the search step, the `Recipe Scraping Agent` attempts to scrape recipe data.
    *   **Code-Based Scraping:**  First, it uses `BeautifulSoup`, `aiohttp`, and `asyncio` (as planned in Sprint 2 - `agentic_platform/docs/stories/sprint-2.md` Task 1.3) to parse HTML and extract structured data (title, ingredients, instructions, etc.), leveraging helper functions (ported from `recipe_agent_old.py` - `agentic_platform/services/recipes/src/recipe_agent_old.py`).
    *   **AI-Powered Scraping Fallback (Sprint 2 - `agentic_platform/docs/stories/sprint-2.md` Task 1.1):** If code-based scraping fails to parse critical information (ingredients, instructions) or encounters errors, it falls back to an AI-powered scraping approach. This could involve:
        *   Using an LLM (e.g., via an API like OpenAI, or a locally hosted model) to analyze the HTML content and extract recipe data in a more flexible and robust way.
        *   Potentially using agentic frameworks to guide the LLM in navigating the webpage and identifying recipe elements.
4.  **Save Recipe:**
    *   The `Recipe Agent Service` executes the `save_recipe` step.
    *   It uses an API client to send the scraped recipe data to the Pantry Chef API (Go) to be saved in the PostgreSQL database.
    *   **Authentication (Sprint 2 - `agentic_platform/docs/stories/sprint-2.md` Section 2):** API requests are authenticated using an API key. The `Recipe Agent Service` will:
        *   Use a Redis client (Sprint 2 - `agentic_platform/docs/stories/sprint-2.md` Task 2.1) to cache authentication tokens.
        *   Implement abstract authentication logic (Sprint 2 - `agentic_platform/docs/stories/sprint-2.md` Task 2.2) and a concrete `APIKeyAuthClient` to handle token retrieval, caching, and refresh.
        *   Include the auth token in API requests when submitting recipes (Sprint 2 - `agentic_platform/docs/stories/sprint-2.md` Task 2.3).
5.  **Workflow Completion:** The `Recipe Agent Service` updates the workflow instance status to `completed`. (Future: could publish a `workflow_completed` message).

### 3. Component Deep Dive (Relevant to Sprint 2)

*   **Recipe Agent Service (Python):**
    *   **Recipe Scraping Agent (Sprint 2 Focus):**
        *   **`recipe_scraper.py` (Sprint 2 - `agentic_platform/docs/stories/sprint-2.md` Task 1.1 & 1.2):**  Will contain the `scrape_recipe(url: str)` function. This function will implement both code-based scraping (initially based on `recipe_agent_old.py` - `agentic_platform/services/recipes/src/recipe_agent_old.py`) and the AI-powered fallback. Helper functions for parsing and cleaning recipe data will also reside here.
        *   **Asynchronous Scraping (Sprint 2 - `agentic_platform/docs/stories/sprint-2.md` Task 1.3 & 1.4):** `workflow_consumer.py` will implement `scrape_recipes_parallel(urls: list[str])` using `asyncio` and `aiohttp` to scrape multiple URLs concurrently, calling `scrape_recipe` for each URL.  `_execute_recipe_search_step` (see `agentic_platform/services/recipes/src/workflow_consumer.py` startLine: 43 endLine: 79) will be modified to use this parallel scraping function.
    *   **Authentication and API Client (Sprint 2 Focus - Section 2):**
        *   **Redis Client (Sprint 2 - `agentic_platform/docs/stories/sprint-2.md` Task 2.1):** Integrated into `workflow_consumer.py` to interact with Redis for caching auth tokens.
        *   **`auth_client.py` (Sprint 2 - `agentic_platform/docs/stories/sprint-2.md` Task 2.2):** Will define the abstract authentication class and the concrete `APIKeyAuthClient`. This will encapsulate the authentication logic and token management.
        *   **API Submission (Sprint 2 - `agentic_platform/docs/stories/sprint-2.md` Task 2.3):** `workflow_consumer.py`'s `submit_recipe_to_api` function will be updated to use the `APIKeyAuthClient` for authentication when calling the Pantry Chef API.

### 4. Deployment Architecture

*   **Kubernetes:** The entire platform is deployed on Kubernetes for container orchestration, scalability, and resilience.
*   **Separate Pods/Services:** Each component (API, Recipe Agent Service, RabbitMQ, Redis, PostgreSQL) is deployed as a separate Kubernetes pod or service, allowing for independent scaling and management.
*   **Environment Variables:** Configuration (API endpoints, RabbitMQ connection details, Redis connection details, API keys, etc.) is managed through Kubernetes environment variables, ensuring flexibility and security.
*   **Monitoring and Logging:** New Relic and Opentelemetry are used for monitoring and observability. Centralized logging (e.g., using Elasticsearch, Fluentd, and Kibana - EFK stack or similar) would be beneficial for aggregating logs from all components.

### 5. Sprint 2 and System Design

Sprint 2 is crucial for building the core recipe scraping functionality and securing API interactions, which are essential parts of the overall system design.

*   **Recipe Scraping Agent (Tasks 1.1 - 1.4):** Directly implements the `recipe_scraping` step in the `recipe_workflow_full` workflow, addressing the need to extract recipe data from URLs. The AI fallback in Task 1.1 enhances the robustness of the scraper, addressing the "skipped recipes" issue by providing a more flexible parsing mechanism when code-based scraping fails.
*   **Authentication and API Interaction (Tasks 2.1 - 2.3):** Enables the `save_recipe` step in the workflow by providing secure and efficient communication with the Pantry Chef API. Redis caching improves performance and reduces API load.
*   **Testing and Refinement (Tasks 3.1 - 3.3 & 4.1):** Ensures the quality and reliability of the implemented components, validating that they function correctly within the overall system.

### 6. Addressing "Skipped Recipes" Issue

The AI-powered scraping fallback is specifically designed to address the issue of skipped recipes due to parsing failures in the code-based scraper. By using an LLM, the system gains:

*   **Flexibility:** LLMs can understand and extract information from unstructured or semi-structured HTML content, even if the website's structure deviates from expected patterns.
*   **Robustness:** LLMs are less susceptible to minor website changes that might break code-based parsers.
*   **Improved Data Extraction:** LLMs can potentially extract more complete and accurate recipe data, even from complex or poorly formatted websites.

By combining code-based scraping for efficiency and AI-powered scraping for robustness, the Recipe Agent Platform aims to achieve a balance between performance and reliability in recipe data extraction.

This system design provides a comprehensive overview of the Recipe Agent Platform, highlighting the role of Sprint 2 in building key functionalities. Let me know if you have any specific areas you'd like to delve deeper into or any adjustments you'd like to make!
