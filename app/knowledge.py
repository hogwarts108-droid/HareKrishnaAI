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
    # Preprocess: separate letters and digits to catch 'BG1.1' -> 'bg 1.1'
    q_proc = re.sub(r"([a-zA-Z])(?=\d)", r"\1 ", q_lower)
    q_proc = re.sub(r"(?<=\d)([a-zA-Z])", r" \1", q_proc)

    entries = _load_documents()
    if not entries:
        return None

    # PRIORITY 1: Special handling for concept questions (Who is X?)
    if any(x in q_proc for x in ["wer ist", "who is", "कौन है", "क्या है", "what is"]):
        if "krishna" in q_proc:
            for entry in entries:
                src_lower = entry.get("source", "").lower()
                chapter_lower = entry.get("chapter", "").lower()
                if src_lower == "krishna" and chapter_lower == "introduction":
                    return {
                        "source": entry.get("source", "Unbekannt"),
                        "chapter": entry.get("chapter", ""),
                        "verse": entry.get("verse", ""),
                        "sanskrit": entry.get("sanskrit", ""),
                        "translation": entry.get("translation", {}),
                        "explanation": entry.get("explanation", {}),
                    }
        # Look for introduction chapters for other scriptures
        for entry in entries:
            chapter_lower = entry.get("chapter", "").lower()
            if chapter_lower == "introduction" or chapter_lower == "philosophy":
                return {
                    "source": entry.get("source", "Unbekannt"),
                    "chapter": entry.get("chapter", ""),
                    "verse": entry.get("verse", ""),
                    "sanskrit": entry.get("sanskrit", ""),
                    "translation": entry.get("translation", {}),
                    "explanation": entry.get("explanation", {}),
                }

    # Try to parse explicit reference like 'BG 1.1' or 'Bhagavad Gita 2.47' or 'BG1.1'
    alias_map = {
        'bg': 'bhagavad gita', 'gita': 'bhagavad gita', 'bhagavad': 'bhagavad gita',
        'sb': 'srimad bhagavatam', 'bhagavatam': 'srimad bhagavatam', 'srimad bhagavatam': 'srimad bhagavatam',
        'yoga': 'yoga sutra', 'yoga sutra': 'yoga sutra', 'isopanishad': 'sri isopanishad',
    }

    # find all tokens and possible reference numbers
    m_ref = re.search(r"(\b(?:\d+(?:\.\d+)+)\b)", q_proc)
    ref = m_ref.group(1) if m_ref else None

    # find source token
    src_hint = None
    for a in alias_map.keys():
        if re.search(rf"\b{re.escape(a)}\b", q_proc):
            src_hint = alias_map[a]
            break

    # if explicit source and ref present, try exact match
    if src_hint and ref:
        for entry in entries:
            src_norm = _normalize_source(entry.get('source',''))
            if src_hint != src_norm and src_hint not in src_norm:
                continue
            chapter = str(entry.get('chapter') or "").strip()
            verse = str(entry.get('verse') or "").strip()
            entry_ref = f"{chapter}.{verse}" if chapter and verse and verse.lower() != 'full' else ''
            if entry_ref == ref:
                return {
                    'source': entry.get('source','Unbekannt'),
                    'chapter': entry.get('chapter',''),
                    'verse': entry.get('verse',''),
                    'sanskrit': entry.get('sanskrit',''),
                    'translation': entry.get('translation',{}),
                    'explanation': entry.get('explanation',{}),
                }

    # PRIORITY 2: Direct reference matching (Bhagavad Gita 2.47) - improved
    for entry in entries:
        src = _normalize_source(entry.get("source", ""))
        chapter = str(entry.get("chapter") or "")
        verse = str(entry.get("verse") or "")
        if not src:
            continue

        # build variants to match against processed query
        variants = []
        if chapter and verse and verse.lower() != 'full':
            variants.append(f"{src} {chapter}.{verse}")
        if chapter:
            variants.append(f"{src} {chapter}")
        if verse and verse.lower() != 'full':
            variants.append(f"{src} {verse}")
        variants.append(src)

        if any(v and v in q_proc for v in variants):
            return {
                "source": entry.get("source", "Unbekannt"),
                "chapter": entry.get("chapter", ""),
                "verse": entry.get("verse", ""),
                "sanskrit": entry.get("sanskrit", ""),
                "translation": entry.get("translation", {}),
                "explanation": entry.get("explanation", {}),
            }

    # PRIORITY 3: Exact verse reference (2.47, 1.1, etc.) - prefer entries where ref matches and source hint matches if present
    if ref:
        exact_matches = []
        # collect all entries where chapter.verse == ref
        for entry in entries:
            chapter = str(entry.get("chapter") or "").strip()
            verse = str(entry.get("verse") or "").strip()
            entry_ref = f"{chapter}.{verse}" if chapter and verse and verse.lower() != "full" else ""
            if entry_ref == ref:
                exact_matches.append(entry)
        
        if exact_matches:
            # if user provided a source hint, filter to matching source
            if src_hint:
                for match in exact_matches:
                    if src_hint in _normalize_source(match.get('source','')):
                        return {
                            "source": match.get("source", "Unbekannt"),
                            "chapter": match.get("chapter", ""),
                            "verse": match.get("verse", ""),
                            "sanskrit": match.get("sanskrit", ""),
                            "translation": match.get("translation", {}),
                            "explanation": match.get("explanation", {}),
                        }
                # fallback: return first match if no source hint match found
                match = exact_matches[0]
                return {
                    "source": match.get("source", "Unbekannt"),
                    "chapter": match.get("chapter", ""),
                    "verse": match.get("verse", ""),
                    "sanskrit": match.get("sanskrit", ""),
                    "translation": match.get("translation", {}),
                    "explanation": match.get("explanation", {}),
                }
            else:
                # no source hint: prefer Bhagavad Gita, then others
                bhagavad_match = None
                first_match = exact_matches[0]
                for match in exact_matches:
                    if 'bhagavad' in _normalize_source(match.get('source','')):
                        bhagavad_match = match
                        break
                
                chosen = bhagavad_match if bhagavad_match else first_match
                return {
                    "source": chosen.get("source", "Unbekannt"),
                    "chapter": chosen.get("chapter", ""),
                    "verse": chosen.get("verse", ""),
                    "sanskrit": chosen.get("sanskrit", ""),
                    "translation": chosen.get("translation", {}),
                    "explanation": chosen.get("explanation", {}),
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
        ref_line = f"\n📖 Quelle: {chapter}\n📜 Vers: {verse}"
    elif chapter:
        ref_line = f"\n📖 Quelle: {chapter}"
    elif verse:
        ref_line = f"\n📜 Vers: {verse}"

    source = str(entry.get('source',''))
    sanskrit = str(entry.get('sanskrit',''))
    
    text = f"""📖 Quelle: {source}{ref_line}

🕉 Sanskrit:
{sanskrit}

🌍 Übersetzung:
{trans_text}

🪷 Erklärung:
{expl_text}"""
    
    # Add link to full story if this is Krishna Introduction
    if source.lower() == "krishna" and chapter.lower() == "introduction":
        # Get domain for link
        railway_domain = os.getenv('RAILWAY_PUBLIC_DOMAIN', '')
        port = os.getenv('PORT', '0')
        
        if railway_domain and port != '0':
            # On Railway - use public domain
            krishna_url = f"https://{railway_domain}/krishna"
        elif port != '0':
            # On server with PORT but no RAILWAY_PUBLIC_DOMAIN
            krishna_url = f"http://localhost:{port}/krishna"
        else:
            # Local development
            krishna_url = "http://localhost:8001/krishna"
        
        if lang == 'de':
            text += f"\n\n📚 Die vollständige Geschichte:\n{krishna_url}"
        elif lang == 'en':
            text += f"\n\n📚 Read the full story:\n{krishna_url}"
        else:  # Hindi
            text += f"\n\n📚 पूरी कहानी:\n{krishna_url}"
    
    return text


def reload_index() -> int:
    """Quick reload - only refresh entries without rebuilding vectors (much faster)."""
    global _ENTRIES
    try:
        _ENTRIES = _load_documents()
        # Don't rebuild vectors/embeddings - that's expensive
        # Only update on full _build_index() at startup
        return len(_ENTRIES)
    except Exception:
        return 0
