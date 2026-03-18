
const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const http = require('http');
const fs = require('fs');

const LOG_FILE = '/home/userk/.jarvis/whatsapp.log';
const MSG_QUEUE_FILE = '/home/userk/.jarvis/wa_queue.json';
const AUTHORIZED_NUMBERS = ['905XXXXXXXXX@c.us']; // DeÄŸiÅŸtir!

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
    log('QR Code generated â€” scan with WhatsApp:');
    qrcode.generate(qr, { small: true });
    // Save QR to file for web display
    fs.writeFileSync('/home/userk/.jarvis/wa_qr.txt', qr);
});

client.on('ready', () => {
    log('âœ… WhatsApp baÄŸlantÄ±sÄ± kuruldu!');
    // Notify via file flag
    fs.writeFileSync('/home/userk/.jarvis/wa_ready.flag', 'ready');
});

client.on('message', async (msg) => {
    const from = msg.from;
    const body = msg.body;
    const isGroup = from.endsWith('@g.us');
    
    if (isGroup) return; // Grup mesajlarÄ±nÄ± ignore et
    
    log(`Message from ${from}: ${body.substring(0, 50)}`);
    
    // Queue message for bridge.py to process
    const queue = JSON.parse(fs.readFileSync(MSG_QUEUE_FILE, 'utf8'));
    queue.push({ from, body, time: Date.now() });
    // Keep last 50 messages
    if (queue.length > 50) queue.shift();
    fs.writeFileSync(MSG_QUEUE_FILE, JSON.stringify(queue, null, 2));
    
    // Auto-acknowledge
    client.sendMessage(from, 'âš¡ _Jarvis iÅŸliyor..._');
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
    log('ğŸ“¡ WhatsApp API: http://127.0.0.1:3001');
});

client.initialize();
log('WhatsApp bridge starting...');
