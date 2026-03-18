#!/usr/bin/env python3
"""
Jarvis WhatsApp Bridge — whatsapp-web.js (Node.js) üzerinden WhatsApp entegrasyonu
QR kod ile tararak bağlanır, Telegram gibi mesaj alır/gönderir.

Gereksinimler (sunucuda):
  apt install nodejs npm -y
  npm init -y && npm install whatsapp-web.js qrcode-terminal
"""

WHATSAPP_BRIDGE_JS = """
const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const http = require('http');
const fs = require('fs');

const LOG_FILE = '/home/userk/.jarvis/whatsapp.log';
const MSG_QUEUE_FILE = '/home/userk/.jarvis/wa_queue.json';
const AUTHORIZED_NUMBERS = ['905XXXXXXXXX@c.us']; // Değiştir!

function log(msg) {
    const line = `[${new Date().toISOString()}] ${msg}`;
    console.log(line);
    fs.appendFileSync(LOG_FILE, line + '\\n');
}

// Initialize queue
if (!fs.existsSync(MSG_QUEUE_FILE)) {
    fs.writeFileSync(MSG_QUEUE_FILE, JSON.stringify([]));
}

const client = new Client({
    authStrategy: new LocalAuth({ dataPath: '/home/userk/.jarvis/wa_session' }),
    puppeteer: {
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
    }
});

client.on('qr', (qr) => {
    log('QR Code generated — scan with WhatsApp:');
    qrcode.generate(qr, { small: true });
    // Save QR to file for web display
    fs.writeFileSync('/home/userk/.jarvis/wa_qr.txt', qr);
});

client.on('ready', () => {
    log('✅ WhatsApp bağlantısı kuruldu!');
    // Notify via file flag
    fs.writeFileSync('/home/userk/.jarvis/wa_ready.flag', 'ready');
});

client.on('message', async (msg) => {
    const from = msg.from;
    const body = msg.body;
    const isGroup = from.endsWith('@g.us');
    
    if (isGroup) return; // Grup mesajlarını ignore et
    
    log(`Message from ${from}: ${body.substring(0, 50)}`);
    
    // Queue message for bridge.py to process
    const queue = JSON.parse(fs.readFileSync(MSG_QUEUE_FILE, 'utf8'));
    queue.push({ from, body, time: Date.now() });
    // Keep last 50 messages
    if (queue.length > 50) queue.shift();
    fs.writeFileSync(MSG_QUEUE_FILE, JSON.stringify(queue, null, 2));
    
    // Auto-acknowledge
    client.sendMessage(from, '⚡ _Jarvis işliyor..._');
});

// HTTP API for sending messages from bridge.py
const server = http.createServer((req, res) => {
    if (req.method === 'POST' && req.url === '/send') {
        let body = '';
        req.on('data', chunk => body += chunk);
        req.on('end', async () => {
            try {
                const { to, message } = JSON.parse(body);
                await client.sendMessage(to, message);
                res.writeHead(200);
                res.end(JSON.stringify({ ok: true }));
                log(`Sent to ${to}: ${message.substring(0, 30)}`);
            } catch (e) {
                res.writeHead(500);
                res.end(JSON.stringify({ error: e.message }));
            }
        });
    } else if (req.method === 'GET' && req.url === '/queue') {
        const queue = JSON.parse(fs.readFileSync(MSG_QUEUE_FILE, 'utf8'));
        // Clear queue after reading
        fs.writeFileSync(MSG_QUEUE_FILE, JSON.stringify([]));
        res.writeHead(200);
        res.end(JSON.stringify(queue));
    } else if (req.method === 'GET' && req.url === '/status') {
        const ready = fs.existsSync('/home/userk/.jarvis/wa_ready.flag');
        res.writeHead(200);
        res.end(JSON.stringify({ ready, state: client.pupPage ? 'running' : 'starting' }));
    } else {
        res.writeHead(404);
        res.end('Not found');
    }
});

server.listen(3001, '127.0.0.1', () => {
    log('📡 WhatsApp API: http://127.0.0.1:3001');
});

client.initialize();
log('WhatsApp bridge starting...');
"""

WHATSAPP_SKILL_PY = """#!/usr/bin/env python3
\"\"\"
Jarvis WhatsApp Skill — bridge.py ile entegrasyon
WhatsApp mesajlarını alır, bridge.py aracılığıyla AI'ya yönlendirir.
\"\"\"

import json
import os
from urllib.request import urlopen, Request

WA_API = "http://127.0.0.1:3001"

def send_whatsapp(to: str, message: str) -> bool:
    \"\"\"WhatsApp mesajı gönder\"\"\"
    payload = json.dumps({"to": to, "message": message}).encode()
    req = Request(f"{WA_API}/send", data=payload,
                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            return result.get("ok", False)
    except Exception as e:
        return False

def get_pending_messages() -> list:
    \"\"\"WhatsApp'tan bekleyen mesajları al\"\"\"
    try:
        req = Request(f"{WA_API}/queue")
        with urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except:
        return []

def is_connected() -> bool:
    \"\"\"WhatsApp bağlı mı?\"\"\"
    try:
        req = Request(f"{WA_API}/status")
        with urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
            return data.get("ready", False)
    except:
        return False

def get_qr_path() -> str:
    \"\"\"QR kod dosyası\"\"\"
    return "/home/userk/.jarvis/wa_qr.txt"
"""

INSTALL_SCRIPT = """#!/bin/bash
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

echo "NPM paketleri kuruluyor (3-5 dakika sürebilir)..."
npm install

echo "✅ WhatsApp bridge hazır!"
echo "Başlatmak için: node /opt/jarvis/whatsapp/wa_bridge.js"
echo "QR kodu tara, 30 saniye içinde bağlanır."
"""

SERVICE_UNIT = """[Unit]
Description=Jarvis WhatsApp Bridge
After=network.target jarvis.service

[Service]
Type=simple
User=userk
WorkingDirectory=/opt/jarvis/whatsapp
ExecStart=/usr/bin/node /opt/jarvis/whatsapp/wa_bridge.js
Restart=on-failure
RestartSec=10
StandardOutput=append:/home/userk/.jarvis/whatsapp.log
StandardError=append:/home/userk/.jarvis/whatsapp.log

[Install]
WantedBy=multi-user.target
"""

if __name__ == "__main__":
    import os
    
    # Write all files
    os.makedirs("whatsapp_setup", exist_ok=True)
    
    with open("whatsapp_setup/wa_bridge.js", "w") as f:
        f.write(WHATSAPP_BRIDGE_JS)
    
    with open("whatsapp_setup/wa_skill.py", "w") as f:
        f.write(WHATSAPP_SKILL_PY)
    
    with open("whatsapp_setup/install.sh", "w") as f:
        f.write(INSTALL_SCRIPT)
    
    with open("whatsapp_setup/wa_bridge.service", "w") as f:
        f.write(SERVICE_UNIT)
    
    print("WhatsApp setup files ready in whatsapp_setup/")
