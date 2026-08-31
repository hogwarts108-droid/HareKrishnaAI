import json
from pathlib import Path

KB_DIR = Path(__file__).resolve().parent.parent / 'data' / 'scriptures'

def normalize(s: str) -> str:
    if not isinstance(s, str):
        return s
    s = s.replace('\u2026', '...')
    s = s.strip()
    # remove trailing ellipsis groups
    while s.endswith('...'):
        s = s[:-3].strip()
    # ensure punctuation
    if s and s[-1] not in '.!?':
        s = s + '.'
    return s

modified_files = []
modified_entries = 0
all_entries = []

for path in KB_DIR.rglob('*.json'):
    try:
        text = path.read_text(encoding='utf-8')
        data = json.loads(text)
    except Exception as e:
        print('skip', path, 'err', e)
        continue

    if isinstance(data, dict):
        entries = [data]
    elif isinstance(data, list):
        entries = data
    else:
        continue

    changed = False
    for entry in entries:
        all_entries.append(entry)
        trans = entry.get('translation') or {}
        expl = entry.get('explanation') or {}
        de_trans = trans.get('de', '')
        de_expl = expl.get('de', '').strip()

        new_trans = normalize(de_trans)
        # If original was short or ended with ellipsis, append explanation to form a fuller quote
        needs_append = False
        if not de_trans or len(de_trans.strip()) < 30 or '...' in de_trans:
            needs_append = True
        if needs_append and de_expl:
            # ensure explanation ends with punctuation
            if de_expl and de_expl[-1] not in '.!?':
                de_expl = de_expl + '.'
            # combine
            if new_trans.endswith('.'):
                new_trans = new_trans[:-1]
            new_trans = new_trans + '. ' + de_expl
        # final ensure punctuation
        new_trans = new_trans.strip()
        if new_trans and new_trans[-1] not in '.!?':
            new_trans = new_trans + '.'

        if new_trans != de_trans:
            trans['de'] = new_trans
            entry['translation'] = trans
            changed = True
            modified_entries += 1

    if changed:
        bak = path.with_suffix(path.suffix + '.bak')
        bak.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        modified_files.append(path)

# Report
print('Modified files:', len(modified_files))
for p in modified_files:
    print(' -', p)
print('Modified entries:', modified_entries)

# Build source summary
from collections import Counter
sources = [ (e.get('source') or 'Unbekannt') for e in all_entries ]
counts = Counter(sources)
print('\nSources in KB:')
for s, c in counts.most_common():
    print(f' - {s}: {c} entries')

# Rebuild index and print entry count
try:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from app import knowledge
    n = knowledge.reload_index()
    print('\nIndex rebuilt. Total entries loaded:', n)
except Exception as e:
    print('Could not reload index:', e)
