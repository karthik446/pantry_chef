import pytest
import json
from unittest.mock import patch, MagicMock
from src import workflow_consumer
import pika


@pytest.fixture(autouse=True)
def reset_workflow_initiate_schema():
    """Fixture to reset workflow_initiate_schema before each test."""
    workflow_consumer.workflow_initiate_schema = None


@patch("src.workflow_consumer.search_recipes")
@patch("pika.BlockingConnection")
@patch("src.workflow_consumer.load_workflow_initiate_schema")
def test_process_workflow_command_valid(
    mock_load_workflow_initiate_schema, mock_blocking_connection, mock_search_recipes
):
    """Test processing a valid workflow command."""
    # Mock the load_workflow_initiate_schema function to return a sample schema
    mock_load_workflow_initiate_schema.return_value = {
        "type": "object",
        "properties": {
            "workflow_type": {"type": "string"},
            "workflow_payload": {"type": "object"},
        },
        "required": ["workflow_type", "workflow_payload"],
    }

    # Mock the search_recipes function to return a sample list of URLs
    mock_search_recipes.return_value = [
        "http://example.com/recipe1",
        "http://example.com/recipe2",
    ]

    # Sample valid workflow command
    body = json.dumps(
        {
            "workflow_type": "recipe_workflow_full",
            "workflow_payload": {
                "search_query": "chocolate cake",
                "excluded_domains": ["example.com"],
                "number_of_urls": 2,
            },
        }
    ).encode("utf-8")

    # Mock pika objects
    mock_channel = MagicMock()
    mock_connection = MagicMock()
    mock_connection.channel.return_value = mock_channel
    mock_blocking_connection.return_value = mock_connection
    method = pika.spec.Basic.Deliver(delivery_tag=1)  # Mock method
    properties = pika.spec.BasicProperties()  # Mock properties

    # Call the process_workflow_command function
    workflow_consumer.process_workflow_command(mock_channel, method, properties, body)

    # Assert that search_recipes was called with the correct arguments
    mock_search_recipes.assert_called_once_with("chocolate cake", ["example.com"], 2)

    # Assert that the message was acknowledged
    mock_channel.basic_ack.assert_called_once_with(delivery_tag=1)


@patch("pika.BlockingConnection")
@patch("src.workflow_consumer.search_recipes")
def test_process_workflow_command_invalid_json(
    mock_search_recipes, mock_blocking_connection
):
    """Test processing an invalid workflow command (invalid JSON)."""
    # Invalid JSON body
    body = "invalid json".encode("utf-8")

    # Mock pika objects
    mock_channel = MagicMock()
    mock_connection = MagicMock()
    mock_connection.channel.return_value = mock_channel
    mock_blocking_connection.return_value = mock_connection
    method = pika.spec.Basic.Deliver(delivery_tag=1)  # Mock method
    properties = pika.spec.BasicProperties()  # Mock properties

    # Call the process_workflow_command function
    workflow_consumer.process_workflow_command(mock_channel, method, properties, body)

    # Assert that search_recipes was not called
    mock_search_recipes.assert_not_called()

    # Assert that the message was rejected
    mock_channel.basic_nack.assert_called_once_with(delivery_tag=1, requeue=False)
