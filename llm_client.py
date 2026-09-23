"""
Thin wrapper around an open-source LLM, served via Groq's free-tier API.

Groq hosts open-source models (Llama 3.1, GPT-OSS, etc.) and serves them
over its own OpenAI-compatible endpoint. Set GROQ_API_KEY (in a local
.env file, or as an environment variable / Streamlit secret) to a free
key from https://console.groq.com/keys.

No API key from the employer is used or required, per the assignment brief.
Swap MODEL_ID for any other open model Groq hosts, or point this module at
a different open-source backend entirely (e.g. Ollama running locally) —
every agent only calls the chat() function below, so that's the one place
to change.

Guardrails included:
- Retry with backoff on transient failures (up to MAX_RETRIES attempts).
- Basic output sanity checks: rejects empty replies and truncates
  absurdly long ones before they're shown to the user.
"""
import os
import time

from dotenv import load_dotenv
from groq import Groq

load_dotenv()  # reads a local .env file, if present, into os.environ

MODEL_ID = os.environ.get("GROQ_MODEL_ID", "openai/gpt-oss-120b")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

MAX_RETRIES = 2          # total attempts = 1 + MAX_RETRIES
RETRY_BACKOFF_SECONDS = 1.5
MAX_OUTPUT_CHARS = 4000  # sanity cap in case a model loops/rambles

_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


def _sanitize_output(text: str) -> str:
    """Basic output-side guardrail: no empty replies, no runaway length."""
    text = (text or "").strip()
    if not text:
        return "[The model returned an empty response. Please try again.]"
    if len(text) > MAX_OUTPUT_CHARS:
        text = text[:MAX_OUTPUT_CHARS].rstrip() + "\n\n[...response truncated for length...]"
    return text


def chat(system_prompt: str, user_prompt: str, max_tokens: int = 400) -> str:
    """Send a system + user prompt to the LLM and return the text reply.

    Falls back to a clearly-labeled canned response if no GROQ_API_KEY is
    configured. Retries transient failures a couple of times with a short
    backoff before giving up and returning a labeled error string.
    """
    if _client is None:
        return (
            "[LLM not configured — set GROQ_API_KEY to enable real responses]\n"
            "This is a placeholder reply so the app keeps working."
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = _client.chat.completions.create(
                model=MODEL_ID, messages=messages, max_tokens=max_tokens, temperature=0.4
            )
            raw_text = response.choices[0].message.content
            return _sanitize_output(raw_text)
        except Exception as exc:  # network / rate-limit / server errors
            last_error = exc
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))  # simple linear backoff
            continue

    return f"[LLM call failed after {MAX_RETRIES + 1} attempts: {last_error}]"