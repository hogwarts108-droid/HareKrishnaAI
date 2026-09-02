import json
from pathlib import Path

files = [
    'data/scriptures/bg_sample.json',
    'data/scriptures/bg_extra.json',
    'data/scriptures/bg_complete_work.json',
]

for f in files:
    p = Path(f)
    if not p.exists():
        continue
    print(f"\n=== {f} ===")
    with open(p, encoding='utf-8') as fp:
        data = json.load(fp)
        if isinstance(data, list):
            for entry in data[:3]:
                ch = entry.get('chapter')
                v = entry.get('verse')
                print(f"  Chapter: {ch!r} ({type(ch).__name__}), Verse: {v!r} ({type(v).__name__})")
                ref = f"{ch}.{v}"
                print(f"    → Ref: {ref!r}")
