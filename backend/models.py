from pydantic import BaseModel, Field
from typing import Literal, Optional


class EventPayload(BaseModel):
    user_id: str
    action_type: Literal["search", "view", "dismiss"]
    topic: str
    session_id: str = "default"
    metadata: dict = Field(default_factory=dict)


class EventResponse(BaseModel):
    success: bool
    event_id: str
    message: str
