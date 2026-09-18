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
CHAT_ALLOWED_ORIGINS = {
    origin.strip().rstrip("/")
    for origin in (os.getenv("CHAT_ALLOWED_ORIGINS") or "").split(",")
    if origin.strip()
}
