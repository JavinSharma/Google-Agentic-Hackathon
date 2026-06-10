import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from elasticsearch import AsyncElasticsearch
from typing import Any

load_dotenv()

_client = None


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
