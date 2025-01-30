from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime
import uuid


class MessageType(str, Enum):
    RECIPE_SEARCH = "recipe.search"
    RECIPE_PARSE = "recipe.parse"
    RESEARCH = "research"
    # Add more message types as needed


class MessageStatus(str, Enum):
    """Status of a message in the system."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class ErrorDetail(BaseModel):
    """Detailed error information."""

    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    retry_count: Optional[int] = 0


class RecipeSearchPayload(BaseModel):
    search_query: str = Field(..., description="Search query for recipe")
    cuisine_type: Optional[str] = Field(None, description="Type of cuisine")
    dietary_restrictions: Optional[list[str]] = Field(default_factory=list)


class RecipeParsePayload(BaseModel):
    recipe_url: str = Field(..., description="URL of the recipe to parse")
    include_nutrition: bool = Field(default=False)


class ResearchPayload(BaseModel):
    topic: str = Field(..., description="Research topic")
    depth: Optional[str] = Field(default="medium", enum=["shallow", "medium", "deep"])


# Map message types to their payload models
MESSAGE_PAYLOAD_MODELS = {
    MessageType.RECIPE_SEARCH: RecipeSearchPayload,
    MessageType.RECIPE_PARSE: RecipeParsePayload,
    MessageType.RESEARCH: ResearchPayload,
}


class AgentMessage(BaseModel):
    """Standard message format for agent communication."""

    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: Optional[str] = None
    message_type: MessageType
    status: MessageStatus = Field(default=MessageStatus.PENDING)
    payload: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    error: Optional[ErrorDetail] = None
    retry_count: int = 0
    max_retries: int = 3
    parent_message_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator("updated_at", always=True)
    def update_timestamp(cls, v, values):
        """Always update the updated_at timestamp."""
        return datetime.utcnow()

    def add_error(self, code: str, message: str, details: Optional[Dict] = None):
        """Add error information to the message."""
        self.error = ErrorDetail(code=code, message=message, details=details)
        self.status = MessageStatus.FAILED

    def validate_payload(self):
        """Validate payload against the expected model for the message type"""
        payload_model = MESSAGE_PAYLOAD_MODELS.get(self.message_type)
        if payload_model:
            # Validate and convert payload
            validated_payload = payload_model(**self.payload)
            self.payload = validated_payload.model_dump()
