# HareKrishnaAI - Kostenlos Deployment Guide

## 100% Kostenlose Optionen

### Option 1: Railway.app ⭐ (Empfohlen)
- **Kostenlos**: $5/Monat Guthaben
- **Dauerbetrieb**: Ja, 24/7 im kostenlosen Tier
- **Speicher**: Genug für deinen Bot

#### Schritte:
1. Gehe zu https://railway.app
2. Registriere dich mit GitHub
3. Neues Projekt erstellen
4. GitHub-Repo verbinden (dieses hier)
5. Environment Variable setzen: `TELEGRAM_BOT_TOKEN=<dein-token>`
6. Deploy

### Option 2: Fly.io
- **Kostenlos**: 3 Shared CPUs, 3GB RAM pro Monat
- **Dauerbetrieb**: Ja, immer online
- **Perfect for**: Kleine Bots

#### Schritte:
1. Gehe zu https://fly.io
2. Registriere dich
3. Installiere `flyctl` CLI
4. `flyctl auth login`
5. `flyctl launch` (im Projektverzeichnis)
6. `flyctl secrets set TELEGRAM_BOT_TOKEN=<dein-token>`
7. `flyctl deploy`

### Option 3: Render.com
- **Kostenlos**: Free Tier mit Limits
- **Nachteil**: Wird nach 15 Min Inaktivität pausiert
- **Für Tests OK**, nicht ideal für 24/7

---

## Was brauchst du?

1. **GitHub Account** (kostenlos)
2. **Telegram Bot Token** (kostenlos, von @BotFather)
3. **Railway oder Fly Account** (kostenlos)

---

## Schnellstart mit Railway

```bash
# 1. GitHub Repo clonen/forken
git clone https://github.com/dein-username/HareKrishnaAI.git
cd HareKrishnaAI

# 2. Railway CLI installieren
# https://docs.railway.app/guides/cli

# 3. Login und Deploy
railway login
railway init
railway variables set TELEGRAM_BOT_TOKEN=<token>
railway up
```

---

## Telegram Bot Token bekommen

1. Öffne Telegram
2. Suche: `@BotFather`
3. Schreib: `/newbot`
4. Folge den Anweisungen
5. Kopiere den Token

---

## Kostenloser Speicher für Wissensbasis

Die Wissensdateien (JSON) sind klein genug, dass sie kostenlos gehostet werden.

---

## Support

- Railway Docs: https://docs.railway.app
- Fly Docs: https://fly.io/docs
- Telegram Bot API: https://core.telegram.org/bots

---

## Fazit: 100% Kostenlos ✅

Mit Railway oder Fly.io läuft dein Bot komplett kostenlos 24/7!
