"""
Jarvis Voice Skill
Telegram'dan gelen sesli mesajı metne çevirir.
faster-whisper (Python 3.11) kullanır.

Pipeline:
  Telegram voice (OGG) → ffmpeg → WAV → faster-whisper → metin

TTS (isteğe bağlı):
  metin → pyttsx3 → MP3 → Telegram'a sesli yanıt
"""

import os
import sys
import tempfile
import subprocess

PYTHON311 = r"C:\Program Files\Python311\python.exe"
if not os.path.exists(PYTHON311):
    PYTHON311 = sys.executable

FFMPEG = r"C:\Users\sergen\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-full_build\bin\ffmpeg.exe"
if not os.path.exists(FFMPEG):
    FFMPEG = "ffmpeg"

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
TTS_ENABLED = os.getenv("TTS_ENABLED", "1") == "1"


# ─── OGG → WAV dönüşümü ─────────────────────────────────────────────────────

def ogg_to_wav(ogg_path: str) -> str:
    """Telegram'ın OGG dosyasını WAV'a çevir."""
    wav_path = ogg_path.replace(".ogg", ".wav").replace(".oga", ".wav")
    if not wav_path.endswith(".wav"):
        wav_path += ".wav"
    result = subprocess.run(
        [FFMPEG, "-y", "-i", ogg_path, "-ar", "16000", "-ac", "1", wav_path],
        capture_output=True, timeout=30
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg hatası: {result.stderr.decode()[:200]}")
    return wav_path


# ─── Whisper ile transkript ──────────────────────────────────────────────────

WHISPER_SCRIPT = r"""
import sys
from faster_whisper import WhisperModel
model = WhisperModel("{model}", device="cpu", compute_type="int8")
segments, info = model.transcribe(sys.argv[1], language="tr", beam_size=3)
text = " ".join(s.text.strip() for s in segments)
print(text)
"""

def transcribe_audio(wav_path: str) -> str:
    """faster-whisper ile ses dosyasını metne çevir (Python 3.11 subprocess)."""
    # Script'i geçici dosyaya yaz
    script = WHISPER_SCRIPT.format(model=WHISPER_MODEL)
    tmp_script = tempfile.NamedTemporaryFile(suffix=".py", delete=False,
                                             mode="w", encoding="utf-8")
    tmp_script.write(script)
    tmp_script.close()

    try:
        result = subprocess.run(
            [PYTHON311, tmp_script.name, wav_path],
            capture_output=True, text=True, timeout=60
        )
        os.unlink(tmp_script.name)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"Whisper hatası: {result.stderr.strip()[:200]}"
    except subprocess.TimeoutExpired:
        return "Ses tanıma zaman aşımı."
    except Exception as e:
        return f"Transkript hatası: {e}"


# ─── TTS: Metin → Ses ───────────────────────────────────────────────────────

TTS_SCRIPT = r"""
import sys, pyttsx3, tempfile, os
engine = pyttsx3.init()
engine.setProperty('rate', 165)
engine.setProperty('volume', 0.95)
# Türkçe ses varsa seç
voices = engine.getProperty('voices')
for v in voices:
    if 'tr' in v.id.lower() or 'turkish' in v.name.lower():
        engine.setProperty('voice', v.id)
        break
out_path = sys.argv[1]
engine.save_to_file(sys.argv[2], out_path)
engine.runAndWait()
print(out_path)
"""

def text_to_speech(text: str) -> str:
    """Metni MP3'e çevir, dosya yolunu döndür. Hata olursa None."""
    if not TTS_ENABLED:
        return None
    try:
        out_path = tempfile.mktemp(suffix=".mp3")
        tmp_script = tempfile.NamedTemporaryFile(suffix=".py", delete=False,
                                                  mode="w", encoding="utf-8")
        tmp_script.write(TTS_SCRIPT)
        tmp_script.close()

        result = subprocess.run(
            [PYTHON311, tmp_script.name, out_path, text[:500]],
            capture_output=True, text=True, timeout=30
        )
        os.unlink(tmp_script.name)
        if result.returncode == 0 and os.path.exists(out_path):
            return out_path
        return None
    except Exception:
        return None


# ─── Ana fonksiyon: Telegram voice handler ──────────────────────────────────

def handle_voice_message(bot_token: str, file_id: str) -> dict:
    """
    Telegram'dan gelen voice mesajı işle.
    Döner: {"text": "transkript", "audio_reply": "dosya_yolu veya None"}
    """
    import urllib.request

    # 1. file_path al
    url = f"https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}"
    with urllib.request.urlopen(url, timeout=10) as resp:
        import json
        data = json.loads(resp.read())
        file_path = data["result"]["file_path"]

    # 2. Dosyayı indir
    download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
    ogg_path = tempfile.mktemp(suffix=".ogg")
    urllib.request.urlretrieve(download_url, ogg_path)

    try:
        # 3. OGG → WAV
        wav_path = ogg_to_wav(ogg_path)

        # 4. Whisper → metin
        text = transcribe_audio(wav_path)

        # Temizle
        for p in [ogg_path, wav_path]:
            try:
                os.unlink(p)
            except Exception:
                pass

        return {"text": text, "audio_reply": None}
    except Exception as e:
        return {"text": f"Ses işleme hatası: {e}", "audio_reply": None}
    finally:
        try:
            os.unlink(ogg_path)
        except Exception:
            pass
