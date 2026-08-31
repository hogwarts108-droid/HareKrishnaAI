from pathlib import Path
import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / 'data' / 'scriptures' / 'raw'
OUT_DIR.mkdir(parents=True, exist_ok=True)

URLS = [
    'https://www.sacred-texts.com/hin/chaitanya/cc/index.htm',
    'https://www.sacred-texts.com/hin/chaitanya/cc/cc01.htm',
    'https://www.sacred-texts.com/hin/chaitanya/cc/cc02.htm',
    'https://www.sacred-texts.com/hin/chaitanya/cc/cc03.htm',
    'https://www.sacred-texts.com/hin/chaitanya/caitanya-charitamrita.htm',
    'https://www.sacred-texts.com/hin/cc/index.htm',
    'https://www.sacred-texts.com/hin/cc/cc01.htm',
    'https://archive.org/download/chaitanya-charitamrita/chaitanya-charitamrita.htm',
    'https://archive.org/download/chaitanya-charitamrita/chaitanya-charitamrita.html',
]

for idx, url in enumerate(URLS, 1):
    try:
        r = requests.get(url, timeout=30, headers={'User-Agent': 'Mozilla/5.0'})
        if r.status_code != 200:
            print(f'[{idx}] FAIL {url} -> {r.status_code}')
            continue
        if len(r.text) < 300:
            print(f'[{idx}] TOO SHORT {url} -> {len(r.text)} bytes')
            continue
        name = url.rstrip('/').split('/')[-1] or f'cc_{idx}'
        target = OUT_DIR / name
        target.write_text(r.text, encoding='utf-8')
        print(f'[{idx}] SAVED {url} -> {target}')
        break
    except Exception as e:
        print(f'[{idx}] ERROR {url} -> {e}')
else:
    print('No accessible public Charitamrita source found. Please add a known mirror manually.')
