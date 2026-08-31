# HareKrishnaAI - Telegram Bot mit Bhakti-Wissen

🙏 Ein spiritueller Telegram-Bot, der Fragen über Bhakti, Bhagavad Gita, Yoga Sutra, Srimad Bhagavatam und Sri Isopanishad beantwortet.

## Features

- ✅ Bhagavad Gita Verse + Erklärungen
- ✅ Yoga Sutra 
- ✅ Srimad Bhagavatam
- ✅ Sri Isopanishad
- ✅ Krishna-Lehren
- ✅ Intelligente Versabfrage ("Bhagavad Gita 18.66")
- ✅ Deutsch + Englisch
- ✅ Sanskrit + Übersetzung + Erklärung

## ⚡ Schnellstart (5 Minuten)

### 1. Token bekommen
- Öffne Telegram
- Schreib `@BotFather`
- Kommand: `/newbot`
- Folge Anweisungen
- Kopiere den Token

### 2. Kostenlos deployieren mit Railway

```bash
# 1. Dieses Repo forken/clonen
git clone https://github.com/dein-username/HareKrishnaAI.git

# 2. Auf railway.app gehen
# - Registrieren mit GitHub
# - GitHub-Repo verbinden
# - Environment Variable setzen: TELEGRAM_BOT_TOKEN=<token>
# - Deploy

# Fertig! 🎉
```

## 📱 Bot nutzen

```
/start        - Begrüßung
/reload       - Index neu aufbauen

Fragen:
- "Was ist Dharma?"
- "Bhagavad Gita 18.66"
- "Yoga Sutra 1.2"
- "Wer bin ich?"
```

## 💻 Lokal testen

```bash
# Virtual Env
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\\Scripts\\activate    # Windows

# Dependencies
pip install -r requirements.txt

# .env mit Token erstellen
cp .env.example .env
# Bearbeite .env und setze TELEGRAM_BOT_TOKEN

# Bot starten
python -m app.bot
```

## 🚀 Deployment

Siehe [DEPLOYMENT.md](DEPLOYMENT.md) für:
- Railway.app (kostenlos, 24/7)
- Fly.io (kostenlos, 24/7)
- Docker
- Systemd (Linux)

## 📚 Struktur

```
app/
  bot.py           - Telegram Bot
  knowledge.py     - Wissensbasis + Suchlogik
  config.py        - Konfiguration

data/
  scriptures/      - JSON Wissensdateien
    bg_complete_work.json
    yoga_sutra_complete.json
    isopanishad_complete.json
    bhagavatam_complete.json

scripts/
  import_texts.py  - Texte importieren
  download_sources.py - Quellen laden
```

## 🧠 Wissensbasis erweitern

1. Neue Texte in `data/scriptures/raw/` speichern
2. `scripts/import_texts.py` ausführen
3. Bot neu starten

JSON-Format:
```json
{
  "source": "Bhagavad Gita",
  "chapter": "18",
  "verse": "66",
  "sanskrit": "sarva-dharman parityajya...",
  "translation": {
    "de": "...",
    "en": "..."
  },
  "explanation": {
    "de": "...",
    "en": "..."
  }
}
```

## 🆓 Kostenlos 100%?

✅ Ja! Mit Railway oder Fly.io:
- Kein Account nötig außer GitHub
- $5/Monat Guthaben kostenlos (Railway)
- oder 3 Shared CPUs kostenlos (Fly.io)
- Läuft 24/7

## 📖 Mehr Info

- [Deployment Guide](DEPLOYMENT.md)
- [Telegram Bot API](https://core.telegram.org/bots)
- [Railway Docs](https://docs.railway.app)
- [Fly.io Docs](https://fly.io/docs)

---

🙏 **Hare Krishna!** Jai Radhe!
