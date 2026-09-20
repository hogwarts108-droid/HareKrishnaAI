"""Shared web-chat orchestration for the Telegram/web application."""

import logging
from typing import Any, Dict, Optional

from openai import OpenAI

from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_TIMEOUT
from app.knowledge import (
    find_answer,
    generate_answer_text,
    generate_local_llm_answer,
    search_entries,
)

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = {"de", "en"}
MAX_MESSAGE_LENGTH = 2000


def _build_rag_context(message: str, entry: Optional[Dict[str, Any]], language: str) -> str:
    """Collect the best matching verse plus extra search hits as AI context."""
    chunks = []
    seen = set()
    if entry:
        reference = " ".join(
            part
            for part in (
                entry.get("source", ""),
                entry.get("chapter", ""),
                entry.get("verse", ""),
            )
            if part
        )
        seen.add(reference.lower())
        rendered = generate_answer_text(message, entry, lang=language)
        chunks.append(f"[Passender Vers aus der Wissensdatenbank: {reference}]\n{rendered}")
    for extra in search_entries(message)[:4]:
        source = extra.get("source", "")
        chapter = extra.get("chapter", "")
        verse = extra.get("verse", "")
        reference = " ".join(part for part in (source, chapter, verse) if part)
        if not reference or reference.lower() in seen:
            continue
        seen.add(reference.lower())
        translation = extra.get("translation", {})
        text = translation.get(language) or translation.get("de") or translation.get("en") or ""
        chunks.append(f"[Weiterer Vers: {reference}]\n{text}")
    return "\n\n".join(chunks)


def generate_ai_answer(message: str, language: str, rag_context: str) -> Optional[str]:
    """Ask a real external AI model, grounding it with the knowledge base if possible."""
    if not LLM_API_KEY:
        return None
    if language == "en":
        system = (
            "You are VedaAmrita, a warm devotional AI of the Hare Krishna / Vaishnava "
            "tradition. Always answer in the same language as the user (English here). "
            "Use the provided verses from the knowledge base as authoritative quotes when "
            "relevant and cite them. If no provided verse fits, answer from general Vedic "
            "wisdom (Bhagavad-gita, Srimad-Bhagavatam) honestly, without inventing exact "
            "verse references. Keep answers warm, clear and concise (max ~300 words), "
            "use simple markdown."
        )
    else:
        system = (
            "Du bist VedaAmrita, eine herzliche, fromme AI der Hare-Krishna-/Vaishnava-"
            "Tradition. Antworte immer in der Sprache des Nutzers (hier Deutsch). Nutze die "
            "gelieferten Verse aus der Wissensdatenbank als maßgebliche Zitate, sofern "
            "passend, und zitiere sie. Wenn kein gelieferter Vers passt, antworte aus "
            "allgemeinem vedischem Wissen (Bhagavad-gita, Srimad-Bhagavatam) ehrlich und "
            "ohne erfundene Versangaben. Bleib warm, klar und prägnant (max. ca. 300 "
            "Wörter), verwende einfaches Markdown."
        )
    try:
        client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL, timeout=LLM_TIMEOUT)
        user_content = rag_context if rag_context else (
            "Es gibt nichts Passendes aus der Wissensdatenbank – antworte aus deinem "
            "allgemeinen Wissen über die Bhagavad-gita und die vedische Weisheit."
        )
        user_content += f"\n\nFrage: {message}"
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            temperature=0.4,
            max_tokens=700,
        )
        answer = response.choices[0].message.content
        return (answer or "").strip() or None
    except Exception:
        logger.exception("External LLM request failed")
        return None


def answer_chat(message: str, language: str = "de") -> Dict[str, Any]:
    """Answer a web chat message using the local model, then the external AI, then the knowledge base."""
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

    rag_context = _build_rag_context(normalized_message, entry, normalized_language)
    ai_answer = generate_ai_answer(normalized_message, normalized_language, rag_context)
    if ai_answer:
        result = {
            "answer": ai_answer,
            "source": "ai",
            "language": normalized_language,
        }
        if entry:
            result["reference"] = {
                "source": entry.get("source", ""),
                "chapter": entry.get("chapter", ""),
                "verse": entry.get("verse", ""),
            }
        return result

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
