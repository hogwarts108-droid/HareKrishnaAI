import sys
import json
from pathlib import Path

# Ensure project root is on sys.path so `from app import ...` works when running
# the script directly.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import knowledge

queries = [
    'Was ist Dharma?',
    'Was ist Karma?',
    'Wer ist die Quelle aller Welten?',
    'Was ist Atman?'
]

for q in queries:
    print('\n=== Frage: ' + q)
    r = knowledge.find_answer(q)
    if not r:
        print('Keine Antwort gefunden')
        continue
    print(json.dumps(r, ensure_ascii=False, indent=2))
    # Also test generation
    text = knowledge.generate_answer_text(q, r, lang='de')
    print('\nGenerierte Antwort:\n')
    print(text)
