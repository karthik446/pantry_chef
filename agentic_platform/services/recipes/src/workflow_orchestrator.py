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
from typing import Dict, Any, List, Tuple
from api_client import PantryChefAPIClient
from models import Recipe
from event_models import MetricsEvent

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

    async def _publish_metrics(
        self, event_type: str, metadata: dict, workflow_instance: dict | None = None
    ):
        """
        Publishes metrics to the metrics queue.
        """
        try:
            if isinstance(workflow_instance, dict):  # Check if it's actually a dict
                workflow_name = workflow_instance.get("workflow_type", "unknown")
                message = {
                    "event_type": f"{workflow_name}.status",
                    "timestamp": datetime.utcnow().isoformat(),
                    "metadata": {
                        "workflow_id": str(workflow_instance.get("workflow_id")),
                        "workflow_type": workflow_instance.get("workflow_type"),
                        "status": workflow_instance.get("status"),
                        "current_step": workflow_instance.get("current_step"),
                        "start_timestamp": workflow_instance.get("start_timestamp"),
                        "last_updated_timestamp": workflow_instance.get(
                            "last_updated_timestamp"
                        ),
                    },
                }
            else:
                # Ensure all values in metadata are JSON serializable
                sanitized_metadata = {}
                for key, value in metadata.items():
                    if (
                        hasattr(value, "__class__")
                        and value.__class__.__name__ == "HttpUrl"
                    ):
                        sanitized_metadata[key] = str(value)
                    else:
                        sanitized_metadata[key] = value

                message = {
                    "event_type": event_type,
                    "timestamp": datetime.utcnow().isoformat(),
                    "metadata": sanitized_metadata,
                }

            message_json = json.dumps(message)
            await self._publish_to_metrics_queue(message_json)
        except Exception as e:
            logging.error(f"Error publishing metrics: {e}", exc_info=True)

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
        start_time = time.time()
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
            recipe_urls, search_metrics = search_recipes(
                search_query=search_query,
                excluded_domains=excluded_domains,
                num_urls=number_of_urls,
            )
            workflow_instance["context_data"]["recipe_search_results"] = recipe_urls
            workflow_instance["current_step"] = "recipe_search"
            workflow_instance["status"] = "recipe_search_completed"
            workflow_instance["last_updated_timestamp"] = datetime.now().isoformat()

            # Publish search metrics
            await self._publish_metrics(
                "recipe.search_completed",
                {
                    "recipe_urls": recipe_urls,
                    "duration": search_metrics.duration,
                    "attempts": search_metrics.metadata.get("attempts", 1),
                },
                workflow_instance,
            )
            logging.info(
                f"Recipe search completed: workflow_id={workflow_id}, found {len(recipe_urls)} recipes"
            )

            # Step 2: Recipe Scraping
            workflow_instance["current_step"] = "recipe_scraping"
            workflow_instance["status"] = "recipe_scraping_in_progress"
            workflow_instance["last_updated_timestamp"] = datetime.now().isoformat()
            await self._publish_metrics(
                "recipe.scraping_started", {}, workflow_instance
            )
            logging.info(
                f"Starting parallel recipe scraping: workflow_id={workflow_id}"
            )

            scraped_recipes = await self.scraperStep.scrape_recipes(recipe_urls)
            workflow_instance["context_data"]["scraped_recipes"] = scraped_recipes
            workflow_instance["status"] = "recipe_scraping_completed"
            workflow_instance["last_updated_timestamp"] = datetime.now().isoformat()
            await self._publish_metrics(
                "recipe.scraping_completed",
                {"scraped_recipes": len(scraped_recipes)},
                workflow_instance,
            )

            # Step 3: Save Recipes to API
            workflow_instance["current_step"] = "save_recipes_api"
            workflow_instance["status"] = "save_recipes_api_pending"
            workflow_instance["last_updated_timestamp"] = datetime.now().isoformat()
            await self.save_recipes(
                scraped_recipes=scraped_recipes,
                workflow_id=workflow_id,
                search_query=search_query,
            )

            # Workflow Completion
            workflow_instance["status"] = "completed"
            workflow_instance["current_step"] = "completed"
            workflow_instance["last_updated_timestamp"] = datetime.now().isoformat()
            end_time = time.time()
            execution_time = end_time - start_time
            await self._publish_metrics(
                "workflow.completed",
                {"workflow_id": str(workflow_id), "execution_time": execution_time},
                workflow_instance,
            )

            logging.info(
                f"Workflow '{workflow_type}' completed: workflow_id={workflow_id}"
            )

        except Exception as e:
            workflow_instance["status"] = "failed"
            workflow_instance["current_step"] = "failed"
            workflow_instance["last_updated_timestamp"] = datetime.now().isoformat()
            workflow_instance["error_details"] = str(e)
            await self._publish_metrics(
                "workflow.failed", {"error": str(e)}, workflow_instance
            )
            logging.error(f"Error executing workflow {workflow_id}: {e}", exc_info=True)

    async def save_recipes(
        self,
        scraped_recipes: List[Tuple[Recipe | None, List[MetricsEvent]]],
        workflow_id: uuid.UUID,
        search_query: str,
    ) -> None:
        """
        Save successfully scraped recipes to database through API

        Args:
            scraped_recipes: List of tuples containing (Recipe | None, List[MetricsEvent])
                            where Recipe is None if scraping failed
        """
        try:
            api_client = PantryChefAPIClient()

            for recipe, metrics in scraped_recipes:
                if recipe is None:
                    # Skip failed recipes but log the failure
                    logging.warning(
                        f"Skipping failed recipe: {metrics[0].metadata.get('url', 'Unknown URL')}"
                    )
                    continue

                try:
                    # Use model_dump() instead of model_dump_json() to get dict
                    recipe_dict = recipe.model_dump()
                    recipe_dict["created_from_query"] = search_query
                    saved_recipe = api_client.create_recipe(recipe_dict)

                    await self._publish_metrics(
                        "recipe.saved",
                        {
                            "recipe_id": saved_recipe.get("id"),
                            "workflow_id": str(workflow_id),
                            "url": recipe.source_url,
                        },
                        None,
                    )

                except Exception as e:
                    logging.error(
                        f"Failed to save recipe from {recipe.source_url}: {e}"
                    )
                    await self._publish_metrics(
                        "recipe.save_failed",
                        {
                            "error": str(e),
                            "workflow_id": str(workflow_id),
                            "url": recipe.source_url,
                        },
                        None,
                    )
                    # Continue with next recipe instead of failing entire batch
                    continue

        except Exception as e:
            logging.error(f"Fatal error in save_recipe: {e}")
            await self._publish_metrics(
                "recipe.save_batch_failed",
                {"error": str(e), "workflow_id": str(workflow_id)},
                None,
            )
            raise
