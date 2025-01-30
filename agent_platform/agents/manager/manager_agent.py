from smolagents import HfApiModel, ManagedAgent
from datetime import datetime, timedelta
import asyncio
from typing import Dict, Optional, Any, Set
from loguru import logger
from queue import Queue
import pika
import json

from queue.setup import AGENT_TASK_QUEUE, AGENT_RESULT_QUEUE
from models.agent_lifecycle import AgentState, AgentHealth
from agents.base.base_agent import BaseAgent
from models.messages import MessageType, AgentMessage, MessageStatus


class ManagerAgent(BaseAgent):
    """Agent manager responsible for lifecycle and health monitoring."""

    HEARTBEAT_INTERVAL = 30  # seconds
    HEALTH_CHECK_INTERVAL = 60  # seconds
    MAX_ERROR_COUNT = 3

    def __init__(self, agent_id: str, base_url: str, model_id: str):
        super().__init__(agent_id, base_url)
        self.model = HfApiModel(model_id)
        self.managed_agents: Dict[str, ManagedAgent] = {}
        self.agent_health: Dict[str, AgentHealth] = {}
        self.agent_capabilities: Dict[str, Set[MessageType]] = (
            {}
        )  # Track what message types each agent can handle
        self.health_check_task = None
        self.task_queue: Dict[str, Queue] = {}  # Task queues by priority
        self.active_tasks: Dict[str, Dict] = {}  # Track tasks by task_id
        self.agent_load: Dict[str, int] = {}  # Track number of active tasks per agent

    async def start(self):
        """Start the manager, health monitoring, and result consumption."""
        # Setup result queue consumer
        self.channel.basic_consume(
            queue=AGENT_RESULT_QUEUE,
            on_message_callback=self._handle_result,
            auto_ack=False,
        )

        # Start health monitoring
        self.health_check_task = asyncio.create_task(self._health_check_loop())

        logger.info(
            "Manager agent started with health monitoring and result consumption"
        )

    def register_agent(self, agent_id: str, capabilities: Set[MessageType]):
        """Register an agent with its message type capabilities"""
        self.agent_capabilities[agent_id] = capabilities
        self.agent_load[agent_id] = 0
        logger.info(f"Registered agent {agent_id} with capabilities: {capabilities}")

    async def deregister_agent(self, agent_id: str) -> bool:
        """Deregister an agent from the manager."""
        try:
            if agent_id in self.managed_agents:
                # Cleanup agent resources
                await self._cleanup_agent(agent_id)
                # Remove from tracking
                del self.managed_agents[agent_id]
                del self.agent_health[agent_id]
                logger.info(f"Successfully deregistered agent {agent_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deregistering agent {agent_id}: {str(e)}")
            return False

    async def _health_check_loop(self):
        """Periodic health check of all managed agents."""
        while True:
            try:
                await self._check_all_agents()
                await asyncio.sleep(self.HEALTH_CHECK_INTERVAL)
            except Exception as e:
                logger.error(f"Error in health check loop: {str(e)}")

    async def _check_all_agents(self):
        """Check health of all managed agents."""
        for agent_id, health in self.agent_health.items():
            try:
                # Check last heartbeat
                if datetime.utcnow() - health.last_heartbeat > timedelta(
                    seconds=self.HEARTBEAT_INTERVAL
                ):
                    await self._handle_agent_timeout(agent_id)

                # Check error count
                if health.error_count >= self.MAX_ERROR_COUNT:
                    await self._handle_agent_failure(agent_id)

            except Exception as e:
                logger.error(f"Error checking agent {agent_id}: {str(e)}")

    async def _handle_agent_timeout(self, agent_id: str):
        """Handle agent timeout by attempting restart."""
        logger.warning(f"Agent {agent_id} timed out")
        health = self.agent_health[agent_id]
        health.state = AgentState.FAILED
        await self._attempt_agent_restart(agent_id)

    async def _handle_agent_failure(self, agent_id: str):
        """Handle agent failure by attempting recovery."""
        logger.error(f"Agent {agent_id} failed")
        health = self.agent_health[agent_id]
        health.state = AgentState.FAILED
        await self._attempt_agent_restart(agent_id)

    async def distribute_task(self, message: AgentMessage) -> str:
        """Distribute a task based on message type and load."""
        try:
            # Validate message payload
            message.validate_payload()

            # Select best agent based on message type and load
            selected_agent = await self._select_agent(message.message_type)
            if not selected_agent:
                raise ValueError(
                    f"No suitable agent available for {message.message_type}"
                )

            # Update tracking
            self.active_tasks[message.message_id] = {
                "agent_id": selected_agent,
                "status": "assigned",
                "started_at": datetime.utcnow(),
                "message": message,
            }
            self.agent_load[selected_agent] = self.agent_load.get(selected_agent, 0) + 1

            # Send task to agent
            await self._send_task_to_agent(selected_agent, message)

            return message.message_id

        except Exception as e:
            logger.error(f"Failed to distribute task {message.message_id}: {str(e)}")
            raise

    async def _select_agent(self, message_type: MessageType) -> Optional[str]:
        """Select the most suitable agent based on message type and load."""
        # Filter agents that can handle this message type and are active
        capable_agents = [
            agent_id
            for agent_id, health in self.agent_health.items()
            if (
                health.state == AgentState.ACTIVE
                and message_type in self.agent_capabilities.get(agent_id, set())
            )
        ]

        if not capable_agents:
            logger.warning(f"No capable agents found for message type: {message_type}")
            return None

        # Among capable agents, find the one with lowest load
        return min(capable_agents, key=lambda x: self.agent_load.get(x, 0))

    async def update_task_status(self, task_id: str, status: str, result: Dict = None):
        """Update status of a task and handle completion."""
        if task_id not in self.active_tasks:
            logger.warning(f"Unknown task {task_id}")
            return

        task_info = self.active_tasks[task_id]
        task_info["status"] = status
        task_info["result"] = result

        if status in ["completed", "failed"]:
            # Update agent load
            agent_id = task_info["agent_id"]
            self.agent_load[agent_id] = max(0, self.agent_load.get(agent_id, 1) - 1)

            # Clean up task tracking
            if status == "completed":
                del self.active_tasks[task_id]

    async def get_task_status(self, task_id: str) -> Dict:
        """Get current status of a task."""
        return self.active_tasks.get(task_id, {"status": "unknown"})

    async def _send_task_to_agent(self, agent_id: str, message: AgentMessage):
        """Send task to specific agent via RabbitMQ task queue."""
        try:
            # Update message with target agent
            message.agent_id = agent_id
            message.status = MessageStatus.PENDING

            # Publish to task queue
            self.channel.basic_publish(
                exchange="",
                routing_key=AGENT_TASK_QUEUE,
                body=message.model_dump_json(),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type="application/json",
                    headers={
                        "target_agent": agent_id,
                        "message_type": message.message_type,
                    },
                ),
            )

            logger.info(f"Task {message.message_id} sent to agent {agent_id}")

        except Exception as e:
            logger.error(f"Failed to send task to agent {agent_id}: {str(e)}")
            # Update task tracking
            if message.message_id in self.active_tasks:
                self.active_tasks[message.message_id]["status"] = "failed"
                self.agent_load[agent_id] = max(0, self.agent_load.get(agent_id, 1) - 1)
            raise

    async def _handle_result(self, ch, method, properties, body):
        """Handle results from agents."""
        try:
            message_data = json.loads(body)
            message = AgentMessage(**message_data)

            # Update task status and store result
            await self.update_task_status(
                message.message_id, status="completed", result=message.payload
            )

            # Acknowledge message
            ch.basic_ack(delivery_tag=method.delivery_tag)

            logger.info(f"Processed result for task {message.message_id}")

        except Exception as e:
            logger.error(f"Error processing result: {str(e)}")
            # Negative ack in case of processing error
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
