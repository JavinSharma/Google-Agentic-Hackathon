# Slice 1 Handoff — Activity Tracker

## What's Been Built
A complete data collection pipeline that captures user behavioral events from the frontend, validates them through the backend, and stores them in Elasticsearch. This is the foundation layer — every other slice depends on the data this slice produces.

---

## Infrastructure
| Item | Value |
|---|---|
| Elasticsearch | Elastic Cloud, GCP us-central1 |
| Index | `behavioral_events` |
| Backend | FastAPI on `http://localhost:8000` |
| Status | ✅ Live and verified |

---

## Files Completed

### `elastic/mappings/behavioral_events.json`
Index mapping schema defining the shape of every behavioral event stored in Elasticsearch.

Fields:
| Field | Type | Notes |
|---|---|---|
| `user_id` | keyword | Exact match, not analyzed |
| `timestamp` | date | ISO 8601, auto-added if missing |
| `action_type` | keyword | One of: `search`, `view`, `dismiss` |
| `topic` | text + keyword | Full-text and exact search |
| `session_id` | keyword | Defaults to `"default"` |
| `metadata` | object | Dynamic, accepts any extra fields |

---

### `elastic/client.py`
AsyncElasticsearch singleton. Loads credentials from `.env`. Two public functions:

```python
get_client()           # Returns the shared AsyncElasticsearch connection
ingest_event(event_dict: dict)  # Writes document to behavioral_events index
                                # Auto-adds timestamp if not present
                                # Returns the Elasticsearch response
```

**Person B — add your read methods below the existing code in this file. Use `get_client()` for the connection, do not create a new one.**

---

### `backend/models.py`
Pydantic v2 models for API validation.

```python
class EventPayload(BaseModel):
    user_id: str
    action_type: Literal["search", "view", "dismiss"]
    topic: str
    session_id: str = "default"
    metadata: dict = {}

class EventResponse(BaseModel):
    success: bool
    event_id: str
    message: str
```

---

### `backend/routes/events.py`
FastAPI router with one endpoint:

```
POST /api/events
Body:     EventPayload
Returns:  EventResponse
```

Calls `ingest_event()` internally. Returns `success: false` with error message if Elasticsearch is unreachable.

---

### `agent/tools/log_action.py`
ADK tool function that exposes event ingestion to Gemini.

```python
async def log_user_action(
    user_id: str,
    action_type: str,   # "search" | "view" | "dismiss"
    topic: str,
    session_id: str = "default"
) -> str
```

**Person C — import and register like this:**
```python
from agent.tools.log_action import log_user_action
root_agent = LlmAgent(tools=[log_user_action, ...])
```

---

### `frontend/app.py` (Slice 1 section)
Activity Simulator UI — three buttons that fire real events to the backend for demo purposes.

| Button | action_type | topic |
|---|---|---|
| Read ML Article | `view` | `machine learning` |
| Search Quantum Computing | `search` | `quantum computing` |
| Dismiss Finance News | `dismiss` | `finance` |

Uses `httpx.AsyncClient` to call `POST /api/events`. Shows `st.success` or `st.error` on response.

---

## Verified Working

```
POST http://localhost:8000/api/events
Content-Type: application/json

{
  "user_id": "user_001",
  "action_type": "view",
  "topic": "machine learning"
}

Response:
{
  "success": true,
  "event_id": "9l-psJ4BQWAsdlx8UbRS",
  "message": "Event logged"
}
```

Document confirmed in Kibana under `behavioral_events` index with all fields populated.

---

## Environment Variables
> Share over WhatsApp/Discord only. Never commit `.env` to GitHub.

```env
ELASTIC_URL=https://1054f03f67cb4c18aee6c4d9afbc0e65.us-central1.gcp.cloud.es.io:443
ELASTIC_API_KEY=WUY4aHJaNEJRV0FzZGx4OHFLVUo6VUJ4VTltX3dSdEwxRjJjS3N4a0E4QQ==
ELASTIC_CLOUD_ID=2a156ac56e254d0ca0d7b97c9346c96f:dXMtY2VudHJhbDEuZ2NwLmNsb3VkLmVzLmlvOjQ0MyQxMDU0ZjAzZjY3Y2I0YzE4YWVlNmM0ZDlhZmJjMGU2NSRhMTFlMGZlYzI0NDA0N2VmYThlM2YyMTExNjdkYjM5OQ==
BACKEND_URL=http://localhost:8000
```

---

## How to Run
Always from project root `hyper-context-engine/`:

```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

---

## Notes for Each Teammate

### Person B — Context Engine
- Query the `behavioral_events` index using `get_client()` from `elastic/client.py`
- Fields available to filter/search: `user_id`, `action_type`, `topic`, `timestamp`, `session_id`
- Add your read functions (`fetch_events`, etc.) directly below the existing code in `client.py`
- Do not create a new Elasticsearch client — reuse `get_client()`

### Person C — Conversational Core
- Import `log_user_action` from `agent/tools/log_action.py`
- Pass it into `LlmAgent(tools=[log_user_action, ...])`
- The function docstring is already written for ADK tool selection
- `backend/main.py` already has CORS and the events router — just add your query router

### Person D — Infra
- `behavioral_events` index already exists in Elastic Cloud — do not recreate it in `setup_indices.py`
- All `__init__.py` files exist and are clean
- Always run uvicorn from project root: `uvicorn backend.main:app --reload`
- `backend/main.py` is complete — just add Person C's query router when ready

---

## What's NOT Done (Other Slices)
- `backend/routes/query.py` — Person C
- `agent/agent.py` and `agent/prompts.py` — Person C
- `elastic/client.py` read methods — Person B
- `agent/tools/fetch_context.py` — Person B
- `agent/tools/update_profile.py` — Person B
- `frontend/app.py` chat UI, sidebar, Thought Trace panel — Persons A/B/C/D
- `elastic/mappings/user_profiles.json` — Person B
- `deploy/Dockerfile` and `cloud_run_deploy.sh` — Person D
