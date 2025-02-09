import pika
import os
import json
import logging
import jsonschema  # Import jsonschema library
from jsonschema import validate  # Import the validate function
from jsonschema.exceptions import ValidationError  # Import ValidationError exception
import uuid  # Import the UUID module
from datetime import datetime  # Import datetime for timestamping
from search_agent import search_recipes  # Import the search_recipes function

# Configure logging

SCHEMA_PATH = "/app/src/schema.json"


# Load the workflow_initiate schema from file
def load_workflow_initiate_schema(
    schema_path=SCHEMA_PATH,
):
    """Loads the workflow_initiate JSON schema from a JSON file."""
    try:
        with open(schema_path, "r") as f:
            schema = json.load(f)
        return schema
    except FileNotFoundError:
        logging.error(f"Schema file not found: {schema_path}")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON schema: {e}")
        return None
    except Exception as e:
        logging.error(f"Error loading schema: {e}")
        return None


workflow_initiate_schema = load_workflow_initiate_schema()

# In-memory workflow instance storage (for MVP)
workflow_instances = {}


def _execute_recipe_search_step(workflow_instance: dict) -> None:
    """
    Executes the recipe search step for the given workflow instance.

    Args:
        workflow_instance: The workflow instance dictionary.
    """
    try:
        search_query = workflow_instance["workflow_payload"]["search_query"]
        excluded_domains = workflow_instance["workflow_payload"].get(
            "excluded_domains", []
        )  # Get excluded_domains, default to [] if not present
        num_urls = workflow_instance["workflow_payload"].get(
            "number_of_urls", 10
        )  # Get number_of_urls, default to 10 if not present

        logging.info(
            f"Executing recipe search step for workflow: {workflow_instance['workflow_id']}, query: {search_query}, excluded_domains: {excluded_domains}, num_urls: {num_urls}"
        )

        # Call the search_recipes function from the search_agent module
        recipe_search_results = search_recipes(search_query, excluded_domains, num_urls)

        # Update workflow instance attributes
        workflow_instance["context_data"][
            "recipe_search_results"
        ] = recipe_search_results
        workflow_instance["current_step"] = "recipe_search"  # Mark step as completed
        workflow_instance["status"] = "running"  # Update workflow status
        workflow_instance["last_updated_timestamp"] = (
            datetime.utcnow().isoformat()
        )  # Update timestamp

        logging.info(
            f"Recipe search step completed for workflow: {workflow_instance['workflow_id']}, found {len(recipe_search_results)} recipes"
        )
        logging.debug(f"Workflow instance after recipe search: {workflow_instance}")

    except Exception as e:
        logging.error(
            f"Error executing recipe search step for workflow: {workflow_instance['workflow_id']}: {e}"
        )
        workflow_instance["status"] = "failed"  # Update workflow status
        workflow_instance["last_updated_timestamp"] = (
            datetime.utcnow().isoformat()
        )  # Update timestamp


def process_recipe_workflow_full(workflow_instance: dict) -> None:
    """
    Processes the 'recipe_workflow_full' workflow.

    Args:
        workflow_instance: The workflow instance dictionary.
    """
    try:
        logging.info(
            f"Processing 'recipe_workflow_full' workflow: {workflow_instance['workflow_id']}"
        )

        # Execute the recipe search step
        _execute_recipe_search_step(workflow_instance)

        # Add more steps here as needed for the full recipe workflow

        workflow_instance["status"] = "completed"  # Update workflow status
        workflow_instance["last_updated_timestamp"] = (
            datetime.utcnow().isoformat()
        )  # Update timestamp
        logging.info(
            f"Workflow 'recipe_workflow_full' completed: {workflow_instance['workflow_id']}"
        )
        logging.debug(f"Workflow instance after completion: {workflow_instance}")

    except Exception as e:
        logging.error(
            f"Error processing 'recipe_workflow_full' workflow: {workflow_instance['workflow_id']}: {e}"
        )
        workflow_instance["status"] = "failed"  # Update workflow status
        workflow_instance["last_updated_timestamp"] = (
            datetime.utcnow().isoformat()
        )  # Update timestamp


def process_workflow_command(channel, method, properties, body):
    """
    Callback function to process messages from the workflow_commands queue.
    """
    try:
        command = json.loads(body.decode("utf-8"))
        logging.info(f"Received workflow command: {command}")

        # Validate the message against the schema
        if workflow_initiate_schema:
            try:
                validate(
                    instance=command, schema=workflow_initiate_schema
                )  # Validate the command against the schema
                logging.info("Workflow command validated successfully.")

                # Workflow instance creation logic (Task 1.4)
                workflow_id = str(uuid.uuid4())  # Generate workflow_id (UUID)
                workflow_type = command["workflow_type"]
                workflow_payload = command["workflow_payload"]

                # Create workflow instance object (Python dictionary)
                workflow_instance = {
                    "workflow_id": workflow_id,
                    "workflow_type": workflow_type,
                    "workflow_payload": workflow_payload,
                    "status": "pending",  # Initial status
                    "current_step": None,  # No step started yet
                    "context_data": {},  # Store intermediate results
                }

                # Store workflow instance in in-memory dictionary
                workflow_instances[workflow_id] = workflow_instance

                logging.info(
                    f"Workflow initiated: {workflow_id}, type: {workflow_type}"
                )
                logging.debug(f"Workflow instance: {workflow_instance}")

                # Process the workflow based on its type
                if workflow_type == "recipe_workflow_full":
                    process_recipe_workflow_full(workflow_instance)
                else:
                    logging.warning(f"Unknown workflow type: {workflow_type}")
                    workflow_instance["status"] = "failed"
                    workflow_instance["last_updated_timestamp"] = (
                        datetime.utcnow().isoformat()
                    )

                channel.basic_ack(
                    delivery_tag=method.delivery_tag
                )  # Acknowledge if validation and processing are successful
                logging.info(f"Acknowledged message: {method.delivery_tag}")
            except ValidationError as e:
                logging.error(f"Workflow command validation error: {e}")
                channel.basic_nack(
                    delivery_tag=method.delivery_tag, requeue=False
                )  # Reject and don't requeue invalid messages
        else:
            logging.error(
                "Workflow initiate schema not loaded. Cannot validate message."
            )
            channel.basic_nack(
                delivery_tag=method.delivery_tag, requeue=False
            )  # Reject if schema is not loaded

    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON: {e}")
        channel.basic_nack(
            delivery_tag=method.delivery_tag, requeue=False
        )  # Reject and don't requeue invalid JSON
    except Exception as e:
        logging.error(f"Error processing message: {e}")
        channel.basic_nack(
            delivery_tag=method.delivery_tag, requeue=True
        )  # Reject and requeue other errors


def start_workflow_command_consumer():
    """
    Starts the RabbitMQ consumer for the workflow_commands queue.
    """
    rabbitmq_host = os.environ.get(
        "RABBITMQ_HOST", "localhost"
    )  # Default to localhost for local testing
    rabbitmq_port = int(os.environ.get("RABBITMQ_PORT", 5672))  # Default RabbitMQ port
    rabbitmq_user = os.environ.get("RABBITMQ_USER", "guest")  # Default RabbitMQ user
    rabbitmq_password = os.environ.get(
        "RABBITMQ_PASSWORD", "guest"
    )  # Default RabbitMQ password
    workflow_commands_queue_name = os.environ.get(
        "WORKFLOW_COMMANDS_QUEUE_NAME", "recipe_searches"
    )  # Queue name

    credentials = pika.PlainCredentials(rabbitmq_user, rabbitmq_password)
    parameters = pika.ConnectionParameters(
        host=rabbitmq_host, port=rabbitmq_port, credentials=credentials
    )

    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()

    # Declare the recipe_searches
    exchange_name = "recipe_searches"
    channel.exchange_declare(
        exchange=exchange_name, exchange_type="direct", durable=True
    )

    # channel.queue_declare(
    #     queue=workflow_commands_queue_name,
    #     durable=True,
    # )  # Declare the queue

    channel.basic_qos(prefetch_count=1)  # Process one message at a time
    channel.basic_consume(
        queue=workflow_commands_queue_name, on_message_callback=process_workflow_command
    )

    logging.info(
        f" [*] Waiting for messages from {workflow_commands_queue_name} queue. To exit, press CTRL+C"
    )
    channel.start_consuming()


if __name__ == "__main__":
    # Simplified local testing (temporary)
    sample_message = {
        "workflow_type": "recipe_workflow_full",
        "workflow_payload": {"search_query": "pasta"},
    }
    print("testing")

    # Manually call process_workflow_command with a dummy channel and method
    class DummyChannel:
        def basic_ack(self, delivery_tag):
            print(f"  [DummyChannel] Acknowledged message: {delivery_tag}")

        def basic_nack(self, delivery_tag, requeue):
            print(
                f"  [DummyChannel] Nacked message: {delivery_tag}, requeue: {requeue}"
            )

    class DummyMethod:
        def __init__(self, delivery_tag):
            self.delivery_tag = delivery_tag

    dummy_channel = DummyChannel()
    dummy_method = DummyMethod(delivery_tag=1)
    process_workflow_command(
        dummy_channel, dummy_method, None, json.dumps(sample_message).encode("utf-8")
    )

    print("Workflow Instances:", workflow_instances)
