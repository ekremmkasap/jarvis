import os
import time
from flask import Flask, request, jsonify, render_template
import google.generativeai as genai
from datetime import datetime
import threading
import schedule

app = Flask(__name__)

# --- YAPILANDIRMA ---
# NOT: Buraya geçerli bir Gemini API Key koyulmalı. 
# Kullanıcıdan anahtarı alana kadar simülasyon veya çevresel değişken kullanılacak.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- BLACKBOX OTOMASYON AJANI ---
def run_automation_tasks():
    print(f"[{datetime.now()}] Otomasyon ajanı arka planda kontrol yapılıyor...")
    # Burada agent.py içindeki mantık çalıştırılacak
    pass

def start_agent():
    schedule.every(1).hour.do(run_automation_tasks)
    while True:
        schedule.run_pending()
        time.sleep(60)

# Ajanı ayrı bir thread'de başlat
agent_thread = threading.Thread(target=start_agent, daemon=True)
agent_thread.start()

# --- API ROTARLARI ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message', '')
        
        if not user_message:
            return jsonify({'status': 'error', 'message': 'Mesaj boş olamaz'}), 400

        # İleri seviye istem (Prompt) mühendisliği
        # Kullanıcının tam isteğine göre: Blackbox + Özel istekler
        prompt = f"""
        Sen kullanıcının özel yapay zekasısın. 
        Görevlerin: Sohbet etmek, veri analizi yapmak ve otomasyon ajanlarını yönetmek.
        Dil: Tamamen Türkçe.
        Karakteristik: Dobra, dürüst ve son derece zeki.
        Kullanıcı Mesajı: {user_message}
        """

        response = model.generate_content(prompt)
        ai_response = response.text

        return jsonify({
            'status': 'success',
            'response': ai_response,
            'timestamp': datetime.now().strftime("%H:%M:%S")
        })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/analyze', methods=['POST'])
def analyze():
    # Veri analizi yeteneği buraya eklenecek
    return jsonify({'status': 'success', 'message': 'Veri analizi modülü aktif ediliyor.'})

if __name__ == '__main__':
    # Flask sunucusunu başlat
    app.run(debug=True, port=5000)
