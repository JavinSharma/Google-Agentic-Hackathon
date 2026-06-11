import os
import sys
import asyncio
import uuid
import hashlib
import streamlit as st
import httpx

# Ensure project root is in sys.path and takes precedence over site-packages
sys.path.insert(1, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from elastic.client import fetch_user_profile

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# ---------------------------------------------------------------------------
# Demo credentials  (username → sha256(password))
# In production, replace with a real auth backend / OAuth flow.
# ---------------------------------------------------------------------------
def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

DEMO_USERS: dict[str, dict] = {
    "user_001": {"password_hash": _hash("demo1234"),  "display_name": "Alice (Demo)"},
    "user_002": {"password_hash": _hash("demo5678"),  "display_name": "Bob (Demo)"},
    "admin":    {"password_hash": _hash("admin2024"), "display_name": "Admin"},
}

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
# Login CSS — full-viewport hero + glassmorphic card
# ---------------------------------------------------------------------------
LOGIN_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ---- Hide Streamlit chrome on login page ---- */
[data-testid="stSidebar"]        { display: none !important; }
[data-testid="stToolbar"]        { display: none !important; }
[data-testid="stDecoration"]     { display: none !important; }
header                           { display: none !important; }
footer                           { display: none !important; }

/* ---- Full-viewport background ---- */
.login-bg {
    position: fixed; inset: 0; z-index: 0;
    background: radial-gradient(ellipse at 20% 50%, #1a0533 0%, #0a0a1a 55%, #001233 100%);
    overflow: hidden;
}

/* ---- Animated glow orbs ---- */
.orb {
    position: absolute; border-radius: 50%;
    filter: blur(80px); opacity: 0.45;
    animation: float 8s ease-in-out infinite;
}
.orb-1 { width:420px; height:420px; background:#7F00FF;
          top:-80px; left:-80px; animation-delay:0s; }
.orb-2 { width:340px; height:340px; background:#E100FF;
          bottom:-60px; right:-60px; animation-delay:-3s; }
.orb-3 { width:260px; height:260px; background:#00B4FF;
          top:40%; left:55%; animation-delay:-6s; }

@keyframes float {
    0%,100% { transform: translateY(0px) scale(1); }
    50%      { transform: translateY(-30px) scale(1.06); }
}

/* ---- Card wrapper ---- */
.login-card {
    position: relative; z-index: 10;
    background: rgba(255,255,255,0.055);
    border: 1px solid rgba(255,255,255,0.13);
    border-radius: 24px;
    padding: 48px 44px 40px;
    backdrop-filter: blur(22px);
    -webkit-backdrop-filter: blur(22px);
    box-shadow: 0 8px 48px rgba(0,0,0,0.55),
                0 0 0 1px rgba(255,255,255,0.06) inset;
    max-width: 440px;
    margin: 0 auto;
    font-family: 'Inter', sans-serif;
}

/* ---- Logo / brand ---- */
.login-logo {
    font-size: 52px;
    text-align: center;
    margin-bottom: 4px;
    filter: drop-shadow(0 0 24px rgba(127,0,255,0.7));
}
.login-brand {
    text-align: center;
    font-size: 26px;
    font-weight: 800;
    letter-spacing: -0.5px;
    background: linear-gradient(135deg, #bf7fff 0%, #e040fb 50%, #7c4dff 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 4px;
}
.login-tagline {
    text-align: center;
    font-size: 13px;
    color: #8892a4;
    margin-bottom: 36px;
    letter-spacing: 0.2px;
}

/* ---- Divider ---- */
.login-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.15), transparent);
    margin: 28px 0;
}

/* ---- Demo hint badge ---- */
.demo-hint {
    background: rgba(127,0,255,0.15);
    border: 1px solid rgba(127,0,255,0.3);
    border-radius: 10px;
    padding: 12px 16px;
    font-size: 12px;
    color: #c8a8ff;
    margin-top: 24px;
    line-height: 1.7;
}
.demo-hint code {
    background: rgba(255,255,255,0.1);
    padding: 1px 6px;
    border-radius: 4px;
    font-size: 11.5px;
    color: #e0c8ff;
}

/* ---- Error box ---- */
.login-error {
    background: rgba(255,65,108,0.15);
    border: 1px solid rgba(255,65,108,0.35);
    border-radius: 10px;
    padding: 10px 14px;
    font-size: 13px;
    color: #ff8fab;
    margin-bottom: 8px;
    text-align: center;
}

/* ---- Streamlit input overrides ---- */
[data-testid="stTextInput"] > div > div > input {
    background: rgba(255,255,255,0.07) !important;
    border: 1px solid rgba(255,255,255,0.15) !important;
    border-radius: 10px !important;
    color: #ffffff !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 14px !important;
    padding: 10px 14px !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
[data-testid="stTextInput"] > div > div > input:focus {
    border-color: rgba(127,0,255,0.6) !important;
    box-shadow: 0 0 0 3px rgba(127,0,255,0.18) !important;
    outline: none !important;
}
[data-testid="stTextInput"] label {
    color: #a0aec0 !important;
    font-size: 12.5px !important;
    font-weight: 600 !important;
    letter-spacing: 0.4px !important;
    text-transform: uppercase !important;
}

/* ---- Primary button override ---- */
[data-testid="stFormSubmitButton"] > button,
.login-btn button {
    width: 100% !important;
    background: linear-gradient(135deg, #7F00FF 0%, #E100FF 100%) !important;
    border: none !important;
    border-radius: 12px !important;
    color: #ffffff !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 15px !important;
    font-weight: 700 !important;
    padding: 12px 0 !important;
    letter-spacing: 0.3px !important;
    cursor: pointer !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease !important;
    box-shadow: 0 4px 20px rgba(127,0,255,0.45) !important;
    margin-top: 8px !important;
}
[data-testid="stFormSubmitButton"] > button:hover,
.login-btn button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 30px rgba(127,0,255,0.65) !important;
}
[data-testid="stFormSubmitButton"] > button:active {
    transform: translateY(0px) !important;
}
</style>
"""


def render_login_page() -> None:
    """Render the full-screen login page and handle auth state."""
    st.markdown(LOGIN_CSS, unsafe_allow_html=True)

    # Background gradient + orbs
    st.markdown(
        """
        <div class="login-bg">
            <div class="orb orb-1"></div>
            <div class="orb orb-2"></div>
            <div class="orb orb-3"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Centre column layout
    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        st.markdown(
            """
            <div class="login-card">
                <div class="login-logo">🧠</div>
                <div class="login-brand">Hyper-Context Engine</div>
                <div class="login-tagline">Google ADK · Gemini 2.0 Flash · Elasticsearch</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Error placeholder
        error_box = st.empty()

        # Login form
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username", placeholder="e.g. user_001")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("Sign In →")

        if submitted:
            user_rec = DEMO_USERS.get(username)
            if user_rec and user_rec["password_hash"] == _hash(password):
                st.session_state.authenticated = True
                st.session_state.logged_in_user = username
                st.session_state.display_name = user_rec["display_name"]
                # Pre-seed the user_id_input so the main app uses the logged-in user
                st.session_state.user_id_input = username
                st.session_state.chat_history = []
                st.session_state.session_id = str(uuid.uuid4())
                st.rerun()
            else:
                error_box.markdown(
                    '<div class="login-error">⚠️ Invalid username or password. Please try again.</div>',
                    unsafe_allow_html=True,
                )

        st.markdown(
            """
            <div class="demo-hint">
                <strong>🔑 Demo credentials</strong><br>
                <code>user_001</code> / <code>demo1234</code><br>
                <code>user_002</code> / <code>demo5678</code><br>
                <code>admin</code> &nbsp;&nbsp;&nbsp;/ <code>admin2024</code>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Auth gate — must run before any other page content
# ---------------------------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    render_login_page()
    st.stop()

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
    _default_uid = st.session_state.get("logged_in_user", "user_001")
    user_id = st.text_input("User ID", value=_default_uid, key="user_id_input", on_change=handle_user_change)
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
    # ---- Session header + logout ------------------------------------------
    display = st.session_state.get("display_name", st.session_state.get("logged_in_user", "User"))
    st.markdown(
        f"""
        <div style="
            background: rgba(127,0,255,0.12);
            border: 1px solid rgba(127,0,255,0.25);
            border-radius: 12px;
            padding: 12px 14px;
            margin-bottom: 4px;
        ">
            <div style="font-size:12px;color:#8892a4;font-weight:600;letter-spacing:0.5px;text-transform:uppercase;">Signed in as</div>
            <div style="font-size:15px;font-weight:700;color:#e0c8ff;margin-top:2px;">{display}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("🚪 Sign Out", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    st.divider()

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
