from fastapi import APIRouter, HTTPException
from backend.models import EventPayload, EventResponse
from elastic.client import ingest_event

router = APIRouter(prefix="/api", tags=["events"])


@router.post("/events", response_model=EventResponse)
async def log_event(event: EventPayload) -> EventResponse:
    try:
        event_dict = event.model_dump()
        response = await ingest_event(event_dict)
        
        return EventResponse(
            success=True,
            event_id=response["_id"],
            message="Event logged"
        )
    except Exception as e:
        return EventResponse(
            success=False,
            event_id="",
            message=str(e)
        )
