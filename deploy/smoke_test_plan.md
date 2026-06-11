# End-to-End Smoke Test Plan — Hyper-Context Engine

Manual test steps for verifying the system before/during the judges' demo.
Run from the project root (`hyper-context-engine/`) unless noted otherwise.

## Status Legend
- ✅ Verified locally this session
- 🅰️ Pending Person A — needs `GOOGLE_API_KEY` (or Vertex AI credentials) in `.env`
- 🔄 Pending Slice 4 infra (T6/T7 — Dockerfile / Cloud Run deploy)

---

## 0. Prerequisites Checklist

- [x] `.env` populated with `ELASTIC_URL`, `ELASTIC_API_KEY` (✅ done)
- [ ] `.env` populated with `GOOGLE_API_KEY` (or `GOOGLE_CLOUD_PROJECT` + ADC for Vertex AI) (🅰️ pending Person A — see handoff below)
- [x] `elastic/mappings/user_profiles.json` exists, index name `user_profiles` confirmed (✅ done)
- [x] `python -m elastic.setup_indices` exits 0 (✅ verified — created `user_profiles`, `behavioral_events` already existed)
- [x] `agent/agent.py` runner + thought-trace capture wired (✅ done — `run_agent()` returns `(text, thought_trace)`)
- [x] Thought Trace panel present in `frontend/app.py` (✅ done — `render_thought_trace()` + `st.expander`)

---

## 0.5 Handoff for Person A — Finish the Chat Smoke Test 🅰️

Everything below is built and wired. The chat path (`POST /api/query`) was
tested end-to-end this session and fails *only* at the final Gemini client
construction:

```
ValueError: No API key was provided. Please pass a valid API key.
```

Routing, request validation, session creation (`InMemorySessionService`), the
MCP toolset (`fetch_user_context` / `update_user_profile` registered and
importable), and the Thought Trace plumbing are all confirmed working up to
that point. This is the only missing piece.

**To finish:**
1. Add a Gemini credential to `.env`:
   - AI Studio: set `GOOGLE_API_KEY=<your key>`
   - OR Vertex AI: set `GOOGLE_CLOUD_PROJECT=<project-id>`, run
     `gcloud auth application-default login`, and set
     `GOOGLE_GENAI_USE_VERTEXAI=true` if required by your `google-genai` version
2. Restart the backend: `uvicorn backend.main:app --reload`
3. Run through **Sections 3–5** below (Context Engine synthesis, Conversational
   Core, Thought Trace Panel) — these are the only sections that call Gemini.
4. Tick off the remaining `[ ]` box in Section 0 once confirmed.

---

## 1. Local Environment Setup ✅

```bash
# Recommend a venv:
python -m venv .venv
.venv/Scripts/activate   # or source .venv/bin/activate on macOS/Linux

pip install -r requirements.txt

# Bootstraps/validates Elastic indices, safe to re-run:
python -m elastic.setup_indices

# Terminal 1 — backend
uvicorn backend.main:app --reload

# Terminal 2 — frontend
streamlit run frontend/app.py
```

**Expected:**
- `python -m elastic.setup_indices` prints one line per index (created or
  already-exists) and exits 0
- `http://localhost:8000/health` returns `{"status": "ok"}`
- `http://localhost:8000/` returns `{"status": "running"}`
- `http://localhost:8501` loads the Streamlit UI without errors

**Verified this session** ✅ against the real Elastic Cloud cluster and a
local `.venv`/`uvicorn`. Note: `requirements.txt` was missing `aiohttp`
(required by the async Elasticsearch transport) — this has been added.

---

## 2. Slice 1 — Activity Tracker ✅

1. In the Streamlit UI, locate the **Activity Simulator** section.
2. Enter a `user_id` (default `user_001`).
3. Click **Read ML Article** → expect `Tracked: view → machine learning` success toast.
4. Click **Search Quantum Computing** → expect `Tracked: search → quantum computing` success toast.
5. Click **Dismiss Finance News** → expect `Tracked: dismiss → finance` success toast.
6. In Kibana (or via the Elastic API), query:
   ```
   GET behavioral_events/_search
   { "query": { "term": { "user_id": "user_001" } } }
   ```
   Confirm documents exist with correct `action_type`, `topic`, `session_id: "default"`, and an auto-populated `timestamp`.

**Verified this session** ✅ — `POST /api/events` returns
`{"success": true, "event_id": "...", "message": "Event logged"}`.

---

## 3. Slice 2 — Context Engine ✅ (landed)

1. After firing the Slice 1 events above, check the **Live Personalization Profile** sidebar for `user_001`.
   - If no profile document exists yet, expect: *"No profile exists yet for this user."*
2. Click **✨ Synthesise Profile** 🅰️ (calls Gemini via `trigger_profile_synthesis` — needs `GOOGLE_API_KEY`).
   - Expect a `user_profiles` document to be created/updated:
     ```
     GET user_profiles/_search
     { "query": { "term": { "user_id": "user_001" } } }
     ```
   - Confirm the sidebar now shows `persona`, `interests`, `dislikes`,
     `communication_style`, `technical_depth`, and `last_updated`.
3. `fetch_user_context(user_id)` returns a JSON string:
   `{"recent_events": [...], "current_profile": {...} | null}` — this is what
   the chat agent (Section 4) consumes.
4. `update_user_profile` performs a **partial merge**
   (`client.update(doc=..., doc_as_upsert=True)`). Confirm that calling it with
   only `{"interests": [...]}` does **not** erase `persona` / `dislikes` /
   `communication_style` / `technical_depth` on an existing profile.

---

## 4. Slice 3 — Conversational Core 🅰️ (built, pending Person A's API key)

`POST /api/query` — body `{"user_id": ..., "message": ..., "session_id": ...}`,
response `{"response": "...", "thought_trace": [...]}`.

**Confirmed this session** (no API key needed):
- Endpoint registered, request validated, session created via `InMemorySessionService`.
- Without `GOOGLE_API_KEY`, fails cleanly with `500: No API key was provided`,
  surfaced in the chat UI as `⚠️ Error: ...` (per `backend/routes/query.py` /
  `frontend/app.py`).

**Pending Person A's API key:**
1. Type a message referencing a tracked topic, e.g. *"What should I read about machine learning?"*
2. Confirm a response appears in `st.chat_message("assistant")`.
3. Confirm the response tone/content reflects `user_001`'s profile (per
   `agent/prompts.py` §2 PERSONALIZE) — e.g. an ML-flavoured analogy if
   `interests` includes "machine learning".
4. Confirm `log_user_action` fires for substantive answers (check
   `behavioral_events` for a new `action_type: "search"` doc, or watch the
   Thought Trace panel — Section 5).
5. Confirm `update_user_profile` fires only when the message reveals a *new*
   interest not already in `current_profile.interests`.

---

## 5. Thought Trace Panel ✅ built / 🅰️ live verification pending Person A

Implemented in `frontend/app.py` via `render_thought_trace()`, called for
every assistant message (new replies and replayed history) inside an
`st.expander("🔍 Thought Trace")`.

**Pending Person A's API key:**
1. Send a chat message for `user_001`.
2. Expand **🔍 Thought Trace** under the assistant's reply.
3. Confirm frames appear for each tool call/response pair, in order:
   - `fetch_user_context` (tool_call → tool_response)
   - `log_user_action` (if the agent logged this turn)
   - `update_user_profile` (if a new interest was detected)
4. Confirm `tool_call` frames render `args` via `st.json`, and `tool_response`
   frames render `response` via `st.json`.
5. Confirm the chat response itself is not delayed or duplicated by trace capture.
6. Reload the page / start a new browser session — confirm `chat_history` and
   the trace panels reset (both are per-`st.session_state`).

---

## 6. Deployment Smoke Test ✅ built / 🅰️ untested live (needs `gcloud auth` + GCP project)

`deploy/Dockerfile.backend` and `deploy/Dockerfile.frontend` build two
separate images; `deploy/cloud_run_deploy.sh` deploys both as Cloud Run
services and wires `BACKEND_URL`/`FRONTEND_URL` between them.

1. Ensure `.env` has `GOOGLE_CLOUD_PROJECT` set to a real GCP project (and
   `gcloud auth login` has been run with access to it).
2. Run `./deploy/cloud_run_deploy.sh` from the project root.
3. Confirm it prints both a backend and frontend URL on success.
4. `curl <BACKEND_URL>/health` → expect `{"status": "ok"}`.
5. Open `<FRONTEND_URL>` in a browser.
6. Repeat Sections 2–5 against the deployed service.
7. Confirm env vars (Elastic creds, Google API key, `FRONTEND_URL`/`BACKEND_URL`)
   were injected via `--set-env-vars`/`--update-env-vars` and are **not**
   baked into either image (`.dockerignore` excludes `.env`).

---

## 7. Judges' Demo Script (condensed, ~3–5 min)

1. Open the app with a fresh `user_id` — show the **Live Personalization Profile** sidebar empty/default.
2. Click 2–3 Activity Simulator buttons to simulate browsing history.
3. Point out the sidebar updating with derived interests in near real-time.
4. Ask the chat a question related to one of those interests — highlight that the response is personalized. 🅰️
5. Expand the **Thought Trace** panel and walk through the JSON frames: 🅰️
   - `fetch_user_context` retrieving the profile Gemini used to personalize its answer
   - `log_user_action` / `update_user_profile` writing the updated state back
   - *"This is the transparency layer — it shows judges exactly what the agent saw and did, not just the final answer."*
6. (If deployed) repeat the flow against the live Cloud Run URL to show it works end-to-end in production.
