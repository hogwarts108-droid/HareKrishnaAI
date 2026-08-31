import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPTURES_DIR = BASE_DIR / 'data' / 'scriptures'

def create_chaitanya_charitamrita_from_raw():
    """Importiert Chaitanya Charitamrita Texts aus Raw-HTML/TXT und wandelt sie in JSON um."""
    raw_dir = SCRIPTURES_DIR / 'raw'
    if not raw_dir.exists():
        return 0

    entries = []
    for raw_file in raw_dir.glob('*chaitan*'):
        if not raw_file.is_file():
            continue
        try:
            content = raw_file.read_text(encoding='utf-8', errors='ignore')
            # Simple parsing: split by chapter/verse patterns
            lines = content.split('\n')
            current_chapter = None
            current_verse = None

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Try to detect chapter.verse pattern
                if any(c.isdigit() for c in line[:10]):
                    parts = line.split()
                    for part in parts:
                        if '.' in part and all(c.isdigit() or c == '.' for c in part):
                            ch_v = part.split('.')
                            if len(ch_v) >= 2:
                                try:
                                    current_chapter = ch_v[0]
                                    current_verse = ch_v[1]
                                    break
                                except:
                                    pass

                if current_chapter and current_verse:
                    entry = {
                        'source': 'Chaitanya Charitamrita',
                        'chapter': current_chapter,
                        'verse': current_verse,
                        'sanskrit': '',
                        'translation': {'de': line, 'en': line},
                        'explanation': {'de': '', 'en': ''}
                    }
                    entries.append(entry)
                    current_verse = None

            print(f'Imported {len(entries)} entries from {raw_file.name}')
        except Exception as e:
            print(f'Error processing {raw_file.name}: {e}')

    if entries:
        out = SCRIPTURES_DIR / 'chaitanya_imported.json'
        out.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'Saved {len(entries)} Chaitanya entries to {out}')

    return len(entries)


if __name__ == '__main__':
    count = create_chaitanya_charitamrita_from_raw()
    print(f'Total: {count}')
