#!/bin/bash
# WhatsApp bridge kurulum scripti
set -e

echo "=== WhatsApp Bridge Kurulum ==="

# Node.js kontrol
if ! command -v node &> /dev/null; then
    echo "Node.js kuruluyor..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

echo "Node.js: $(node --version)"
echo "NPM: $(npm --version)"

# WhatsApp dizini
mkdir -p /opt/jarvis/whatsapp
cd /opt/jarvis/whatsapp

# package.json
cat > package.json << 'EOF'
{
  "name": "jarvis-whatsapp",
  "version": "1.0.0",
  "main": "wa_bridge.js",
  "dependencies": {
    "whatsapp-web.js": "^1.23.0",
    "qrcode-terminal": "^0.12.0"
  }
}
EOF

echo "NPM paketleri kuruluyor (3-5 dakika sÃ¼rebilir)..."
npm install

echo "âœ… WhatsApp bridge hazÄ±r!"
echo "BaÅŸlatmak iÃ§in: node /opt/jarvis/whatsapp/wa_bridge.js"
echo "QR kodu tara, 30 saniye iÃ§inde baÄŸlanÄ±r."
