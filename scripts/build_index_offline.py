#!/usr/bin/env python3
from pathlib import Path
import json
import pickle

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "data" / "scriptures"


def load_entries():
    entries = []
    if not KNOWLEDGE_DIR.exists():
        return entries
    for p in KNOWLEDGE_DIR.rglob("*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                entries.append(data)
            elif isinstance(data, list):
                entries.extend([e for e in data if isinstance(e, dict)])
        except Exception as e:
            print(f"Failed to read {p}: {e}")
    return entries


def entry_to_text(entry):
    parts = [entry.get("source", ""), entry.get("verse", ""), entry.get("sanskrit", "")]
    trans = entry.get("translation") or {}
    expl = entry.get("explanation") or {}
    parts.append(" ".join(str(v) for v in trans.values() if isinstance(v, str)))
    parts.append(" ".join(str(v) for v in expl.values() if isinstance(v, str)))
    return " \n ".join([p for p in parts if p])


def main():
    entries = load_entries()
    print("json_files:", sum(1 for _ in KNOWLEDGE_DIR.rglob("*.json")))
    print("entries:", len(entries))
    if not entries:
        return
    corpus = [entry_to_text(e) for e in entries]

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        vec = TfidfVectorizer(stop_words='english')
        mat = vec.fit_transform(corpus)
        print("tfidf_shape:", mat.shape)
        out = {
            "entries": entries,
            "vectorizer": vec,
            "matrix_shape": mat.shape,
        }
        # Save lightweight index (do not attempt to pickle large sparse matrix reliably)
        with open(KNOWLEDGE_DIR / "index_meta.pkl", "wb") as f:
            pickle.dump(out, f)
        print("Saved index_meta.pkl")
    except Exception as e:
        print("TF-IDF build failed:", e)


if __name__ == '__main__':
    main()
