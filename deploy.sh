#!/bin/bash
set -e

echo "🙏 HareKrishnaAI Bot Deployment Setup"
echo "======================================"
echo ""
echo "Kostenlose Optionen:"
echo "1. Railway.app (kostenloses Tier, $5/Monat Guthaben)"
echo "2. Fly.io (kostenloses Tier, 3 Shared CPUs)"
echo ""

# Check for Railway CLI
if command -v railway &> /dev/null; then
    echo "✅ Railway CLI gefunden"
    echo ""
    echo "Schritte:"
    echo "1. railway login"
    echo "2. railway init"
    echo "3. railway variables set TELEGRAM_BOT_TOKEN=<dein-token>"
    echo "4. railway up"
    exit 0
fi

# Check for Fly CLI
if command -v flyctl &> /dev/null; then
    echo "✅ Fly CLI gefunden"
    echo ""
    echo "Schritte:"
    echo "1. fly auth login"
    echo "2. fly launch"
    echo "3. fly secrets set TELEGRAM_BOT_TOKEN=<dein-token>"
    echo "4. fly deploy"
    exit 0
fi

echo "❌ Weder Railway noch Fly CLI gefunden"
echo ""
echo "Installation:"
echo "Railway: https://docs.railway.app/guides/cli"
echo "Fly:     https://fly.io/docs/hands-on/install-flyctl/"
