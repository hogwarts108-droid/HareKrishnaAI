import json
from pathlib import Path

KB_DIR = Path(__file__).resolve().parent.parent / 'data' / 'scriptures'

def normalize_text(t):
    if not isinstance(t, str):
        return t
    # replace unicode ellipsis and triple dots
    s = t.replace('…', '...')
    # remove trailing ellipses
    if s.strip().endswith('...'):
        s = s.strip()[:-3].strip()
    # ensure it ends with punctuation
    if s and s[-1] not in '.!?':
        s = s + '.'
    return s

changed_files = []
entries_changed = 0
for path in KB_DIR.rglob('*.json'):
    try:
        text = path.read_text(encoding='utf-8')
        data = json.loads(text)
    except Exception as e:
        print('skip', path, 'err', e)
        continue
    modified = False
    if isinstance(data, dict):
        entries = [data]
    elif isinstance(data, list):
        entries = data
    else:
        continue

    for entry in entries:
        trans = entry.get('translation', {}) or {}
        expl = entry.get('explanation', {}) or {}
        de = trans.get('de')
        if isinstance(de, str) and '...' in de:
            new_de = normalize_text(de)
            # if explanation.de exists and is not duplicate, append it to make fuller quote
            expl_de = expl.get('de', '').strip()
            if expl_de and expl_de not in new_de:
                # ensure expl_de ends with punctuation
                if expl_de[-1] not in '.!?':
                    expl_de = expl_de + '.'
                new_de = new_de.rstrip('.') + '. ' + expl_de
            trans['de'] = new_de
            entry['translation'] = trans
            modified = True
            entries_changed += 1
        # also replace unicode ellipsis in other translations if present
        for k, v in list(trans.items()):
            if isinstance(v, str) and '…' in v:
                trans[k] = normalize_text(v)
                modified = True
    if modified:
        # write backup
        bak = path.with_suffix(path.suffix + '.bak')
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        changed_files.append(path)

print('Files modified:', len(changed_files))
print('Entries modified:', entries_changed)
for f in changed_files:
    print(' -', f)
