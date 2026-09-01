import json
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = Path(BASE_DIR / "data" / "scriptures")

# Import database
from app.database import get_all_knowledge, insert_knowledge as db_insert_knowledge

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import linear_kernel
except Exception:
    TfidfVectorizer = None
    linear_kernel = None

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    _SENTENCE_MODEL = SentenceTransformer('all-MiniLM-L6-v2')
except Exception:
    SentenceTransformer = None
    np = None
    _SENTENCE_MODEL = None

try:
    import openai
except Exception:
    openai = None

import os
_LAST_INDEX_MTIME = 0.0
_OBSERVER = None

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

    class _KBChangeHandler(FileSystemEventHandler):
        def on_any_event(self, event):
            # Rebuild index on any change event
            try:
                _build_index()
            except Exception:
                pass

    def _start_watcher():
        global _OBSERVER
        if _OBSERVER is not None:
            return
        try:
            handler = _KBChangeHandler()
            obs = Observer()
            obs.schedule(handler, str(KNOWLEDGE_DIR), recursive=True)
            obs.daemon = True
            obs.start()
            _OBSERVER = obs
        except Exception:
            _OBSERVER = None
except Exception:
    Observer = None
    FileSystemEventHandler = None
    def _start_watcher():
        return


def _normalize_source(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    tokens = re.sub(r"[^a-zA-Z0-9]+", " ", text.lower()).split()
    if not tokens:
        return ""
    return " ".join(tokens)


def _normalize_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(entry, dict):
        return entry
    source = str(entry.get("source") or "")
    chapter = str(entry.get("chapter") or "")
    verse = str(entry.get("verse") or "")

    if not chapter and isinstance(verse, str) and re.search(r"^\d+(?:\.\d+)+$", verse.strip()):
        parts = verse.strip().split(".")
        if len(parts) >= 2:
            chapter = parts[0]
            verse = ".".join(parts[1:]) if len(parts) > 2 else parts[1]
            entry["chapter"] = chapter
            entry["verse"] = verse
    if chapter and not verse:
        entry["verse"] = chapter
        entry["chapter"] = chapter

    if "reference" not in entry:
        ref_parts = []
        if source:
            ref_parts.append(str(source))
        if chapter:
            ref_parts.append(str(chapter))
        if verse and verse.lower() != "full":
            ref_parts.append(str(verse))
        entry["reference"] = " ".join(ref_parts)

    return entry


def _load_documents() -> List[Dict[str, Any]]:
    """Load documents from JSON files and database."""
    entries: List[Dict[str, Any]] = []
    
    # Load from JSON files
    if KNOWLEDGE_DIR.exists():
        for path in KNOWLEDGE_DIR.rglob("*.json"):
            try:
                text = path.read_text(encoding="utf-8")
                data = json.loads(text)
                if isinstance(data, dict):
                    entries.append(_normalize_entry(data))
                elif isinstance(data, list):
                    entries.extend([_normalize_entry(e) for e in data if isinstance(e, dict)])
            except Exception:
                continue
    
    # Also try to load from database
    try:
        db_entries = get_all_knowledge()
        entries.extend(db_entries)
    except Exception:
        pass
    
    return entries


def _entry_to_corpus_text(entry: Dict[str, Any]) -> str:
    parts = [
        entry.get("source", ""),
        entry.get("chapter", ""),
        entry.get("verse", ""),
        entry.get("sanskrit", ""),
    ]
    trans = entry.get("translation") or {}
    expl = entry.get("explanation") or {}
    parts.append(" ".join(str(v) for v in trans.values() if isinstance(v, str)))
    parts.append(" ".join(str(v) for v in expl.values() if isinstance(v, str)))
    return " \n ".join([p for p in parts if p])


# Global index
_ENTRIES: List[Dict[str, Any]] = []
_VECTORIZER = None
_MATRIX = None
_EMBEDDINGS = None


def _build_index():
    global _ENTRIES, _VECTORIZER, _MATRIX
    _ENTRIES = _load_documents()
    if not _ENTRIES or TfidfVectorizer is None:
        _VECTORIZER = None
        _MATRIX = None
        return

    corpus = [_entry_to_corpus_text(e) for e in _ENTRIES]
    _VECTORIZER = TfidfVectorizer(stop_words='english')
    try:
        _MATRIX = _VECTORIZER.fit_transform(corpus)
    except Exception:
        _VECTORIZER = None
        _MATRIX = None

    # build embeddings if available
    global _EMBEDDINGS
    _EMBEDDINGS = None
    if _SENTENCE_MODEL is not None and np is not None:
        try:
            _EMBEDDINGS = _SENTENCE_MODEL.encode(corpus, convert_to_numpy=True)
        except Exception:
            _EMBEDDINGS = None



_build_index()

# Start watcher to auto-rebuild index when files change
try:
    _start_watcher()
except Exception:
    pass


def _query_exact_reference_matches(question: str) -> Optional[Dict[str, Any]]:
    q = (question or "").strip()
    if not q:
        return None

    q_lower = q.lower()
    entries = _load_documents()
    if not entries:
        return None

    # Priority 1: Special handling for Krishna Introduction
    if "krishna" in q_lower and ("introduction" in q_lower or "who_is" in q_lower):
        for entry in entries:
            src_lower = entry.get("source", "").lower()
            chapter_lower = entry.get("chapter", "").lower()
            if (src_lower == "krishna" and chapter_lower == "introduction"):
                return {
                    "source": entry.get("source", "Unbekannt"),
                    "chapter": entry.get("chapter", ""),
                    "verse": entry.get("verse", ""),
                    "sanskrit": entry.get("sanskrit", ""),
                    "translation": entry.get("translation", {}),
                    "explanation": entry.get("explanation", {}),
                }

    # Priority 2: Standard reference matching
    patterns = []
    for token in ["bg", "gita", "bhagavad gita", "yoga sutra", "yogasutra", "isopanishad", "sri isopanishad", "srimad bhagavatam", "bhagavatam", "krishna"]:
        if token in q_lower:
            patterns.append(token)

    for entry in entries:
        src = _normalize_source(entry.get("source", ""))
        chapter = str(entry.get("chapter") or "")
        verse = str(entry.get("verse") or "")
        if not src:
            continue

        candidates = [
            f"{src} {chapter}.{verse}" if chapter and verse and verse.lower() != "full" else "",
            f"{src} {chapter}" if chapter else "",
            f"{src} {verse}" if verse and verse.lower() != "full" else "",
            src,
        ]
        if any(c and c in q_lower for c in candidates):
            return {
                "source": entry.get("source", "Unbekannt"),
                "chapter": entry.get("chapter", ""),
                "verse": entry.get("verse", ""),
                "sanskrit": entry.get("sanskrit", ""),
                "translation": entry.get("translation", {}),
                "explanation": entry.get("explanation", {}),
            }

    for entry in entries:
        chapter = str(entry.get("chapter") or "")
        verse = str(entry.get("verse") or "")
        entry_ref = f"{chapter}.{verse}" if chapter and verse and verse.lower() != "full" else ""
        if entry_ref and entry_ref in q_lower:
            return {
                "source": entry.get("source", "Unbekannt"),
                "chapter": entry.get("chapter", ""),
                "verse": entry.get("verse", ""),
                "sanskrit": entry.get("sanskrit", ""),
                "translation": entry.get("translation", {}),
                "explanation": entry.get("explanation", {}),
            }

    return None


def find_answer(question: str) -> Optional[Dict[str, Any]]:
    question = (question or "").strip()
    if not question:
        return None

    direct = _query_exact_reference_matches(question)
    if direct:
        return direct

    # rebuild index if files changed
    global _LAST_INDEX_MTIME
    try:
        mtime = max(p.stat().st_mtime for p in KNOWLEDGE_DIR.rglob('*.json')) if KNOWLEDGE_DIR.exists() else 0
    except Exception:
        mtime = 0
    if mtime and mtime != _LAST_INDEX_MTIME:
        _LAST_INDEX_MTIME = mtime
        _build_index()

    # Use embeddings if available
    if _EMBEDDINGS is not None and _SENTENCE_MODEL is not None and np is not None:
        try:
            q_emb = _SENTENCE_MODEL.encode([question], convert_to_numpy=True)
            sims = np.inner(q_emb, _EMBEDDINGS).flatten()
            best_idx = int(sims.argmax())
            best_score = float(sims[best_idx])
            if best_score > 0.2:
                best = _ENTRIES[best_idx]
                return {
                    "source": best.get("source", "Unbekannt"),
                    "chapter": best.get("chapter", ""),
                    "verse": best.get("verse", ""),
                    "sanskrit": best.get("sanskrit", ""),
                    "translation": best.get("translation", {}),
                    "explanation": best.get("explanation", {}),
                }
        except Exception:
            pass

    # Use TF-IDF if available
    if _VECTORIZER is not None and _MATRIX is not None and linear_kernel is not None:
        try:
            qv = _VECTORIZER.transform([question])
            sims = linear_kernel(qv, _MATRIX).flatten()
            best_idx = int(sims.argmax())
            best_score = float(sims[best_idx])
            if best_score > 0.05:
                best = _ENTRIES[best_idx]
                return {
                    "source": best.get("source", "Unbekannt"),
                    "chapter": best.get("chapter", ""),
                    "verse": best.get("verse", ""),
                    "sanskrit": best.get("sanskrit", ""),
                    "translation": best.get("translation", {}),
                    "explanation": best.get("explanation", {}),
                }
        except Exception:
            pass

    # Fallback simple keyword matching
    entries = _load_documents()
    if not entries:
        return None

    keywords = re.findall(r"\w+", question.lower())
    if not keywords:
        return None

    best = None
    best_score = 0
    for entry in entries:
        joined = _entry_to_corpus_text(entry).lower()
        score = sum(1 for kw in keywords if kw in joined)
        if score > best_score:
            best_score = score
            best = entry

    if best and best_score > 0:
        return {
            "source": best.get("source", "Unbekannt"),
            "chapter": best.get("chapter", ""),
            "verse": best.get("verse", ""),
            "sanskrit": best.get("sanskrit", ""),
            "translation": best.get("translation", {}),
            "explanation": best.get("explanation", {}),
        }

    return None


def generate_answer_text(question: str, entry: Dict[str, Any], lang: str = 'de') -> str:
    """Generate a polished answer using OpenAI if available, otherwise format from the entry."""
    if not entry:
        return (
            "🙏 Hare Krishna!\n\n"
            "Ich habe dazu noch keinen passenden Vers in meiner Datenbank."
        )

    translation = entry.get('translation', {})
    explanation = entry.get('explanation', {})
    trans_text = translation.get(lang) or translation.get('de') or translation.get('en') or ''
    expl_text = explanation.get(lang) or explanation.get('de') or explanation.get('en') or ''

    # If OpenAI available and API key present, call to generate a concise answer
    if openai is not None and os.getenv('OPENAI_API_KEY'):
        try:
            openai.api_key = os.getenv('OPENAI_API_KEY')
            prompt = (
                f"Question: {question}\n\n"
                f"Source: {entry.get('source','')}\nVerse: {entry.get('verse','')}\n"
                f"Sanskrit: {entry.get('sanskrit','')}\nTranslation: {trans_text}\nExplanation: {expl_text}\n\n"
                "Bitte antworte auf Deutsch kurz und bestimmt (assertiv), nenne die Quelle und den Vers." 
            )
            resp = openai.ChatCompletion.create(
                model='gpt-3.5-turbo',
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.2,
            )
            ans = resp['choices'][0]['message']['content'].strip()
            return ans
        except Exception:
            pass

    chapter = entry.get('chapter') or ''
    verse = entry.get('verse') or ''
    ref_line = ""
    if chapter and verse and str(verse).lower() != 'full':
        ref_line = f"\n📖 Kapitel: {chapter}\n📜 Vers: {verse}"
    elif chapter:
        ref_line = f"\n📖 Kapitel: {chapter}"
    elif verse:
        ref_line = f"\n📜 Vers: {verse}"

    text = (
        "📖 Quelle: " + str(entry.get('source','')) +
        ref_line +
        "\n\n🕉 Sanskrit:\n" + str(entry.get('sanskrit','')) +
        "\n\n🌍 Übersetzung:\n" + trans_text +
        "\n\n🪷 Erklärung:\n" + expl_text
    )
    return text


def reload_index() -> int:
    """Public function to rebuild the in-memory index and return number of entries."""
    try:
        _build_index()
        return len(_ENTRIES)
    except Exception:
        return 0
