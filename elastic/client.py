import os
import json
from datetime import datetime, timezone
from typing import Any
from dotenv import load_dotenv
from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import NotFoundError

load_dotenv()

_client: AsyncElasticsearch | None = None
_user_profiles_initialized: bool = False


async def get_client() -> AsyncElasticsearch:
    global _client
    if _client is None:
        elastic_url = os.getenv("ELASTIC_URL")
        elastic_api_key = os.getenv("ELASTIC_API_KEY")

        if not elastic_url:
            raise ValueError("ELASTIC_URL environment variable is not set")

        try:
            _client = AsyncElasticsearch(
                elastic_url,
                api_key=elastic_api_key,
                request_timeout=30
            )
        except Exception as e:
            print(f"Error connecting to Elasticsearch: {e}")
            raise

    return _client


async def ingest_event(event_dict: dict) -> Any:
    try:
        client = await get_client()

        if "timestamp" not in event_dict:
            event_dict["timestamp"] = datetime.now(timezone.utc).isoformat()

        response = await client.index(
            index="behavioral_events",
            document=event_dict
        )

        return response
    except Exception as e:
        print(f"Error ingesting event: {e}")
        raise


# ---------------------------------------------------------------------------
# Person B — Context Engine Read Methods
# ---------------------------------------------------------------------------

async def _ensure_user_profiles_index() -> None:
    """
    Lazy initialiser: checks whether the 'user_profiles' index exists in
    Elasticsearch and creates it from the JSON mapping schema if it does not.
    Runs at most once per process lifetime.
    """
    global _user_profiles_initialized
    if _user_profiles_initialized:
        return

    client = await get_client()
    try:
        exists = await client.indices.exists(index="user_profiles")
        if not exists:
            mapping_path = os.path.join(
                os.path.dirname(__file__), "mappings", "user_profiles.json"
            )
            if os.path.exists(mapping_path):
                with open(mapping_path, "r", encoding="utf-8") as f:
                    mapping_body = json.load(f)
                await client.indices.create(index="user_profiles", body=mapping_body)
                print("[elastic/client] Created 'user_profiles' index from schema file.")
            else:
                # Fallback: create with dynamic mappings if schema file is missing
                await client.indices.create(index="user_profiles")
                print(
                    "[elastic/client] WARNING: Schema file not found. "
                    "Created 'user_profiles' with dynamic mappings."
                )
        _user_profiles_initialized = True
    except Exception as e:
        print(f"[elastic/client] Error during user_profiles index initialisation: {e}")
        raise


async def fetch_recent_events(user_id: str, limit: int = 15) -> list[dict]:
    """
    Fetches the most recent `limit` behavioral events for `user_id` from the
    'behavioral_events' index, ordered newest-first.

    Args:
        user_id: The unique identifier for the user.
        limit:   Maximum number of events to return (default 15).

    Returns:
        A list of event source dicts, e.g.
        [{"user_id": "user_001", "action_type": "view", "topic": "ML", ...}, ...]
    """
    client = await get_client()
    try:
        response = await client.search(
            index="behavioral_events",
            query={
                "bool": {
                    "must": [{"term": {"user_id": user_id}}]
                }
            },
            sort=[{"timestamp": {"order": "desc"}}],
            size=limit,
        )
        hits = response.get("hits", {}).get("hits", [])
        return [hit["_source"] for hit in hits]
    except Exception as e:
        print(f"[elastic/client] Error fetching recent events for '{user_id}': {e}")
        return []


async def fetch_user_profile(user_id: str) -> dict | None:
    """
    Retrieves the synthesised persona profile for `user_id` from the
    'user_profiles' index.  Returns None if no document exists yet.

    Args:
        user_id: The unique identifier for the user (used as the document ID).

    Returns:
        The profile source dict, or None if not found.
    """
    await _ensure_user_profiles_index()
    client = await get_client()
    try:
        response = await client.get(index="user_profiles", id=user_id)
        return response["_source"]
    except NotFoundError:
        return None
    except Exception as e:
        print(f"[elastic/client] Error fetching profile for '{user_id}': {e}")
        return None


async def save_user_profile(user_id: str, profile_data: dict) -> dict:
    """
    Merges `profile_data` into the persona profile for `user_id` in the
    'user_profiles' index (partial update — fields not present in
    `profile_data` are left untouched). Creates the document if it does not
    exist yet (upsert), injecting 'user_id' and a zeroed 'profile_vector' as
    defaults for new documents. 'last_updated' is always refreshed.

    Args:
        user_id:      The unique identifier for the user.
        profile_data: Dictionary containing the persona fields to set/merge.

    Returns:
        The raw Elasticsearch response dict.
    """
    await _ensure_user_profiles_index()
    client = await get_client()
    try:
        # Inject required fields if missing
        profile_data.setdefault("user_id", user_id)
        profile_data.setdefault("profile_vector", [0.0] * 768)
        profile_data["last_updated"] = datetime.now(timezone.utc).isoformat()

        response = await client.update(
            index="user_profiles",
            id=user_id,
            doc=profile_data,
            doc_as_upsert=True,
            refresh=True,       # make the doc immediately searchable
        )
        return response
    except Exception as e:
        print(f"[elastic/client] Error saving profile for '{user_id}': {e}")
        raise
