# Mini Healthcare Assistant

A small multi-agent demo: synthetic patient data, a greeting agent, a
CGM-aware meal planner agent, and a free-text Q&A "interrupt" agent — all
wired together in a single-page Streamlit app.

**This is a take-home/demo project. It uses only synthetic (Faker-generated)
data and is not medical advice.**

## Live deployment

**https://healthcare-assistant-jcuca89kdjx9zilrwfm2vb.streamlit.app/**

Deployed via **Streamlit Community Cloud** rather than a Hugging Face Space
— HF Spaces has no free CPU tier for always-on apps at the time of
submission, while Streamlit Community Cloud is free and deploys directly
from this repo's `app.py`, so it was the closer match to the brief's
"live, public, free" intent.

## How to run it locally

```bash
git clone <this-repo-url>
cd healthcare-assistant
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
