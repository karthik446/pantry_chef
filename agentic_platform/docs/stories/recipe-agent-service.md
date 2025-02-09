Okay, let's define a detailed user story for how workflow objects should look within your `RecipeAgentService`, drawing inspiration from CrewAI's concepts but adapting it to your platform architecture.

### User Story: Workflow Object Definition in `RecipeAgentService`

*   **As a** `RecipeAgentService` developer,
*   **I want** to define a clear and structured object to represent a `recipe_workflow_full` instance within the `RecipeAgentService`,
*   **So that** I can effectively manage, track, and persist the state and progress of each workflow execution, making the orchestration logic robust and observable.

**Details:**

To manage the `recipe_workflow_full` and future workflows, we need to represent each running instance as a workflow object within the `RecipeAgentService`.  This object will hold all the relevant information about a specific execution of a workflow.  Inspired by CrewAI's concepts of Agents, Tasks, and Processes, our workflow object will encapsulate the following:

**Workflow Object Attributes (Conceptual Python Dictionary for MVP - In-Memory State):**

```python
workflow_instance = {
    "workflow_id": "unique_workflow_id_uuid",  # Unique identifier for this workflow instance (UUID)
    "workflow_type": "recipe_workflow_full",  # Type of workflow (e.g., "recipe_workflow_full", "ingredients_nutrition_gather_workflow")
    "status": "pending",  # Current status of the workflow: "pending", "running", "recipe_search_pending", "recipe_scraping_pending", "nutrition_gathering_pending", "completed", "failed"
    "current_step": "init",  #  Current step being executed: "init", "recipe_search", "recipe_scraping", "nutrition_gathering", "saving_recipes", "completed", "error"
    "start_timestamp": "2024-08-03T10:00:00Z",  # Timestamp when the workflow was initiated
    "last_updated_timestamp": "2024-08-03T10:05:00Z", # Timestamp of the last status update
    "payload": {  # Initial data provided when the workflow was started
        "search_query": "chocolate cake recipes",
        # ... other initial parameters ...
    },
    "context_data": { # To store intermediate data generated during workflow execution, step by step
        "recipe_search_results": [ # URLs found by the SearchAgent
            "https://www.example.com/recipe1",
            "https://www.example.com/recipe2",
            # ...
        ],
        "scraped_recipe_data": [ # List of structured recipe data dictionaries after scraping
            {
                "recipe_url": "https://www.example.com/recipe1",
                "title": "Delicious Chocolate Cake",
                "ingredients": ["...", "..."],
                "instructions": "...",
                # ... other scraped fields ...
            },
            # ...
        ],
        "nutrition_data_needed_ingredients": ["chocolate", "flour", "sugar"], # List of ingredients that need nutrition info
        "nutrition_data": { # Nutrition information gathered for ingredients
            "chocolate": { "calories": 500, "fat": 30, ...},
            "flour": { "calories": 100, "carbs": 20, ...},
            # ...
        }
    },
    "error_details": { # If workflow failed, store error information
        "step_failed": "recipe_scraping",
        "error_message": "Failed to scrape URL: https://www.example.com/recipeX",
        "exception_type": "requests.exceptions.Timeout",
        "stacktrace": "...",
    },
    "retries_attempted": 0, # Number of retries attempted for the current step (for future retry logic)
    # ... potentially other relevant metadata for monitoring or debugging ...
}
```

**Explanation of Attributes and their Purpose (Inspired by CrewAI and Workflow Concepts):**

*   **`workflow_id`**:  A unique identifier (UUID) for each workflow instance. This is crucial for tracking, logging, and correlating messages to the correct workflow execution.  Think of this as the "session ID" for a workflow.
*   **`workflow_type`**:  Indicates the type of workflow being executed.  For MVP, it will be `recipe_workflow_full`.  This allows the `RecipeAgentService` to handle different workflow types in the future.
*   **`status`**:  Represents the overall state of the workflow.  Status transitions will be managed by the `RecipeAgentService` as it progresses through the workflow steps.  Possible statuses:
    *   `pending`: Workflow initiated but not yet started processing.
    *   `running`: Workflow is actively executing steps.
    *   `recipe_search_pending`, `recipe_scraping_pending`, `nutrition_gathering_pending`:  Indicates which specific step is currently in progress or queued.  This provides more granular status.
    *   `completed`: Workflow finished successfully.
    *   `failed`: Workflow encountered an error and could not complete.
*   **`current_step`**:  Indicates the specific step the workflow is currently executing or has just completed.  This helps in understanding the current stage of processing.  Steps for `recipe_workflow_full` are: `init`, `recipe_search`, `recipe_scraping`, `nutrition_gathering`, `saving_recipes`, `completed`, `error`.
*   **`start_timestamp` & `last_updated_timestamp`**: Timestamps for tracking when the workflow started and when its state was last updated. Useful for monitoring duration, debugging, and potentially for cleanup of long-running or stalled workflows.
*   **`payload`**:  Stores the initial input data that triggered the workflow. For `recipe_workflow_full`, this would include the `search_query`.  This is analogous to the initial "task" input in CrewAI.
*   **`context_data`**:  This is a dictionary to store intermediate data generated at each step of the workflow.  This is where you'll keep lists of recipe URLs found, scraped recipe data, ingredients needing nutrition info, and the gathered nutrition data.  This acts as the "working memory" of the workflow instance, accumulating results as it progresses through its tasks.
*   **`error_details`**:  If the workflow fails, this dictionary will store information about the error, including the step where it failed, the error message, exception type, and potentially a stack trace.  This is crucial for debugging and error reporting.
*   **`retries_attempted`**:  For future implementation of retry mechanisms, this attribute can track how many times a step has been retried.

**How `RecipeAgentService` will use the Workflow Object:**

1.  **Workflow Initiation:** When the `RecipeAgentService` receives a `workflow_initiate` message from the `workflow_commands` queue, it will:
    *   Generate a new `workflow_id` (UUID).
    *   Create a new workflow object (Python dictionary) and populate it with `workflow_type`, `workflow_id`, `payload`, `status = "pending"`, `current_step = "init"`, and `start_timestamp`.
    *   Store this workflow object in memory (initially, for MVP).
    *   Update the `status` to `"running"` and `current_step` to `"recipe_search"`.
    *   Publish a `recipe_searches` message to trigger the `SearchAgent` step.

2.  **Step Execution and State Updates:** As the workflow progresses through its steps (recipe search, scraping, etc.):
    *   The `RecipeAgentService` will update the `status`, `current_step`, `last_updated_timestamp`, and `context_data` of the workflow object based on events (e.g., receiving `recipe_search_done`, scraping results, etc.).
    *   For example, after receiving `recipe_search_done`, it will update `workflow_instance["context_data"]["recipe_search_results"]` with the URLs, change `current_step` to `"recipe_scraping"`, and update `status` to `"recipe_scraping_pending"`.

3.  **Error Handling:** If an error occurs during any step:
    *   The `RecipeAgentService` will catch the exception.
    *   Update the workflow object's `status` to `"failed"`, `current_step` to the step where the error occurred, and populate the `error_details` dictionary with relevant error information.

4.  **Workflow Completion:** When all steps are successfully completed:
    *   Update the workflow object's `status` to `"completed"` and `current_step` to `"completed"`.
    *   Publish a `recipe_search_done` message (or a more generic `workflow_completed` message in the future).

5.  **Persistence (Future):**  For MVP, in-memory storage is fine.  For production, you will need to persist these workflow objects in a database (e.g., PostgreSQL, Redis) so that workflow state is not lost if the `RecipeAgentService` pod restarts.  You would then load and update workflow objects from the database.

**Benefits of this Workflow Object:**

*   **Clear Structure:** Provides a well-defined structure to represent workflow instances.
*   **State Management:**  Enables effective tracking of workflow status and progress.
*   **Contextual Data Storage:**  Allows storing intermediate data generated during workflow execution, making it accessible across steps.
*   **Error Tracking:**  Provides a dedicated place to record error information for debugging and monitoring.
*   **Extensibility:**  The object can be easily extended to include more attributes as your workflows become more complex (e.g., retry counts, timestamps for each step, agent assignments, etc.).
*   **Observability:**  Makes it easier to log and monitor workflow execution by providing a central object to inspect.

This detailed workflow object definition will be crucial for building a robust and manageable `RecipeAgentService` capable of orchestrating complex agentic workflows.  It provides a solid foundation for your MVP and future platform enhancements.
