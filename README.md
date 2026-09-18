# HareKrishnaAI

## Web-Chat

Das Repository enthält jetzt einen Chat-Endpunkt unter `POST /api/chat`. Der Browser spricht ausschließlich mit diesem eigenen Backend; lokale Ollama- oder LM-Studio-Endpunkte werden nie aus JavaScript angesprochen.

### Backend konfigurieren

```bash
cp .env.example .env
# Telegram-Bot-Token setzen
LOCAL_LLM_ENABLED=true
LOCAL_LLM_PROVIDER=ollama             # ollama oder openai-compatible
LOCAL_LLM_BASE_URL=http://localhost:11434
LOCAL_LLM_MODEL=llama3.1
LOCAL_LLM_TIMEOUT=30
CHAT_ALLOWED_ORIGINS=https://hogwarts108-droid.github.io
```

Für LM Studio setzt du beispielsweise `LOCAL_LLM_PROVIDER=openai-compatible`, `LOCAL_LLM_BASE_URL=http://127.0.0.1:1234` und den dort geladenen Modellnamen. Wenn das Modell nicht erreichbar ist oder deaktiviert wurde, antwortet die API aus der vorhandenen Wissensdatenbank. `CHAT_ALLOWED_ORIGINS` ist eine kommaseparierte Allowlist; leer bedeutet keine Cross-Origin-Freigabe.

### GitHub-Pages-Frontend

Die statische Seite unter `docs/` benötigt eine öffentlich erreichbare Backend-URL. Vor dem Deployment kann sie in `docs/index.html` gesetzt werden:

```html
<script>window.BHAKTI_CHAT_API_URL = "https://dein-backend.example";</script>
```

Ist keine URL gesetzt, zeigt die Chat-UI eine klare Konfigurationsmeldung. GitHub Pages kann keine lokalen `localhost`-Modelle erreichen. Das Flask-Backend läuft über `python -m app.bot` und stellt neben den Seiten auch `/api/chat` und `/health` bereit.

### Tests

```bash
python -m pytest
python -m py_compile app/chat.py app/bot.py app/config.py app/knowledge.py
```
