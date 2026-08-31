import re
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent.parent

KB_DIR = SCRIPT_DIR / 'data' / 'scriptures'

REPLACEMENTS = [
    (re.compile(r"\bbehauptet\b", flags=re.IGNORECASE), "ist"),
    (re.compile(r"\bbehauptet seine Stellung als\b", flags=re.IGNORECASE), "ist"),
    (re.compile(r"\bDieser Vers erklärt,?\b", flags=re.IGNORECASE), ""),
    (re.compile(r"\berklärt,? dass\b", flags=re.IGNORECASE), ""),
    (re.compile(r"\bstellt .* dar\b", flags=re.IGNORECASE), "ist"),
]


def to_assertive(text: str) -> str:
    if not text or not isinstance(text, str):
        return text
    s = text.strip()
    for patt, rep in REPLACEMENTS:
        s = patt.sub(rep, s)
    # clean up multiple spaces
    s = re.sub(r"\s+", " ", s).strip()
    # ensure ends with exclamation mark for assertive tone
    if not s.endswith('!'):
        s = s + '!' if s else s
    return s


def process_file(path: Path):
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except Exception as e:
        print(f"skip {path}: read error {e}")
        return

    changed = False
    if isinstance(data, dict):
        entries = [data]
    elif isinstance(data, list):
        entries = data
    else:
        return

    for entry in entries:
        expl = entry.get('explanation')
        if isinstance(expl, dict) and 'de' in expl:
            new = to_assertive(expl['de'])
            if new != expl['de']:
                expl['de'] = new
                changed = True

    if changed:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"updated {path}")


if __name__ == '__main__':
    for p in KB_DIR.glob('*.json'):
        process_file(p)
    print('Done')
