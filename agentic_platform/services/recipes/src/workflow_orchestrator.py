import logging
from datetime import datetime
import uuid
import time
import pika
import os
import json
from search_agent import search_recipes
from event_models import WorkflowType, WorkflowPayload
from recipe_scraper_step import RecipeScraperWorkflowStep
import aio_pika
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash", generation_config={"temperature": 0})


class WorkflowOrchestrator:
    """
    Orchestrates the execution of workflows.
    """

    def __init__(self):
        """
        Initializes the WorkflowOrchestrator.
        """
        self.workflow_instances = {}  # In-memory workflow instance storage (for MVP)
        logging.info("WorkflowOrchestrator initialized.")

        # Initialize RabbitMQ connection parameters
        self.rabbitmq_host = os.environ.get("RABBITMQ_HOST", "localhost")
        self.rabbitmq_port = int(os.environ.get("RABBITMQ_PORT", 5672))
        self.rabbitmq_user = os.environ.get("RABBITMQ_USER", "guest")
        self.rabbitmq_password = os.environ.get("RABBITMQ_PASSWORD", "guest")
        self.metrics_queue_name = os.environ.get("METRICS_QUEUE_NAME", "metrics_queue")

        # Initialize RabbitMQ connection asynchronously
        self.connection = None
        self.channel = None

        self.scraperStep = RecipeScraperWorkflowStep(model)

    async def _publish_to_metrics_queue(self, message_json):
        """
        Publishes a message to the metrics queue.
        """
        try:
            if not self.channel or self.channel.is_closed:
                await self._connect_to_rabbitmq()
            channel = await self.connection.channel()
            await channel.default_exchange.publish(
                aio_pika.Message(body=message_json.encode()),
                routing_key=self.metrics_queue_name,
            )
            logging.info(f"Sent message to metrics queue: {message_json}")
        except Exception as e:
            logging.error(f"Error publishing to metrics queue: {e}")

    async def _send_metrics(self, workflow_instance):
        """
        Sends metrics about the workflow execution to the metrics queue.
        """
        try:
            workflow_name = workflow_instance["workflow_type"]
            message = {
                "event_type": f"{workflow_name}.status",
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": {
                    "workflow_id": str(workflow_instance["workflow_id"]),
                    "workflow_type": workflow_instance["workflow_type"],
                    "status": workflow_instance["status"],
                    "current_step": workflow_instance["current_step"],
                    "start_timestamp": workflow_instance["start_timestamp"],
                    "last_updated_timestamp": workflow_instance[
                        "last_updated_timestamp"
                    ],
                },
            }
            message_json = json.dumps(message)
            await self._publish_to_metrics_queue(message_json)
        except Exception as e:
            logging.error(f"Error sending metrics: {e}")

    async def _connect_to_rabbitmq(self):
        """Connects to RabbitMQ using aio_pika."""
        try:
            self.connection = await aio_pika.connect_robust(
                host=self.rabbitmq_host,
                port=self.rabbitmq_port,
                login=self.rabbitmq_user,
                password=self.rabbitmq_password,
            )
            self.channel = await self.connection.channel()

            # Declare the metrics queue
            await self.channel.declare_queue(
                self.metrics_queue_name,
                durable=True,
                arguments={
                    "x-queue-type": "quorum",
                    "x-max-length": 10000,
                    "x-max-length-bytes": 104857600,
                    "x-overflow": "reject-publish",
                },
            )
            logging.info(
                f"Connected to RabbitMQ and declared queue: {self.metrics_queue_name}"
            )
        except Exception as e:
            logging.error(f"Error connecting to RabbitMQ: {e}")
            if self.channel and not self.channel.is_closed:
                await self.channel.close()
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
            raise

    async def initiate_workflow(
        self, workflow_type: WorkflowType, workflow_payload: WorkflowPayload
    ):
        """
        Initiates a new workflow instance.
        """
        workflow_id = uuid.uuid4()
        workflow_instance = {
            "workflow_id": workflow_id,
            "workflow_type": workflow_type,
            "payload": workflow_payload,
            "status": "pending",
            "current_step": "init",
            "start_timestamp": datetime.now().isoformat(),
            "last_updated_timestamp": datetime.now().isoformat(),
            "context_data": {},
        }
        self.workflow_instances[workflow_id] = workflow_instance
        logging.info(
            f"Initiating workflow: workflow_id={workflow_id}, workflow_type={workflow_type}"
        )
        logging.info(
            f"Workflow {workflow_id} initiated: type={workflow_type}, status=pending"
        )

        # Start the workflow execution
        await self._execute_workflow(workflow_id)
        return workflow_id

    async def _execute_workflow(self, workflow_id: uuid.UUID):
        """
        Executes the workflow steps based on the workflow type.
        """
        workflow_instance = self.workflow_instances.get(workflow_id)
        if not workflow_instance:
            logging.error(f"Workflow instance not found: {workflow_id}")
            return

        workflow_type = workflow_instance["workflow_type"]
        logging.info(
            f"Processing '{workflow_type}' workflow: workflow_id={workflow_id}"
        )

        if workflow_type == "recipe_workflow_full":
            await self._execute_recipe_workflow_full(workflow_id)
        else:
            logging.warning(f"Unknown workflow type: {workflow_type}")

    async def _execute_recipe_workflow_full(self, workflow_id: uuid.UUID):
        """
        Executes the steps for the 'recipe_workflow_full' workflow.
        """
        workflow_instance = self.workflow_instances.get(workflow_id)
        workflow_type = workflow_instance["workflow_type"]

        if not workflow_instance:
            logging.error(f"Workflow instance not found: {workflow_id}")
            return

        try:
            # Step 1: Recipe Search
            logging.info(f"Executing recipe search step: workflow_id={workflow_id}")
            search_query = workflow_instance["payload"].get("search_query")
            excluded_domains = workflow_instance["payload"].get("excluded_domains", [])
            number_of_urls = workflow_instance["payload"].get("number_of_urls", 10)
            recipe_urls = search_recipes(search_query, excluded_domains, number_of_urls)
            workflow_instance["context_data"]["recipe_search_results"] = recipe_urls
            workflow_instance["current_step"] = "recipe_search"
            workflow_instance["status"] = "recipe_search_completed"
            workflow_instance["last_updated_timestamp"] = datetime.now().isoformat()
            logging.info(
                f"Recipe search completed: workflow_id={workflow_id}, found {len(recipe_urls)} recipes"
            )

            # Step 2: Recipe Scraping
            workflow_instance["current_step"] = "recipe_scraping"
            workflow_instance["status"] = "recipe_scraping_in_progress"
            workflow_instance["last_updated_timestamp"] = datetime.now().isoformat()
            logging.info(
                f"Starting parallel recipe scraping: workflow_id={workflow_id}"
            )

            scraped_recipes = await self.scraperStep.scrape_recipes(recipe_urls)
            workflow_instance["context_data"]["scraped_recipes"] = scraped_recipes
            workflow_instance["status"] = "recipe_scraping_completed"
            workflow_instance["last_updated_timestamp"] = datetime.now().isoformat()

            # Structured logging for scraped recipes
            logging.info(
                f"Recipe scraping completed: workflow_id={workflow_id}, total recipes attempted={len(scraped_recipes)}"
            )

            successful_recipes = 0
            for i, (recipe, metrics) in enumerate(scraped_recipes, 1):
                if recipe:
                    successful_recipes += 1
                    logging.info(
                        f"Recipe {i} (Success) - "
                        f"Title: {recipe.title}, "
                        f"URL: {recipe.source_url}, "
                        f"Ingredients: {len(recipe.ingredients)}"
                    )
                else:
                    logging.error(
                        f"Recipe {i} (Failed) - "
                        f"URL: {metrics[0].metadata.get('url', 'Unknown URL')}, "
                        f"Error: {metrics[0].metadata.get('error', 'Unknown error')}"
                    )

            logging.info(
                f"Successfully scraped {successful_recipes} out of {len(scraped_recipes)} recipes"
            )

            # Step 3: Placeholder for Saving Recipes to API (Not yet implemented)
            # ... (API saving logic would go here in the future) ...
            workflow_instance["current_step"] = "save_recipes_api"
            workflow_instance["status"] = "save_recipes_api_pending"
            workflow_instance["last_updated_timestamp"] = datetime.now().isoformat()
            logging.info(f"Save recipes to API step pending: workflow_id={workflow_id}")

            # Workflow Completion
            workflow_instance["status"] = "completed"
            workflow_instance["current_step"] = "completed"
            workflow_instance["last_updated_timestamp"] = datetime.now().isoformat()
            logging.info(
                f"Workflow '{workflow_type}' completed: workflow_id={workflow_id}"
            )

            await self._send_metrics(workflow_instance)

        except Exception as e:
            workflow_instance["status"] = "failed"
            workflow_instance["current_step"] = "failed"
            workflow_instance["last_updated_timestamp"] = datetime.now().isoformat()
            workflow_instance["error_details"] = str(e)
            logging.error(f"Error executing workflow {workflow_id}: {e}", exc_info=True)
            await self._send_metrics(workflow_instance)

    async def _execute_recipe_search_step(self, workflow_instance: dict) -> None:
        """
        Executes the recipe search step for the given workflow instance.

        Args:
            workflow_instance: The workflow instance dictionary.
        """
        workflow_id = workflow_instance["workflow_id"]
        try:
            logging.info(f"Executing recipe search step: workflow_id={workflow_id}")

            # Start the timer
            start_time = time.time()

            # Access workflow payload attributes using the Pydantic model
            search_query = workflow_instance["workflow_payload"]["search_query"]
            excluded_domains = workflow_instance["workflow_payload"].get(
                "excluded_domains", []
            )  # Get excluded_domains, default to [] if not present
            num_urls = workflow_instance["workflow_payload"].get(
                "number_of_urls", 10
            )  # Get number_of_urls, default to 10 if not present

            logging.info(
                f"Recipe search: workflow_id={workflow_id}, query={search_query}, excluded_domains={excluded_domains}, num_urls={num_urls}"
            )

            # Call the search_recipes function from the search_agent module
            recipe_search_results = search_recipes(
                search_query, excluded_domains, num_urls
            )

            # End the timer
            end_time = time.time()
            duration = end_time - start_time

            # Update workflow instance attributes
            workflow_instance["context_data"][
                "recipe_search_results"
            ] = recipe_search_results
            workflow_instance["current_step"] = (
                "recipe_search"  # Mark step as completed
            )
            workflow_instance["status"] = "running"  # Update workflow status
            workflow_instance["last_updated_timestamp"] = (
                datetime.utcnow().isoformat()
            )  # Update timestamp

            logging.info(
                f"Recipe search completed: workflow_id={workflow_id}, found {len(recipe_search_results)} recipes"
            )
            logging.debug(f"Workflow instance after recipe search: {workflow_instance}")

            # Send metrics to the metrics queue
            await self._send_recipe_search_metrics(workflow_id, search_query, duration)

        except Exception as e:
            logging.error(
                f"Error executing recipe search step: workflow_id={workflow_id}: {e}"
            )
            workflow_instance["status"] = "failed"  # Update workflow status
            workflow_instance["last_updated_timestamp"] = (
                datetime.utcnow().isoformat()
            )  # Update timestamp
            logging.info(
                f"Workflow {workflow_id} failed during _execute_recipe_search_step"
            )

    async def _send_recipe_search_metrics(
        self, workflow_id: str, search_query: str, duration: float
    ):
        """Sends recipe search metrics to the metrics queue."""
        try:
            if not self.channel or self.channel.is_closed:
                await self._connect_to_rabbitmq()

            message = {
                "event_type": "recipe_search.duration",
                "duration": duration,
                "metadata": {"search_query": search_query, "workflow_id": workflow_id},
                "timestamp": datetime.utcnow().isoformat(),
            }
            message_json = json.dumps(message)
            channel = await self.connection.channel()
            await channel.basic_publish(
                exchange="",
                routing_key=self.metrics_queue_name,
                body=message_json,
            )
            logging.info(
                f"Sent recipe search metrics to queue {self.metrics_queue_name}: workflow_id={workflow_id}, duration={duration}"
            )
        except Exception as e:
            logging.error(f"Error sending metrics: {e}")

    async def _publish_metrics(self, workflow_id: uuid.UUID, status: str):
        """
        Publishes workflow metrics to the metrics queue.
        """
        metrics_event = {
            "event_type": "workflow.status",  # Required field
            "timestamp": datetime.utcnow().isoformat(),  # Required field
            "metadata": {  # Optional metadata field for additional info
                "workflow_id": str(workflow_id),
                "workflow_type": "recipe_workflow_full",
                "status": status,
                "current_step": status,
                "start_timestamp": self.start_timestamp.isoformat(),
                "last_updated_timestamp": datetime.utcnow().isoformat(),
            },
        }

        await self._publish_to_metrics_queue(json.dumps(metrics_event))
