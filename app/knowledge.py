import json
import re
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = Path(BASE_DIR / "data" / "scriptures")

# Import database
from app.database import get_all_knowledge, insert_knowledge as db_insert_knowledge

# Fuzzy matching library
try:
    from difflib import SequenceMatcher
except Exception:
    SequenceMatcher = None

try:
    from fuzzywuzzy import fuzz
except Exception:
    fuzz = None

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import linear_kernel
except Exception:
    TfidfVectorizer = None
    linear_kernel = None

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    # Loading the transformer during import blocks Railway's health check.
    # The lightweight TF-IDF index remains available immediately.
    _SENTENCE_MODEL = None
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

    # If verse already contains dots (e.g., "1.3" or "1.2.6"), it's a full reference
    # Don't split it again - just clear redundant chapter
    if verse and re.match(r"^\d+\.", verse):
        # verse is already full reference, ignore chapter
        chapter = ""
    # Only split verse if it doesn't already have chapter embedded
    elif not chapter and isinstance(verse, str) and re.search(r"^\d+(?:\.\d+)+$", verse.strip()):
        parts = verse.strip().split(".")
        if len(parts) >= 2:
            chapter = parts[0]
            verse = ".".join(parts[1:]) if len(parts) > 2 else parts[1]
            entry["chapter"] = chapter
            entry["verse"] = verse
    elif chapter and not verse:
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

    # PRIORITY 1: Match "Who is X?" to the named introduction, never the
    # first introduction in the data set.
    concept_markers = ["wer ist", "who is", "कौन है", "क्या है", "what is"]
    if any(marker in q_proc for marker in concept_markers):
        question_without_marker = q_proc
        for marker in concept_markers:
            question_without_marker = question_without_marker.replace(marker, " ")
        question_without_marker = re.sub(r"[?!.,;:]", " ", question_without_marker)
        requested_name = " ".join(question_without_marker.split()).strip()

        # Prefer exact source names, then normalized aliases such as "baladeva".
        aliases = {
            "baladeva": "balarama",
            "balaji": "balarama",
            "govinda": "krishna",
            "madhava": "krishna",
        }
        requested_name = aliases.get(requested_name, requested_name)
        for entry in entries:
            if str(entry.get("chapter", "")).lower() not in {"introduction", "philosophy"}:
                continue
            source = str(entry.get("source", "")).strip()
            source_normalized = _normalize_source(source)
            if requested_name and (
                requested_name == source_normalized
                or requested_name in source_normalized
                or source_normalized in requested_name
            ):
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


def _normalize_query(question: str) -> str:
    """Normalize query to handle common misspellings and alternatives."""
    q = question.lower()
    
    # Common alternative spellings
    replacements = {
        "krisha": "krishna",
        "krisna": "krishna",
        "krishna gita": "bhagavad gita",
        "arjun": "arjuna",
        "arjun": "arjuna",
        "radha": "radha",
        "raadha": "radha",
        "yogaa sutra": "yoga sutra",
        "bagavad": "bhagavad",
        "bhagwad": "bhagavad",
        "gita": "bhagavad gita",
        "upanishad": "isopanishad",
        "isopanisad": "isopanishad",
        "bhagavatam": "srimad bhagavatam",
        "bhagavat": "srimad bhagavatam",
        "charitra": "chaitanya charitamrita",
        "chaitanya": "chaitanya charitamrita",
    }
    
    # Apply replacements
    for wrong, correct in replacements.items():
        if wrong in q:
            q = q.replace(wrong, correct)
    
    return q


def find_answer(question: str) -> Optional[Dict[str, Any]]:
    # Normalize query for better matching
    normalized_q = _normalize_query(question)
    
    question = (question or "").strip()
    if not question:
        return None

    direct = _query_exact_reference_matches(question)
    if direct:
        return direct
    
    # Try again with normalized version if it's different
    if normalized_q != question.lower():
        direct = _query_exact_reference_matches(normalized_q)
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


def suggest_corrections(question: str) -> List[Tuple[str, float]]:
    """Suggest corrections for misspelled or unclear queries using fuzzy matching."""
    q_lower = question.lower().strip()
    entries = _load_documents()
    if not entries:
        return []
    
    suggestions = []
    
    # Collect all searchable terms
    searchable_terms = set()
    for entry in entries:
        # Add source names
        if entry.get("source"):
            searchable_terms.add(entry.get("source", "").lower())
        # Add chapter names
        if entry.get("chapter") and entry.get("chapter").lower() not in ["introduction", "philosophy", "full"]:
            searchable_terms.add(entry.get("chapter", "").lower())
    
    # Add common scripture abbreviations
    common_terms = {
        "bhagavad gita": 0.95,
        "yoga sutra": 0.95,
        "srimad bhagavatam": 0.95,
        "sri isopanishad": 0.95,
        "chaitanya charitamrita": 0.95,
        "krishna": 0.95,
        "arjuna": 0.90,
        "radha": 0.90,
        "shiva": 0.90,
        "brahma": 0.90,
        "vishnu": 0.90,
    }
    
    searchable_terms.update(common_terms.keys())
    
    # Use fuzzy matching if available
    if fuzz:
        for term in searchable_terms:
            score = fuzz.token_set_ratio(q_lower, term) / 100.0
            if score > 0.6:  # Only suggest if >60% match
                suggestions.append((term, score))
    else:
        # Fallback: use simple SequenceMatcher
        for term in searchable_terms:
            ratio = SequenceMatcher(None, q_lower, term).ratio()
            if ratio > 0.6:
                suggestions.append((term, ratio))
    
    # Sort by score descending
    suggestions.sort(key=lambda x: x[1], reverse=True)
    return suggestions[:3]  # Return top 3


def _load_media_resources() -> Dict[str, Any]:
    """Load media resources (images, videos, audio) for figures and scriptures."""
    media_file = KNOWLEDGE_DIR / "media_resources.json"
    if not media_file.exists():
        return {}
    try:
        with open(media_file, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _get_media_for_source(source: str) -> Dict[str, Any]:
    """Get media resources for a specific figure or scripture."""
    media_db = _load_media_resources()
    source_lower = source.lower()
    
    # Check figures
    figures = media_db.get('figures', {})
    for fig_name, fig_media in figures.items():
        if fig_name.lower() == source_lower:
            return fig_media
    
    # Check scriptures
    scriptures = media_db.get('scriptures', {})
    for script_name, script_media in scriptures.items():
        if script_name.lower() == source_lower:
            return script_media
    
    return {}


def generate_answer_text(question: str, entry: Dict[str, Any], lang: str = 'de') -> str:
    """Generate a beautifully formatted answer with proper Markdown structure."""
    if not entry:
        if lang == 'de':
            return (
                "🙏 *Hare Krishna!*\n\n"
                "Ich habe dazu noch keinen passenden Vers in meiner Datenbank. "
                "Versuche es mit einem anderen Begriff oder einer bekannten Schrift wie *Bhagavad Gita 2.47*"
            )
        elif lang == 'en':
            return (
                "🙏 *Hare Krishna!*\n\n"
                "I don't have a matching verse in my database yet. "
                "Try a different term or a famous scripture like *Bhagavad Gita 2.47*"
            )
        else:  # Hindi
            return (
                "🙏 *हरे कृष्ण!*\n\n"
                "मेरे पास इसके लिए कोई मिलान वाली श्लोक नहीं है। "
                "एक अलग शब्द का प्रयास करें या *भगवद गीता 2.47* जैसे एक प्रसिद्ध शास्त्र का प्रयास करें"
            )

    source = str(entry.get('source', ''))
    chapter = str(entry.get('chapter') or '')
    verse = str(entry.get('verse') or '')
    sanskrit = str(entry.get('sanskrit', ''))
    
    translation = entry.get('translation', {})
    explanation = entry.get('explanation', {})
    trans_text = translation.get(lang) or translation.get('de') or translation.get('en') or ''
    expl_text = explanation.get(lang) or explanation.get('de') or explanation.get('en') or ''

    # Build reference string
    if chapter and verse and verse.lower() != 'full':
        if '.' in str(verse):
            # verse is already "1.3" format
            ref_str = f"{source} {verse}"
        else:
            ref_str = f"{source} {chapter}.{verse}"
    elif chapter:
        ref_str = f"{source} - {chapter}"
    else:
        ref_str = source

    # Determine content type for better formatting
    is_introduction = chapter.lower() == 'introduction' if chapter else False
    
    # Build response with improved Markdown formatting
    lines = []
    
    # Header with emojis and reference
    if is_introduction:
        lines.append(f"✨ *{source}* ✨")
    else:
        lines.append(f"📖 *{ref_str}*")
    
    lines.append("")  # Blank line
    
    # Sanskrit section with code block
    if sanskrit:
        lines.append("*🕉 Sanskrit:*")
        lines.append(f"`{sanskrit}`")
        lines.append("")
    
    # Translation section with emphasis
    if trans_text:
        lines.append("*🌍 Übersetzung:*")
        lines.append(trans_text)
        lines.append("")
    
    # Explanation section
    if expl_text:
        lines.append("*📚 Erklärung:*")
        lines.append(expl_text)
        lines.append("")
    
    text = "\n".join(lines)
    
    # Add a conversational interpretation based on the matched figure.
    if is_introduction:
        figure_insights = {
            "balarama": {
                "de": "Kurz gesagt: Balarama ist nicht Krishna, sondern sein älterer Bruder und eine eigenständige zentrale Gestalt der Krishna-Tradition.",
                "en": "In short: Balarama is not Krishna, but his elder brother and a distinct central figure in the Krishna tradition.",
                "hi": "संक्षेप में: बलराम कृष्ण नहीं हैं, बल्कि उनके बड़े भाई और कृष्ण परंपरा के एक प्रमुख स्वतंत्र व्यक्तित्व हैं।",
            },
            "radha": {
                "de": "Radha steht für die vollkommen persönliche Form der Bhakti. Ihre Beziehung zu Krishna wird als Liebe verstanden, in der Hingabe wichtiger ist als eigener Vorteil.",
                "en": "Radha represents the most intimate form of bhakti. Her relationship with Krishna shows devotion that seeks no personal reward.",
                "hi": "राधा भक्ति के सबसे अंतरंग रूप का प्रतिनिधित्व करती हैं। कृष्ण के साथ उनका संबंध ऐसी भक्ति दिखाता है जिसमें अपना लाभ नहीं, समर्पण प्रधान है।",
            },
            "krishna": {
                "de": "Kurz gesagt: Krishna steht im Mittelpunkt dieser Überlieferungen als Lehrer der Bhagavad Gita und als zentrale göttliche Gestalt.",
                "en": "In short: Krishna is central to these traditions as the teacher of the Bhagavad Gita and a principal divine figure.",
                "hi": "संक्षेप में: कृष्ण इन परंपराओं के केंद्र में हैं—वे भगवद्गीता के शिक्षक और प्रमुख दिव्य व्यक्तित्व हैं।",
            },
            "arjuna": {
                "de": "Die Verbindung zur Bhagavad Gita ist entscheidend: Arjuna stellt die Fragen, durch die Krishna seine Lehren entfaltet.",
                "en": "The connection to the Bhagavad Gita is essential: Arjuna asks the questions through which Krishna unfolds his teachings.",
                "hi": "भगवद्गीता से उनका संबंध अत्यंत महत्वपूर्ण है: अर्जुन के प्रश्नों के माध्यम से कृष्ण अपनी शिक्षाएँ प्रकट करते हैं।",
            },
            "devaki": {
                "de": "Devakis Rolle zeigt, dass die Krishna-Geschichte auch von Schutz, Leid und Vertrauen handelt: Trotz Kamsas Verfolgung bewahrte sie ihre Hoffnung.",
                "en": "Devaki's role shows that Krishna's story is also about protection, suffering, and trust: she kept hope despite Kamsa's persecution.",
                "hi": "देवकी की भूमिका दिखाती है कि कृष्ण की कथा संरक्षण, पीड़ा और विश्वास की भी कथा है; कंस के अत्याचार के बावजूद उन्होंने आशा बनाए रखी।",
            },
            "vasudeva": {
                "de": "Vasudeva verkörpert mutige Verantwortung. Seine Flucht mit dem neugeborenen Krishna verbindet praktische Handlung mit tiefem Vertrauen in das Göttliche.",
                "en": "Vasudeva embodies courageous responsibility. Carrying the newborn Krishna to safety joins decisive action with deep trust in the Divine.",
                "hi": "वसुदेव साहसी जिम्मेदारी का प्रतीक हैं। नवजात कृष्ण को सुरक्षित ले जाना निर्णायक कर्म और ईश्वर में गहरे विश्वास को जोड़ता है।",
            },
            "kamsa": {
                "de": "Kamsa ist mehr als ein einfacher Bösewicht: Seine Angst vor der Prophezeiung zeigt, wie Furcht Macht in Grausamkeit und Kontrolle verwandeln kann.",
                "en": "Kamsa is more than a simple villain: his fear of the prophecy shows how fear can turn power into cruelty and control.",
                "hi": "कंस केवल एक खलनायक नहीं हैं; भविष्यवाणी का उनका भय दिखाता है कि डर सत्ता को क्रूरता और नियंत्रण में बदल सकता है।",
            },
            "nanda": {
                "de": "Nanda zeigt die menschliche Seite der Krishna-Geschichte: Seine väterliche Liebe macht Bhakti im Alltag als Fürsorge und Verantwortung sichtbar.",
                "en": "Nanda shows the human side of Krishna's story: his fatherly love makes bhakti visible through everyday care and responsibility.",
                "hi": "नंद कृष्ण-कथा का मानवीय पक्ष दिखाते हैं; उनका पितृ प्रेम दैनिक सेवा और जिम्मेदारी के रूप में भक्ति को प्रकट करता है।",
            },
            "yasoda": {
                "de": "Yasoda verkörpert Vatsalya-Bhakti, die Liebe einer Mutter. Ihre Beziehung zu Krishna zeigt, dass Hingabe auch vertraut, direkt und fürsorglich sein kann.",
                "en": "Yasoda embodies vatsalya-bhakti, the love of a mother. Her relationship with Krishna shows that devotion can also be intimate, direct, and caring.",
                "hi": "यशोदा वात्सल्य-भक्ति, अर्थात माता के प्रेम, का प्रतीक हैं। उनका कृष्ण से संबंध दिखाता है कि भक्ति आत्मीय, सरल और स्नेहमयी भी हो सकती है।",
            },
            "indra": {
                "de": "Indras Geschichte mit Govardhana lehrt Demut: Äußere Macht und Rang sind weniger wichtig als Respekt vor der Hingabe und dem Schutz der Gemeinschaft.",
                "en": "Indra's Govardhana story teaches humility: status and power matter less than honoring devotion and protecting the community.",
                "hi": "गोवर्धन की इंद्र-कथा विनम्रता सिखाती है: पद और शक्ति से अधिक महत्वपूर्ण भक्ति का सम्मान और समुदाय की रक्षा है।",
            },
            "brahma": {
                "de": "Brahma steht für kosmische Schöpfung und Wissen. In den Krishna-Erzählungen lernt er zugleich, dass intellektuelle Macht Demut vor dem Göttlichen braucht.",
                "en": "Brahma represents cosmic creation and knowledge. Krishna's stories also teach him that intellectual power requires humility before the Divine.",
                "hi": "ब्रह्मा सृष्टि और ज्ञान के प्रतीक हैं। कृष्ण की कथाएँ यह भी सिखाती हैं कि बौद्धिक शक्ति को ईश्वर के सामने विनम्रता चाहिए।",
            },
            "vishnu": {
                "de": "Vishnu verkörpert den Schutz der kosmischen Ordnung. Seine Avatare zeigen das Grundmotiv, dass Dharma wiederhergestellt wird, wenn Unrecht übermächtig wird.",
                "en": "Vishnu represents the preservation of cosmic order. His avatars express the principle that dharma is restored when injustice becomes dominant.",
                "hi": "विष्णु ब्रह्मांडीय व्यवस्था की रक्षा के प्रतीक हैं। उनके अवतार दिखाते हैं कि अन्याय बढ़ने पर धर्म की पुनः स्थापना होती है।",
            },
            "shiva": {
                "de": "Shiva steht für Transformation, Meditation und Loslassen. Zerstörung bedeutet hier nicht nur Ende, sondern auch den Raum für Erneuerung.",
                "en": "Shiva represents transformation, meditation, and letting go. Destruction here is not only an ending, but also space for renewal.",
                "hi": "शिव परिवर्तन, ध्यान और त्याग के प्रतीक हैं। यहाँ विनाश केवल अंत नहीं, बल्कि नवीनीकरण के लिए स्थान भी है।",
            },
            "gopis": {
                "de": "Die Gopis stehen gemeinsam für eine Beziehung zum Göttlichen, die von spontaner, selbstloser Liebe geprägt ist. Deshalb gelten sie als starkes Bhakti-Symbol.",
                "en": "The Gopis collectively represent a relationship with the Divine shaped by spontaneous, selfless love, which is why they are a central symbol of bhakti.",
                "hi": "गोपियाँ ईश्वर के साथ सहज और निःस्वार्थ प्रेमपूर्ण संबंध का सामूहिक प्रतीक हैं; इसलिए वे भक्ति का महत्वपूर्ण आदर्श मानी जाती हैं।",
            },
            "vyasa": {
                "de": "Vyasa ist nicht nur ein Autor, sondern ein Bewahrer von Wissen. Seine Arbeit verbindet mündliche Überlieferung, Ordnung und Weitergabe spiritueller Lehren.",
                "en": "Vyasa is not only an author but a preserver of knowledge. His work connects oral tradition, organization, and the transmission of spiritual teachings.",
                "hi": "व्यास केवल लेखक नहीं, बल्कि ज्ञान के संरक्षक हैं। उनका कार्य मौखिक परंपरा, व्यवस्था और आध्यात्मिक शिक्षाओं के प्रसार को जोड़ता है।",
            },
            "valmiki": {
                "de": "Valmiki zeigt die Kraft spiritueller Wandlung und dichterischer Erkenntnis. Das Ramayana macht durch seine Erzählung Dharma menschlich und nachvollziehbar.",
                "en": "Valmiki represents spiritual transformation and poetic insight. Through the Ramayana, he makes dharma human and understandable.",
                "hi": "वाल्मीकि आध्यात्मिक परिवर्तन और काव्यात्मक अंतर्दृष्टि के प्रतीक हैं। रामायण के माध्यम से वे धर्म को मानवीय और समझने योग्य बनाते हैं।",
            },
            "putana": {
                "de": "Putanas Geschichte gehört zu den frühen Prüfungen Krishnas. Sie zeigt in der Erzähltradition den Gegensatz zwischen täuschender Gefahr und göttlichem Schutz.",
                "en": "Putana's story is one of Krishna's early trials. In the tradition, it contrasts deceptive danger with divine protection.",
                "hi": "पुतना की कथा कृष्ण की प्रारंभिक परीक्षाओं में से एक है। परंपरा में यह छलपूर्ण खतरे और दिव्य संरक्षण का अंतर दिखाती है।",
            },
            "hiranyakashipu": {
                "de": "Hiranyakashipu verkörpert den Versuch, durch Macht und vermeintliche Unbesiegbarkeit jede Transzendenz zu beherrschen. Seine Geschichte stellt Ego der Hingabe gegenüber.",
                "en": "Hiranyakashipu embodies the attempt to control transcendence through power and supposed invulnerability. His story places ego against devotion.",
                "hi": "हिरण्यकशिपु शक्ति और अजेयता के अहंकार से दिव्यता को नियंत्रित करना चाहते हैं। उनकी कथा अहंकार और भक्ति का विरोध दिखाती है।",
            },
            "prahlada": {
                "de": "Prahlada steht für innere Standhaftigkeit. Seine Bhakti hängt nicht von seiner Umgebung ab und bleibt selbst unter Druck friedlich und vertrauensvoll.",
                "en": "Prahlada represents inner steadfastness. His bhakti does not depend on his surroundings and remains peaceful and trusting under pressure.",
                "hi": "प्रह्लाद आंतरिक दृढ़ता के प्रतीक हैं। उनकी भक्ति परिस्थितियों पर निर्भर नहीं रहती और दबाव में भी शांत और विश्वासपूर्ण बनी रहती है।",
            },
        }
        insight = figure_insights.get(source.lower(), {}).get(lang)
        if insight:
            heading = "Einordnung" if lang == "de" else "Context" if lang == "en" else "संदर्भ"
            text += f"\n\n*💡 {heading}:*\n{insight}"

        # Add helpful tip
        if lang == 'de':
            text += "\n\n💡 _Tipp: Schreib eine Figur (z.B. 'Radha', 'Arjuna') für mehr Infos._"
        elif lang == 'en':
            text += "\n\n💡 _Tip: Write a character name (e.g., 'Radha', 'Arjuna') for more info._"
        else:
            text += "\n\n💡 _सुझाव: अधिक जानकारी के लिए कोई नाम लिखें (उदा. 'राधा', 'अर्जुन')।_"
    
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


# ============= NEW FEATURES =============

def get_random_entry() -> Optional[Dict[str, Any]]:
    """Get a random verse or figure introduction."""
    import random
    entries = _load_documents()
    if not entries:
        return None
    return random.choice(entries)


def search_entries(query: str, filters: Dict[str, str] = None) -> List[Dict[str, Any]]:
    """Advanced search with filters (source, chapter, lang)."""
    query_lower = query.lower()
    entries = _load_documents()
    results = []
    
    for entry in entries:
        # Check query match
        text = _entry_to_corpus_text(entry).lower()
        if query_lower not in text:
            continue
        
        # Apply filters
        if filters:
            if 'source' in filters and entry.get('source', '').lower() != filters['source'].lower():
                continue
            if 'chapter' in filters and entry.get('chapter', '').lower() != filters['chapter'].lower():
                continue
        
        results.append(entry)
    
    return results[:20]  # Limit to 20 results


def get_entry_sequence(source: str, chapter: str = None) -> List[Dict[str, Any]]:
    """Get all verses in a source or chapter for navigation."""
    entries = _load_documents()
    results = []
    
    for entry in entries:
        if entry.get('source', '').lower() == source.lower():
            if chapter and entry.get('chapter', '').lower() != chapter.lower():
                continue
            results.append(entry)
    
    return results
