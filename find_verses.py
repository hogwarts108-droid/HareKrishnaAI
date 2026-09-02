import json
from pathlib import Path

files = [
    'data/scriptures/bg_sample.json',
    'data/scriptures/bg_extra.json',
    'data/scriptures/bg_complete_work.json',
    'data/scriptures/complete_works_knowledge.json',
    'data/scriptures/initial_main_scriptures.json',
    'data/scriptures/more_entries.json',
]

print("Searching for verses starting with 1.")

for f in files:
    p = Path(f)
    if not p.exists():
        continue
    try:
        with open(p, encoding='utf-8') as fp:
            data = json.load(fp)
            if isinstance(data, list):
                for entry in data:
                    v = str(entry.get('verse') or '')
                    c = str(entry.get('chapter') or '')
                    if v.startswith('1.') or c.startswith('1.'):
                        ref = f"{c}.{v}" if c and v else (c or v)
                        if ref.startswith('1.'):
                            print(f"{f}: chapter={c}, verse={v} -> ref={ref}")
    except Exception as e:
        pass
