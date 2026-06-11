import os
import sys
import asyncio
import uuid
import streamlit as st
import httpx

# Ensure project root is in sys.path and takes precedence over site-packages
sys.path.insert(1, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from elastic.client import fetch_user_profile

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Hyper-Context Engine",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Global CSS — glassmorphic sidebar + pill tags
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* ---- Google Font ---- */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* ---- Interest pill ---- */
    .pill-interest {
        display: inline-block;
        padding: 4px 13px;
        margin: 3px 4px 3px 0;
        font-size: 12px;
        font-weight: 600;
        color: #ffffff;
        background: linear-gradient(135deg, #7F00FF 0%, #E100FF 100%);
        border-radius: 20px;
        box-shadow: 0 2px 8px rgba(127, 0, 255, 0.30);
        letter-spacing: 0.3px;
    }

    /* ---- Dislike pill ---- */
    .pill-dislike {
        display: inline-block;
        padding: 4px 13px;
        margin: 3px 4px 3px 0;
        font-size: 12px;
        font-weight: 600;
        color: #ffffff;
        background: linear-gradient(135deg, #FF416C 0%, #FF4B2B 100%);
        border-radius: 20px;
        box-shadow: 0 2px 8px rgba(255, 65, 108, 0.30);
        letter-spacing: 0.3px;
    }

    /* ---- Glassmorphic persona card ---- */
    .persona-card {
        background: rgba(255, 255, 255, 0.06);
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.12);
        padding: 14px 16px;
        margin: 8px 0 14px 0;
        font-size: 13px;
        line-height: 1.6;
        color: #e0e0e0;
        backdrop-filter: blur(8px);
    }

    /* ---- Metadata rows ---- */
    .meta-row {
        display: flex;
        align-items: center;
        gap: 8px;
        margin: 6px 0;
        font-size: 13px;
        color: #b0b8c8;
    }
    .meta-row .meta-label { flex-shrink: 0; }
    .meta-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 8px;
        font-size: 12px;
        font-weight: 700;
        background: rgba(255, 255, 255, 0.10);
        color: #ffffff;
        border: 1px solid rgba(255,255,255,0.15);
    }

    /* ---- Section label ---- */
    .section-label {
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 1.2px;
        text-transform: uppercase;
        color: #8892a4;
        margin: 14px 0 6px 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def fire_event(user_id: str, action_type: str, topic: str) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{BACKEND_URL}/api/events",
            json={"user_id": user_id, "action_type": action_type, "topic": topic},
        )
        response.raise_for_status()
        return response.json()


async def send_query(user_id: str, message: str, session_id: str) -> dict:
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{BACKEND_URL}/api/query",
            json={"user_id": user_id, "message": message, "session_id": session_id},
        )
        response.raise_for_status()
        return response.json()


def render_thought_trace(thought_trace: list[dict]) -> None:
    """Renders a list of {"type": "tool_call"|"tool_response", "data": {...}} frames."""
    with st.expander("🔍 Thought Trace"):
        for frame in thought_trace:
            data = frame.get("data", {})
            if frame.get("type") == "tool_call":
                st.markdown(f"🔧 **Calling** `{data.get('name', '?')}`")
                if data.get("args"):
                    st.json(data["args"])
            else:
                st.markdown(f"↩️ **Response from** `{data.get('name', '?')}`")
                if data.get("response"):
                    st.json(data["response"])


def run_async(coro):
    """Bridge async coroutines into Streamlit's synchronous execution model cleanly."""
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Main page — Activity Simulator (Slice 1 preserved)
# ---------------------------------------------------------------------------
st.title("🧠 Hyper-Context Engine")
st.caption("Google ADK · Gemini 2.0 Flash · Elasticsearch · FastAPI · Streamlit")
st.divider()

st.subheader("⚡ Activity Simulator")
st.caption("Fire synthetic behavioral events to populate your user's history.")

def handle_user_change():
    st.session_state.chat_history = []
    st.session_state.session_id = str(uuid.uuid4())

st.markdown("#### 👤 Current User Context")
user_col, btn_col = st.columns([3, 1])

with user_col:
    user_id = st.text_input("User ID", value="user_001", key="user_id_input", on_change=handle_user_change)
    st.caption("Change this ID and press Enter to switch to a different user's profile.")

with btn_col:
    st.write("") # spacing
    st.write("")
    if st.button("🔄 Logout / Clear Chat", use_container_width=True):
        handle_user_change()
        st.rerun()

def _sim_btn(label, action, topic):
    if st.button(label, use_container_width=True):
        try:
            run_async(fire_event(user_id, action, topic))
            st.success(f"Tracked: **{action}** → {topic}")
        except Exception as e:
            st.error(f"Failed: {e}")

st.markdown("##### 💻 Tech & Science")
c1, c2, c3 = st.columns(3)
with c1: _sim_btn("📖 Read ML Article", "view", "machine learning")
with c2: _sim_btn("🔬 Search Quantum Computing", "search", "quantum computing")
with c3: _sim_btn("❌ Dismiss Blockchain", "dismiss", "blockchain")

st.markdown("##### 🎨 Arts & Lifestyle")
c4, c5, c6 = st.columns(3)
with c4: _sim_btn("🖼️ View Renaissance Art", "view", "art history")
with c5: _sim_btn("🎸 Search Indie Rock", "search", "indie music")
with c6: _sim_btn("❌ Dismiss Reality TV", "dismiss", "reality television")

st.markdown("##### 🏃 Health & Productivity")
c7, c8, c9 = st.columns(3)
with c7: _sim_btn("👟 View Marathon Training", "view", "running")
with c8: _sim_btn("🥗 Search Vegan Recipes", "search", "vegan cooking")
with c9: _sim_btn("❌ Dismiss Fast Food", "dismiss", "fast food")

st.markdown("##### 📈 Finance & Business")
c10, c11, c12 = st.columns(3)
with c10: _sim_btn("📊 View Index Funds", "view", "investing")
with c11: _sim_btn("🏢 Search Startup Funding", "search", "startups")
with c12: _sim_btn("❌ Dismiss Crypto News", "dismiss", "cryptocurrency")

# ---------------------------------------------------------------------------
# Main page — Chat (Slice 3) + Thought Trace (Slice 4)
# ---------------------------------------------------------------------------
st.divider()
st.subheader("💬 Chat with your Hyper-Context Agent")
st.caption("Responses adapt to the persona shown in the sidebar.")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("thought_trace"):
            render_thought_trace(msg["thought_trace"])

if prompt := st.chat_input("Ask me anything..."):
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                result = run_async(send_query(user_id, prompt, st.session_state.session_id))
                response_text = result["response"]
                thought_trace = result.get("thought_trace", [])
            except Exception as e:
                response_text = f"⚠️ Error: {e}"
                thought_trace = []

        st.markdown(response_text)
        if thought_trace:
            render_thought_trace(thought_trace)

    st.session_state.chat_history.append(
        {"role": "assistant", "content": response_text, "thought_trace": thought_trace}
    )
    st.rerun()

# ---------------------------------------------------------------------------
# Sidebar — Live Personalization Profile (Slice 2)
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🪪 Live Personalization Profile")
    st.caption(f"Showing profile for `{user_id}`")
    st.divider()

    # Load profile from Elasticsearch
    profile: dict | None = None
    try:
        profile = run_async(fetch_user_profile(user_id))
    except Exception as e:
        st.warning(f"Could not load profile: {e}")

    if profile:
        # ---- Persona summary card ----------------------------------------
        st.markdown('<div class="section-label">User Persona</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="persona-card">{profile.get("persona", "—")}</div>',
            unsafe_allow_html=True,
        )

        # ---- Interests pills ---------------------------------------------
        st.markdown('<div class="section-label">Interests</div>', unsafe_allow_html=True)
        interests = profile.get("interests", [])
        if interests:
            pills = "".join(
                f'<span class="pill-interest">{tag}</span>' for tag in interests
            )
            st.markdown(pills, unsafe_allow_html=True)
        else:
            st.caption("*None tracked yet*")

        # ---- Dislikes pills ----------------------------------------------
        st.markdown('<div class="section-label">Disliked Topics</div>', unsafe_allow_html=True)
        dislikes = profile.get("dislikes", [])
        if dislikes:
            pills = "".join(
                f'<span class="pill-dislike">{tag}</span>' for tag in dislikes
            )
            st.markdown(pills, unsafe_allow_html=True)
        else:
            st.caption("*None tracked yet*")

        # ---- Metadata badges ---------------------------------------------
        st.markdown("---")
        comm_style = profile.get("communication_style", "N/A").capitalize()
        tech_depth = profile.get("technical_depth", "N/A").capitalize()
        last_updated = profile.get("last_updated", "N/A")

        st.markdown(
            f"""
            <div class="meta-row">
                <span class="meta-label">💬 Style</span>
                <span class="meta-badge">{comm_style}</span>
            </div>
            <div class="meta-row">
                <span class="meta-label">🔬 Depth</span>
                <span class="meta-badge">{tech_depth}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(f"🕒 Last synthesised: {last_updated}")

    else:
        st.info(
            "No profile exists yet for this user.  \n"
            "Simulate some activity above, then click **Synthesise Profile** below."
        )

    # ---- Synthesis trigger -----------------------------------------------
    st.markdown("---")
    if st.button("✨ Synthesise Profile", use_container_width=True, type="primary"):
        with st.spinner("Fetching logs & calling Gemini 2.0 Flash…"):
            try:
                from agent.tools.update_profile import trigger_profile_synthesis
                run_async(trigger_profile_synthesis(user_id))
                st.success("Profile synthesised!")
                st.rerun()
            except Exception as e:
                st.error(f"Synthesis failed: {e}")
