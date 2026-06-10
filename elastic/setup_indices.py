import asyncio
import json
import os
import sys

from elastic.client import get_client

MAPPINGS_DIR = os.path.join(os.path.dirname(__file__), "mappings")
MAPPING_FILES = ["behavioral_events.json", "user_profiles.json"]


async def run_setup() -> None:
    client = await get_client()

    for filename in MAPPING_FILES:
        index_name = os.path.splitext(filename)[0]
        with open(os.path.join(MAPPINGS_DIR, filename), encoding="utf-8") as f:
            mapping_body = json.load(f)

        if await client.indices.exists(index=index_name):
            print(f"[setup_indices] '{index_name}' already exists — skipping")
            continue

        await client.indices.create(index=index_name, body=mapping_body)
        print(f"[setup_indices] Created '{index_name}' from {filename}")


async def main() -> None:
    await run_setup()
    client = await get_client()
    await client.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"[setup_indices] Failed: {e}")
        sys.exit(1)
