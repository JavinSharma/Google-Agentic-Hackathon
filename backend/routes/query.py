from fastapi import APIRouter, HTTPException

from agent.agent import run_agent
from backend.models import ChatRequest, ChatResponse

router = APIRouter(prefix="/api", tags=["query"])


@router.post("/query", response_model=ChatResponse)
async def query(req: ChatRequest) -> ChatResponse:
    try:
        final_text, thought_trace = await run_agent(req.user_id, req.message, req.session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return ChatResponse(response=final_text, thought_trace=thought_trace)
