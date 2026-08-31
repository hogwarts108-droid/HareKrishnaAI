import requests
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / 'data' / 'scriptures' / 'raw'
OUT.mkdir(parents=True, exist_ok=True)

urls = [
    'https://www.sacred-texts.com/hin/gita/bg01.htm',
    'https://www.sacred-texts.com/hin/gita/bg02.htm',
    'https://www.sacred-texts.com/hin/gita/bg03.htm',
    'https://www.sacred-texts.com/hin/gita/bg04.htm',
    'https://www.sacred-texts.com/hin/gita/bg05.htm',
    'https://www.sacred-texts.com/hin/gita/bg06.htm',
    'https://www.sacred-texts.com/hin/gita/bg07.htm',
    'https://www.sacred-texts.com/hin/gita/bg08.htm',
    'https://www.sacred-texts.com/hin/gita/bg09.htm',
    'https://www.sacred-texts.com/hin/gita/bg10.htm',
    'https://www.sacred-texts.com/hin/gita/bg11.htm',
    'https://www.sacred-texts.com/hin/gita/bg12.htm',
    'https://www.sacred-texts.com/hin/gita/bg13.htm',
    'https://www.sacred-texts.com/hin/gita/bg14.htm',
    'https://www.sacred-texts.com/hin/gita/bg15.htm',
    'https://www.sacred-texts.com/hin/gita/bg16.htm',
    'https://www.sacred-texts.com/hin/gita/bg17.htm',
    'https://www.sacred-texts.com/hin/gita/bg18.htm',
    'https://www.sacred-texts.com/hin/yogasutr.htm'
]

for url in urls:
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        name = url.split('/')[-1]
        if not name:
            name = 'index'
        fname = OUT / (name.replace('/', '_'))
        # save as .html
        fname.write_text(r.text, encoding='utf-8')
        print('Saved', fname)
    except Exception as e:
        print('Failed', url, e)

print('Done')
