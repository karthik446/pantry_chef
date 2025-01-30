from enum import Enum
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any


class AgentState(str, Enum):
    INITIALIZING = "initializing"
    ACTIVE = "active"
    IDLE = "idle"
    BUSY = "busy"
    FAILED = "failed"
    TERMINATED = "terminated"


class AgentHealth(BaseModel):
    last_heartbeat: datetime
    state: AgentState
    error_count: int = 0
    performance_metrics: Dict[str, float] = {}
    resource_usage: Dict[str, float] = {}
