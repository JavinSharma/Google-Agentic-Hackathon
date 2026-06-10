# End-to-End Smoke Test Plan — Hyper-Context Engine

Manual test steps for verifying the system before/during the judges' demo.
Run from the project root (`hyper-context-engine/`) unless noted otherwise.

## Status Legend
- ✅ Ready to test now
- ❓ Pending teammate work — section written against the planned contract in `CLAUDE.md`; re-verify once that slice lands
- 🔄 Pending Slice 4 infra (T2/T6/T7)

---

## 0. Prerequisites Checklist

- [ ] `.env` populated with `ELASTIC_URL`, `ELASTIC_API_KEY` (✅ done)
- [ ] `.env` populated with `GOOGLE_API_KEY` / `GOOGLE_CLOUD_PROJECT` (❓ pending Slice 3 setup)
- [ ] `elastic/mappings/user_profiles.json` exists with confirmed index name (❓ pending Person B)
- [ ] `python elastic/setup_indices.py` exits 0 (🔄 pending T2)
- [ ] `agent/agent.py` runner loop + event hooks wired (❓ pending Person C / T4)
- [ ] Thought Trace panel present in `frontend/app.py` (🔄 pending T5)

---

## 1. Local Environment Setup ✅

```bash
pip install -r requirements.txt

# Once T2 lands — bootstraps/validates Elastic indices, safe to re-run:
python elastic/setup_indices.py

# Terminal 1 — backend
uvicorn backend.main:app --reload

# Terminal 2 — frontend
streamlit run frontend/app.py
```

**Expected:**
- `http://localhost:8000/` returns `{"status": "running"}`
- `http://localhost:8501` loads the Streamlit UI without errors

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
   Confirm 3 documents exist with correct `action_type`, `topic`, `session_id: "default"`, and an auto-populated `timestamp`.

---

## 3. Slice 2 — Context Engine ❓ (pending Person B)

> Verify once `elastic/mappings/user_profiles.json`, `agent/tools/fetch_context.py`,
> `agent/tools/update_profile.py`, and Person B's hook in `backend/routes/query.py` land.

1. After firing the Slice 1 events above, check the **Live Personalization Profile** sidebar.
   - Expect top interests derived from recent events (e.g., "machine learning", "quantum computing") to appear for `user_001`.
2. Send a chat message (Slice 3 UI) for `user_001`.
   - Confirm `fetch_context` is called before the agent responds (visible in Thought Trace once T4/T5 land) and returns a plain-text profile summary.
3. After the agent responds, confirm `update_profile` fires and the corresponding `user_profiles` document is created/updated:
   ```
   GET user_profiles/_search
   { "query": { "term": { "user_id": "user_001" } } }
   ```
4. Confirm the sidebar reflects the updated profile after a rerun.

---

## 4. Slice 3 — Conversational Core ❓ (pending Person C)

> Verify once `agent/agent.py`, `agent/prompts.py`, `backend/routes/query.py` (core),
> and the `st.chat_input`/`st.chat_message` thread in `frontend/app.py` land.

1. Type a message referencing a tracked topic, e.g. *"What should I read about machine learning?"*
2. Confirm a streamed response appears in `st.chat_message`.
3. Confirm the response tone/content reflects `user_001`'s profile (per `agent/prompts.py` instructions) — e.g., explicitly references the "machine learning" interest.
4. Check backend logs for the request — confirm no unhandled exceptions.

---

## 5. Slice 4 — Thought Trace Panel 🔄 (pending T4/T5)

> Verify once the event-hook interception (T4) and the `st.expander` panel (T5) land.

1. Expand **🧠 View Agent Thought Trace** below the chat thread.
2. Send a chat message for `user_001`.
3. Confirm new JSON frames appear for each ToolCall/ToolResponse pair:
   - `fetch_context` (called before the agent's reply)
   - `log_user_action` (if the agent logs an action during the turn)
   - `update_profile` (called after the agent's reply)
4. Confirm frame order matches the actual call order, and that the chat response itself is **not** delayed, swallowed, or duplicated by the hook (events are yielded onward unchanged).
5. Confirm frames persist for the session via `st.session_state` and reset on a fresh session/page reload.

---

## 6. Deployment Smoke Test 🔄 (pending T6/T7)

> Verify once `deploy/Dockerfile` and `deploy/cloud_run_deploy.sh` land.

1. Run `./deploy/cloud_run_deploy.sh`.
2. Confirm the script prints a deployed service URL on success.
3. `curl <URL>/` → expect `{"status": "running"}`.
4. Open the deployed URL (or Streamlit's exposed path, per T6's single-port resolution) in a browser.
5. Repeat Sections 2–5 against the deployed service.
6. Confirm env vars (Elastic creds, Google API key) were injected via `--set-env-vars` and are **not** baked into the image.

---

## 7. Judges' Demo Script (condensed, ~3–5 min)

1. Open the app with a fresh `user_id` — show the **Live Personalization Profile** sidebar empty/default.
2. Click 2–3 Activity Simulator buttons to simulate browsing history.
3. Point out the sidebar updating with derived interests in near real-time.
4. Ask the chat a question related to one of those interests — highlight that the response is personalized.
5. Expand the **Thought Trace** panel and walk through the JSON frames:
   - `fetch_context` retrieving the profile Gemini used to personalize its answer
   - `update_profile` writing the updated interest state back
   - *"This is the transparency layer — it shows judges exactly what the agent saw and did, not just the final answer."*
6. (If deployed) repeat the flow against the live Cloud Run URL to show it works end-to-end in production.
