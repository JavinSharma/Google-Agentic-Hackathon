import os
import asyncio
import streamlit as st
import httpx

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


async def fire_event(user_id: str, action_type: str, topic: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BACKEND_URL}/api/events",
            json={
                "user_id": user_id,
                "action_type": action_type,
                "topic": topic
            }
        )
        response.raise_for_status()
        return response.json()


st.subheader("Activity Simulator")

user_id = st.text_input("User ID", value="user_001")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("Read ML Article"):
        try:
            asyncio.run(fire_event(user_id, "view", "machine learning"))
            st.success("Tracked: view → machine learning")
        except Exception as e:
            st.error(f"Failed: {e}")

with col2:
    if st.button("Search Quantum Computing"):
        try:
            asyncio.run(fire_event(user_id, "search", "quantum computing"))
            st.success("Tracked: search → quantum computing")
        except Exception as e:
            st.error(f"Failed: {e}")

with col3:
    if st.button("Dismiss Finance News"):
        try:
            asyncio.run(fire_event(user_id, "dismiss", "finance"))
            st.success("Tracked: dismiss → finance")
        except Exception as e:
            st.error(f"Failed: {e}")
