import json
from pathlib import Path
import re

RAW_DIR = Path(__file__).resolve().parent.parent / 'data' / 'scriptures' / 'raw'
OUT_DIR = Path(__file__).resolve().parent.parent / 'data' / 'scriptures'
RAW_DIR.mkdir(parents=True, exist_ok=True)

def detect_blocks(text: str):
    # split on two or more newlines
    parts = re.split(r"\n\s*\n+", text.strip())
    return [p.strip() for p in parts if p.strip()]

verse_header_re = re.compile(r"^\s*(\d+(?:[:.]\d+)?)(?:\s*[-–:\)]\s*)?(.*)$", re.MULTILINE)

processed = 0
files = list(RAW_DIR.glob('*'))
if not files:
    print('No raw files found in', RAW_DIR)
    print('Place TXT/MD/JSON files there and re-run this script.')
    raise SystemExit(0)

for path in files:
    name = path.stem
    out_path = OUT_DIR / f"imported_{name}.json"
    entries = []
    try:
        if path.suffix.lower() == '.json':
            data = json.loads(path.read_text(encoding='utf-8'))
            # if it's already structured, copy through (wrap single dict)
            if isinstance(data, list):
                entries = data
            elif isinstance(data, dict):
                entries = [data]
            else:
                # write as single translation
                entries = [{
                    'source': name,
                    'verse': 'full',
                    'sanskrit': '',
                    'translation': {'de': str(data)},
                    'explanation': {'de': ''}
                }]
        else:
            text = path.read_text(encoding='utf-8')
            blocks = detect_blocks(text)
            for b in blocks:
                # try detect a leading verse number
                m = verse_header_re.match(b)
                if m:
                    verse = m.group(1)
                    content = m.group(2).strip()
                    if not content:
                        # remove first line and take rest
                        lines = b.splitlines()
                        content = '\n'.join(lines[1:]).strip()
                    translation = content or b
                else:
                    verse = 'full' if len(blocks) == 1 else ''
                    translation = b
                entries.append({
                    'source': name,
                    'verse': verse,
                    'sanskrit': '',
                    'translation': {'de': translation.strip()},
                    'explanation': {'de': ''}
                })
        # save
        out_path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding='utf-8')
        processed += len(entries)
        print(f'Wrote {len(entries)} entries to {out_path}')
    except Exception as e:
        print('Error processing', path, e)

print('Processed total entries:', processed)
print('Done. Please run the bot or call reload to rebuild the index.')
