"""Shared web-chat orchestration for the Telegram/web application."""

from typing import Any, Dict

from app.knowledge import (
    find_answer,
    generate_answer_text,
    generate_local_llm_answer,
)

SUPPORTED_LANGUAGES = {"de", "en"}
MAX_MESSAGE_LENGTH = 2000


def answer_chat(message: str, language: str = "de") -> Dict[str, Any]:
    """Answer a web chat message using the local model, then the knowledge base."""
    normalized_message = str(message or "").strip()
    normalized_language = str(language or "de").strip().lower()
    if normalized_language not in SUPPORTED_LANGUAGES:
        normalized_language = "de"

    if not normalized_message:
        raise ValueError("message must not be empty")
    if len(normalized_message) > MAX_MESSAGE_LENGTH:
        raise ValueError(f"message must be at most {MAX_MESSAGE_LENGTH} characters")

    entry = find_answer(normalized_message)
    context = None
    if entry:
        context = generate_answer_text(normalized_message, entry, lang=normalized_language)

    model_answer = generate_local_llm_answer(
        normalized_message,
        lang=normalized_language,
        context=context,
    )
    if model_answer:
        return {"answer": model_answer, "source": "model", "language": normalized_language}

    if entry:
        return {
            "answer": context,
            "source": "knowledge_base",
            "language": normalized_language,
            "reference": {
                "source": entry.get("source", ""),
                "chapter": entry.get("chapter", ""),
                "verse": entry.get("verse", ""),
            },
        }

    return {
        "answer": generate_answer_text(normalized_message, None, lang=normalized_language),
        "source": "knowledge_base",
        "language": normalized_language,
    }
