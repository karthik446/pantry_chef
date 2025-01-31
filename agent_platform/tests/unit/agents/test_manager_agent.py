import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from agents.manager_agent import ManagerAgent
from models.messages import MessageType, AgentMessage, MessageStatus
from models.agent_lifecycle import AgentState, AgentHealth


@pytest.fixture
def manager_config():
    return {
        "agent_id": "test-manager",
        "base_url": "http://test-url",
        "model_id": "test-model",
    }


@pytest.fixture
def manager_agent(mocker, manager_config):
    # Mock pika connection
    mocker.patch("agents.base_agent.pika")

    # Mock AuthService
    mock_auth = mocker.patch("agents.base_agent.AuthService")

    mock_auth.return_value.initialize_auth.return_value = True
    mock_auth.return_value.get_headers.return_value = {"Authorization": "test-token"}

    # Create a concrete implementation of ManagerAgent for testing
    class TestManagerAgent(ManagerAgent):
        async def process_message(self, message):
            return None  # Minimal implementation for testing

    return TestManagerAgent(**manager_config)


def test_manager_agent_initialization(manager_agent, manager_config):
    """Test basic initialization of ManagerAgent."""
    assert manager_agent.agent_id == manager_config["agent_id"]
    assert isinstance(manager_agent.managed_agents, dict)
    assert isinstance(manager_agent.agent_health, dict)
    assert isinstance(manager_agent.agent_capabilities, dict)


def test_register_agent(manager_agent):
    """Test agent registration with capabilities."""
    agent_id = "test-agent-1"
    capabilities = {MessageType.RECIPE_SEARCH}

    manager_agent.register_agent(agent_id, capabilities)

    assert agent_id in manager_agent.agent_capabilities
    assert manager_agent.agent_capabilities[agent_id] == capabilities
    assert manager_agent.agent_load[agent_id] == 0


@pytest.mark.asyncio
async def test_select_agent_with_no_agents(manager_agent):
    """Test agent selection when no agents are available."""
    result = await manager_agent._select_agent(MessageType.RECIPE_SEARCH)
    assert result is None


@pytest.mark.asyncio
async def test_select_agent_with_single_agent(manager_agent):
    """Test agent selection with one available agent."""
    # Register an agent
    agent_id = "test-agent-1"
    capabilities = {MessageType.RECIPE_SEARCH}
    manager_agent.register_agent(agent_id, capabilities)

    # Set agent as active
    manager_agent.agent_health[agent_id] = AgentHealth(
        state=AgentState.ACTIVE, last_heartbeat=datetime.utcnow()
    )

    # Test selection
    selected = await manager_agent._select_agent(MessageType.RECIPE_SEARCH)
    assert selected == agent_id
