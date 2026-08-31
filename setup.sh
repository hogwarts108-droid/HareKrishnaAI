#!/bin/bash
# Automatische Vorbereitung aller Wissensdateien

set -e

echo "📚 HareKrishnaAI Knowledge Base Setup"
echo "====================================="
echo ""

cd "$(dirname "$0")"

# 1. Prüfe Python-Installation
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "❌ Python nicht gefunden. Installiere Python 3.8+"
    exit 1
fi

PY=python3
if ! $PY --version &> /dev/null; then
    PY=python
fi

echo "✅ Python found: $PY"
echo ""

# 2. Virtual Environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    $PY -m venv venv
fi

source venv/bin/activate || . venv/Scripts/activate

echo "✅ Activated venv"
echo ""

# 3. Dependencies
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt

echo "✅ Dependencies installed"
echo ""

# 4. Import Chaitanya if raw files exist
if [ -f "data/scriptures/raw/*chaitan*" ] 2>/dev/null; then
    echo "🔄 Importing Chaitanya Charitamrita from raw files..."
    $PY scripts/import_chaitanya.py
    echo "✅ Chaitanya imported"
fi

# 5. Test knowledge base
echo "🧠 Testing knowledge base..."
$PY -c "
from app import knowledge
q = 'Bhagavad Gita 18.66'
r = knowledge.find_answer(q)
if r:
    print(f'✅ Query works: found {r[\"source\"]} {r[\"verse\"]}')
else:
    print('⚠️  No result found (knowledge files may be empty)')
"

echo ""
echo "📚 Knowledge Base Setup Complete!"
echo ""
echo "Next steps:"
echo "1. Set TELEGRAM_BOT_TOKEN in .env"
echo "2. python -m app.bot (to run locally)"
echo "3. Or deploy to Railway/Fly.io (see DEPLOYMENT.md)"
