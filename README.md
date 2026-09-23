---
title: Mini Healthcare Assistant
emoji: 🩺
colorFrom: blue
colorTo: green
sdk: streamlit
sdk_version: "1.38.0"
app_file: app.py
pinned: false
---

# Mini Healthcare Assistant

A small multi-agent demo: synthetic patient data, a greeting agent, a
CGM-aware meal planner agent, and a free-text Q&A "interrupt" agent — all
wired together in a single-page Streamlit app.

**This is a take-home/demo project. It uses only synthetic (Faker-generated)
data and is not medical advice.**

## How to run it locally

```bash
git clone <this-repo-url>
cd mini-healthcare-assistant
python -m venv .venv && source .venv/bin/activate   # optional
pip install -r requirements.txt

# Generate the synthetic dataset (also happens automatically on first app run)
python data/generate_data.py

# Enable real LLM responses via Groq's free API
cp .env.example .env
# then edit .env and set GROQ_API_KEY to a free key from https://console.groq.com/keys

streamlit run app.py
```

Without a valid `GROQ_API_KEY` set, the app still runs end-to-end — the
LLM-backed agents (meal planner, Q&A) return a clearly labeled placeholder
response instead of failing, so the full flow is still demonstrable offline.

## Architecture

```
data/generate_data.py    -> synthetic 20-patient CSV (Faker)
agents/greeting_agent.py -> looks up user by ID, re-prompts on invalid ID
agents/cgm_meal_agent.py -> flags glucose readings, builds LLM meal plan,
                             checks plausibility + diet compliance
agents/interrupt_agent.py -> answers one free-text question, returns to flow,
                              flags prompt-injection attempts
llm_client.py            -> Groq API wrapper: retries, output sanitization
app.py                    -> Streamlit UI: session-state persistence for
                             results, cached LLM calls, CGM-on-file prompt
```

## Key implementation decisions

- **Framework**: hand-rolled Python functions rather than a full agent
  framework (LangChain/Agno). For three agents with simple, linear
  hand-offs, explicit functions are easier to read and debug in the time
  available, and keep the LLM boundary obvious (`llm_client.chat`).
- **Model**: Groq's free-tier API serving an open-source model
  (`openai/gpt-oss-120b` by default, swappable via `GROQ_MODEL_ID`). No
  proprietary API key is used. Swapping in a local Ollama model or a
  different hosted provider only requires editing `llm_client.py` — every
  agent calls the single `chat()` function in that module.
- **Data**: Faker-generated CSV rather than SQLite — plenty for 20 rows,
  keeps the dataset human-readable and diffable in the repo. Note: a few
  generated CGM readings intentionally fall outside the 80–300 mg/dL
  range named in the data spec, so the "out of range" branch of the CGM
  agent has real data to demonstrate against rather than only being
  reachable by manual input.
- **CGM logic is deterministic, not LLM-based**: whether a reading is in
  range (80–300 mg/dL) is decided in plain Python (`check_glucose`), and
  only the *meal plan content* is delegated to the LLM. This keeps the
  safety-relevant range check testable and independent of model output.
- **CGM input is pre-filled, not auto-submitted**: after greeting, the app
  shows the patient's last recorded CGM reading from the dataset and
  pre-fills the input box with it, but the user must confirm or edit it
  before generating a plan — the reading is always a fresh, explicit
  submission (matching the brief's "CGM input" as its own UI step), not a
  silent pass-through of stored data.
- **Single-page UI**: everything (ID entry, greeting, CGM input, meal
  plan, Q&A box) lives on one Streamlit page with session state, per the
  assignment's scope — no multi-page routing or chat history was built.

### Guardrails (small, deliberately scoped — not a full safety system)

Each of these is a short, self-contained check, added because this is
framed as a *healthcare* assistant, where a couple of the likely failure
modes (LLM ignoring dietary constraints, a user typing an implausible
vital-sign value) felt worth a few lines of code rather than leaving
silent:

1. **CGM plausibility check** (`cgm_meal_agent.is_plausible`) — readings
   outside a wider 40–400 mg/dL band are rejected outright (likely a typo
   or device error), separate from the 80–300 "normal" band check.
2. **Diet-compliance keyword scan** (`cgm_meal_agent._check_diet_compliance`)
   — after the LLM returns a meal plan, a small keyword list flags if a
   vegan/veg plan mentions meat, egg, or dairy terms, and shows a visible
   warning rather than trusting the prompt instruction blindly. A short
   allow-list (`_VEGAN_SAFE_PHRASES`) excludes plant-based phrases like
   "soy milk" or "almond milk" first, so they don't false-positive on the
   bare substring "milk" — a real gap caught during manual testing.
3. **Prompt-injection heuristic** (`interrupt_agent._looks_like_injection`)
   — the Q&A system prompt tells the model the user's message is data to
   answer, not instructions to obey, and a lightweight phrase check flags
   obvious injection attempts (e.g. "ignore previous instructions") with a
   visible note.
4. **Output sanitization + retry** (`llm_client._sanitize_output`, `chat`)
   — empty LLM replies are caught, overly long ones are truncated, and
   transient failures are retried up to twice with backoff before showing
   an error.
5. **Response caching** (`app.py`, `st.cache_data`) — identical inputs
   (same patient + same CGM reading, or the same question) are cached for
   an hour, so re-submitting the same values returns instantly without a
   second LLM call — protects the free-tier quota without an intrusive
   rate-limit message, and a short artificial minimum spinner delay keeps
   the loading feedback visible even on a cache hit.
6. **Session-state result persistence** (`app.py`) — generated plans and
   answers are stored in `st.session_state` and always re-rendered, so
   they don't disappear when the script re-runs for an unrelated reason
   (e.g. typing in the Q&A box), which was a real bug found during testing.

None of these are full production-grade solutions (the keyword scans in
particular are simple substring checks, not semantic validation) — they're
sized to demonstrate awareness of the failure mode within a few lines each,
consistent with the assignment's "don't over-engineer" guidance.

## What I'd add with more time

- A **Mood Tracker** and **Food Intake** agent, as suggested in the brief.
- Persist a longer conversation/session history instead of just the last
  result per section.
- Unit tests for `check_glucose`, `is_plausible`, and the greeting lookup
  (pure functions, easy to test; skipped here to stay inside the time box).
- A `Dockerfile` is included for portability (not required for a
  Streamlit-SDK Space, which runs `app.py` directly), but it isn't wired
  into the HF deployment itself — that would be a separate Docker-SDK
  Space if ever needed.
- Structured output (JSON) from the LLM for the meal plan so it could be
  rendered as a table and validated more rigorously than a keyword scan.
- Replace the substring-based diet/injection checks with a small
  second LLM call ("does this plan violate the stated diet?") for more
  reliable detection than keyword matching.
- The in-memory cache (`st.cache_data`) resets whenever the Space
  restarts/sleeps — fine for a demo, but a persistent cache (e.g. a small
  SQLite file) would survive restarts in a longer-lived deployment.
