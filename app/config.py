import os
from dotenv import load_dotenv

load_dotenv()


def _as_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on", "enabled"}


def _normalize_url(value, fallback):
    candidate = (value or fallback).strip().rstrip("/")
    return candidate or fallback


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Local model fallback stays disabled by default for safety.
LOCAL_LLM_ENABLED = _as_bool(os.getenv("LOCAL_LLM_ENABLED"), False)
LOCAL_LLM_PROVIDER = (os.getenv("LOCAL_LLM_PROVIDER") or "ollama").strip().lower() or "ollama"
LOCAL_LLM_BASE_URL = _normalize_url(os.getenv("LOCAL_LLM_BASE_URL"), "http://localhost:11434")
LOCAL_LLM_MODEL = (os.getenv("LOCAL_LLM_MODEL") or os.getenv("OLLAMA_MODEL") or "llama3.1").strip() or "llama3.1"
LOCAL_LLM_TIMEOUT = float(os.getenv("LOCAL_LLM_TIMEOUT") or "30.0")
# Real AI via an external LLM provider (OpenAI-compatible API, e.g. OpenRouter).
# Runs on Render: set LLM_API_KEY (and optionally LLM_MODEL) in the service env.
LLM_API_KEY = os.getenv("LLM_API_KEY") or os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
LLM_BASE_URL = _normalize_url(os.getenv("LLM_BASE_URL"), "https://openrouter.ai/api/v1")
LLM_MODEL = (os.getenv("LLM_MODEL") or "google/gemma-4-31b-it:free").strip()
LLM_FALLBACK_MODELS = [
    model.strip()
    for model in (
        os.getenv("LLM_FALLBACK_MODELS")
        or "qwen/qwen3.8-27b:free,thinkingmachines/inkling-small:free,"
           "nvidia/nemotron-3.5-lightning:free,dots-studio/dots-3-note-preview:free,"
           "google/gemma-4-26b-a4b-it:free"
    ).split(",")
    if model.strip()
]
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT") or "40.0")
CHAT_ALLOWED_ORIGINS = {
    origin.strip().rstrip("/")
    for origin in (os.getenv("CHAT_ALLOWED_ORIGINS") or "").split(",")
    if origin.strip()
}
