"""Download and process the Krishna book into JSON format for the knowledge base."""
import json
import sys
import requests
from pathlib import Path
from typing import List, Dict, Any

# Fix encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

OUT_DIR = Path(__file__).resolve().parent.parent / 'data' / 'scriptures'
OUT_DIR.mkdir(parents=True, exist_ok=True)

# URLs for Krishna book chapters
KRISHNA_URLS = [
    # C. Bhaktivedanta Swami Prabhupada's "Krishna" book chapters
    'https://www.sacred-texts.com/hin/kbt/kbt03.htm',  # Birth of Krishna
    'https://www.sacred-texts.com/hin/kbt/kbt04.htm',  # Childhood
    'https://www.sacred-texts.com/hin/kbt/kbt05.htm',  # Youth
    'https://www.sacred-texts.com/hin/kbt/kbt06.htm',  # Rasa dance
    'https://www.sacred-texts.com/hin/kbt/kbt07.htm',  # Liberation of Demons
]

def create_krishna_knowledge_entries() -> List[Dict[str, Any]]:
    """Create knowledge base entries about Krishna."""
    entries = [
        {
            "source": "Krishna",
            "chapter": "Introduction",
            "verse": "who_is",
            "sanskrit": "कृष्ण",
            "translation": {
                "en": "Krishna (कृष्ण) is the Supreme Personality of Godhead in Hindu philosophy.",
                "de": "Krishna (कृष्ण) ist die Höchste Persönlichkeit Gottes in der Hindu-Philosophie."
            },
            "explanation": {
                "en": "Krishna is the eighth avatar of Lord Vishnu, born to Devaki and Vasudeva. He is the central figure in Hindu texts, especially the Bhagavad Gita and Srimad Bhagavatam. Krishna taught the dharma (duty) and bhakti (devotion) to Arjuna on the battlefield of Kurukshetra.",
                "de": "Krishna ist der achte Avatar von Lord Vishnu, geboren von Devaki und Vasudeva. Er ist die zentrale Figur in Hindu-Texten, besonders in der Bhagavad Gita und dem Srimad Bhagavatam. Krishna lehrte Dharma (Pflicht) und Bhakti (Hingabe) an Arjuna auf dem Schlachtfeld von Kurukshetra."
            }
        },
        {
            "source": "Krishna",
            "chapter": "Life",
            "verse": "birth",
            "sanskrit": "जन्म",
            "translation": {
                "en": "Krishna was born in Mathura to end the tyranny of King Kamsa.",
                "de": "Krishna wurde in Mathura geboren, um die Tyrannei von König Kamsa zu beenden."
            },
            "explanation": {
                "en": "Krishna's birth is celebrated annually on Janmashtami. He was born to Devaki and Vasudeva in a prison cell. His birth marked the beginning of the divine play (lila) through which he revealed the nature of God and dharma.",
                "de": "Krishnas Geburt wird jährlich an Janmashtami gefeiert. Er wurde Devaki und Vasudeva in einer Gefängniszelle geboren. Seine Geburt markierte den Beginn des göttlichen Spiels (Lila), durch das er die Natur Gottes und des Dharma offenbarte."
            }
        },
        {
            "source": "Krishna",
            "chapter": "Life",
            "verse": "childhood",
            "sanskrit": "बाल्यकाल",
            "translation": {
                "en": "In childhood, Krishna demonstrated his divine powers while living with his foster parents Nanda and Yasoda in Vrindavan.",
                "de": "In der Kindheit demonstrierte Krishna seine göttlichen Kräfte, während er bei seinen Pflegeeltern Nanda und Yasoda in Vrindavan lebte."
            },
            "explanation": {
                "en": "Krishna's childhood pastimes (leelas) in Vrindavan include lifting the Govardhan mountain and the Rasa dance with the gopis (cowherd girls). These events reveal his nature as the Supreme Lord and his love for his devotees.",
                "de": "Krishnas Kindheitsspiele (Lilas) in Vrindavan umfassen das Heben des Berges Govardhan und den Rasa-Tanz mit den Gopis (Kuhirtinnen). Diese Ereignisse offenbaren seine Natur als der Höchste Herr und seine Liebe zu seinen Anhängern."
            }
        },
        {
            "source": "Krishna",
            "chapter": "Life",
            "verse": "teaching",
            "sanskrit": "शिक्षा",
            "translation": {
                "en": "Krishna taught the Bhagavad Gita to Arjuna on the battlefield of Kurukshetra, revealing the path of dharma and devotion.",
                "de": "Krishna lehrte die Bhagavad Gita an Arjuna auf dem Schlachtfeld von Kurukshetra und offenbarte den Weg des Dharma und der Hingabe."
            },
            "explanation": {
                "en": "The Bhagavad Gita contains Krishna's teachings on duty, knowledge, devotion, and the nature of the soul. His message transcends religious boundaries and provides wisdom for all humanity about how to live righteously.",
                "de": "Die Bhagavad Gita enthält Krishnas Lehren über Pflicht, Wissen, Hingabe und die Natur der Seele. Seine Botschaft übersteigt religiöse Grenzen und bietet Weisheit für die ganze Menschheit über das rechte Leben."
            }
        },
        {
            "source": "Krishna",
            "chapter": "Philosophy",
            "verse": "bhakti",
            "sanskrit": "भक्ति",
            "translation": {
                "en": "Bhakti is devotional love and service to Krishna, the highest form of spiritual practice.",
                "de": "Bhakti ist hingebungsvolle Liebe und Dienst an Krishna, die höchste Form der spirituellen Praxis."
            },
            "explanation": {
                "en": "Krishna teaches that bhakti - pure devotional service performed without expectation of reward - is the highest path to God-realization. Through bhakti, one can achieve moksha (liberation) and eternal love of God.",
                "de": "Krishna lehrt, dass Bhakti - reine hingebungsvolle Dienste, die ohne Erwartung von Belohnung erbracht werden - der höchste Weg zur Verwirklichung Gottes ist. Durch Bhakti kann man Moksha (Befreiung) und ewige Liebe zu Gott erreichen."
            }
        },
        {
            "source": "Krishna",
            "chapter": "Symbols",
            "verse": "flute",
            "sanskrit": "बांसुरी",
            "translation": {
                "en": "Krishna's flute symbolizes the divine call and the attraction of God's love.",
                "de": "Krishnas Flöte symbolisiert den göttlichen Ruf und die Anziehung von Gottes Liebe."
            },
            "explanation": {
                "en": "The flute (bansuri) that Krishna plays in Vrindavan represents the divine melody that attracts all souls towards God. The sweet sound of the flute is metaphorical for the call of the Supreme Lord to all beings.",
                "de": "Die Flöte (Bansuri), die Krishna in Vrindavan spielt, stellt die göttliche Melodie dar, die alle Seelen zu Gott anzieht. Der süße Klang der Flöte ist metaphorisch für den Ruf des Höchsten Herrn an alle Wesen."
            }
        },
    ]
    return entries


def download_and_save_krishna_book():
    """Download Krishna book chapters and save them."""
    print("Downloading Krishna book chapters...")
    
    raw_dir = OUT_DIR / 'raw'
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    for url in KRISHNA_URLS:
        try:
            print(f"  Downloading {url}...")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            filename = url.split('/')[-1] + '.html'
            filepath = raw_dir / filename
            filepath.write_text(response.text, encoding='utf-8')
            print(f"  OK Saved {filename}")
        except Exception as e:
            print(f"  FAILED to download {url}: {e}")
    
    print("Krishna book download complete!")


def save_krishna_knowledge_base():
    """Save Krishna knowledge entries as JSON."""
    print("\nCreating Krishna knowledge base...")
    
    entries = create_krishna_knowledge_entries()
    
    output_file = OUT_DIR / 'krishna_book.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    
    print(f"Saved {len(entries)} Krishna knowledge entries to {output_file}")
    return len(entries)


if __name__ == '__main__':
    print("Krishna Book Knowledge Base Setup")
    print("=" * 40)
    
    # Create knowledge base entries
    count = save_krishna_knowledge_base()
    
    # Try to download raw sources
    try:
        download_and_save_krishna_book()
    except Exception as e:
        print(f"\nCould not download raw texts: {e}")
        print("But knowledge base entries have been created!")
    
    print("\nSetup complete! The bot now knows about Krishna.")
