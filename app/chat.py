"""Shared web-chat orchestration for the Telegram/web application."""

import logging
import re
import time as _time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Any, Dict, Optional

from openai import OpenAI

from app.config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_FALLBACK_MODELS,
    LLM_MAX_WAIT,
    LLM_MODEL,
    LLM_TIMEOUT,
)
from app.knowledge import (
    find_answer,
    generate_answer_text,
    generate_local_llm_answer,
    search_entries,
)

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = {"de", "en"}
MAX_MESSAGE_LENGTH = 2000

_COT_PATTERNS = re.compile(
    r"(?i)here('|i)?s?\s+a\s+thinking\s+process|here\s+is\s+my\s+thinking|"
    r"let\s+me\s+think|let'?s\s+think|shall\s+we\s+think|ich\s+überlege|"
    r"gedankenprozess|chain\s+of\s+thought|reasoning\s+process|"
    r"analy[sz]e\s+(the\s+)?user\s+input|anal[ys]es?e\s+der\s+eingabe|"
    r"^1\.\s+analy[sz]e|^schritt\s*1:|^step\s*1:"
)


def _looks_like_chain_of_thought(text: str) -> bool:
    """Reject model output that is an exposed reasoning chain, not an answer."""
    return bool(_COT_PATTERNS.search(text or ""))


_GREETING_PATTERNS = re.compile(
    r"(?i)^(hare|jay|jai|om)\b|^(hallo|hello|hi|hey|namaste|namaskar)\b|"
    r"^(guten\s+(morgen|tag|abend)|good\s+(morning|afternoon|evening))\b|"
    r"\bhare\s+krishna\b|\bjay\s+srila\b"
)

_GREETINGS = {
    "de": (
        "🙏 Hare Krishna! Schön, dass du da bist.\n\n"
        "Ich bin VedaAmrita – dein kleiner Seelenfreund aus der vedischen Tradition. "
        "Frag mich alles über die *Bhagavad-gita*, *Srimad-Bhagavatam*, Karma, Reinkarnation "
        "oder das Mantra. Wie kann ich dir heute dienen?"
    ),
    "en": (
        "🙏 Hare Krishna! So nice to have you here.\n\n"
        "I am VedaAmrita, your little soul-friend from the Vedic tradition. "
        "Ask me anything about the *Bhagavad-gita*, *Srimad-Bhagavatam*, karma, reincarnation "
        "or the mantra. How may I serve you today?"
    ),
}


def _greeting_for(message: str, language: str) -> Optional[str]:
    """Return an instant warm greeting for pure greetings so the user never waits."""
    if len(message) > 120:
        return None
    if _GREETING_PATTERNS.search(message):
        return _GREETINGS.get(language, _GREETINGS["de"])
    return None


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
            "verse references. Keep answers warm, clear and very short (max ~120 words), "
            "use simple markdown."
        )
    else:
        system = (
            "Du bist VedaAmrita, eine herzliche, fromme AI der Hare-Krishna-/Vaishnava-"
            "Tradition. Antworte immer in der Sprache des Nutzers (hier Deutsch). Nutze die "
            "gelieferten Verse aus der Wissensdatenbank als maßgebliche Zitate, sofern "
            "passend, und zitiere sie. Wenn kein gelieferter Vers passt, antworte aus "
            "allgemeinem vedischem Wissen (Bhagavad-gita, Srimad-Bhagavatam) ehrlich und "
            "ohne erfundene Versangaben. Bleib warm, klar und sehr kurz (max. ca. 120 "
            "Wörter), verwende einfaches Markdown."
        )
    user_content = rag_context if rag_context else (
        "Es gibt nichts Passendes aus der Wissensdatenbank – antworte aus deinem "
        "allgemeinen Wissen über die Bhagavad-gita und die vedische Weisheit."
    )
    user_content += f"\n\nFrage: {message}"
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(_request_llm, system, user_content)
    try:
        return future.result(timeout=LLM_MAX_WAIT)
    except FutureTimeoutError:
        logger.warning("LLM answer exceeded budget of %.1fs, using knowledge base", LLM_MAX_WAIT)
        executor.shutdown(wait=False)
        return None
    except Exception:
        logger.exception("External LLM request failed")
        executor.shutdown(wait=False)
        return None
    finally:
        executor.shutdown(wait=False)


def _request_llm(system: str, user_content: str) -> Optional[str]:
    """Try the configured model, then fallbacks (called in a bounded thread)."""
    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL, timeout=LLM_TIMEOUT, max_retries=1)
    for model in [LLM_MODEL] + LLM_FALLBACK_MODELS:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.3,
                max_tokens=400,
            )
            answer = response.choices[0].message.content
            if answer and answer.strip():
                if _looks_like_chain_of_thought(answer):
                    logger.warning("LLM model %s returned chain-of-thought, skipping it", model)
                    _time.sleep(0.6)
                    continue
                return answer.strip()
        except Exception as exc:
            logger.warning("LLM model %s failed: %s", model, exc)
            _time.sleep(0.6)
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

    greeting = _greeting_for(normalized_message, normalized_language)
    if greeting:
        return {"answer": greeting, "source": "greeting", "language": normalized_language}

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
