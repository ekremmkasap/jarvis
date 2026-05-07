import sys
import types

from server.skills import telegram_tts_reply
from server.skills import telegram_voice_handler
from server.skills import whisper_skill


def test_handle_voice_message_transcribes(monkeypatch, tmp_path):
    audio_path = tmp_path / "voice.ogg"
    audio_path.write_bytes(b"ogg")
    calls = {}

    monkeypatch.setattr(
        telegram_voice_handler,
        "download_telegram_voice",
        lambda bot_token, file_id: (audio_path, {"file_path": "voice.ogg"}),
    )

    def fake_transcribe(path, language="tr"):
        calls["path"] = path
        calls["language"] = language
        return "Merhaba"

    monkeypatch.setitem(
        sys.modules,
        "whisper_skill",
        types.SimpleNamespace(transcribe_audio=fake_transcribe),
    )

    result = telegram_voice_handler.handle_voice_message(
        "token",
        {"voice": {"file_id": "abc", "duration": 10}, "chat": {"id": 1}},
    )

    assert result["ok"] is True
    assert result["text"] == "Merhaba"
    assert calls == {"path": str(audio_path), "language": "tr"}


def test_handle_voice_message_rejects_long_voice():
    result = telegram_voice_handler.handle_voice_message(
        "token",
        {"voice": {"file_id": "abc", "duration": 61}, "chat": {"id": 1}},
    )

    assert result["ok"] is False
    assert result["error"] == "voice_too_long"


def test_send_voice_reply_calls_bridge_and_cleans_temp(monkeypatch, tmp_path):
    voice_dir = tmp_path / "voice"
    voice_dir.mkdir()
    ogg_path = voice_dir / "reply.ogg"
    ogg_path.write_bytes(b"ogg")

    monkeypatch.setattr(
        telegram_tts_reply,
        "synthesize_voice_ogg",
        lambda text, voice=None: ogg_path,
    )

    sent = []

    class Bridge:
        def send_voice(self, chat_id, audio_path):
            sent.append((chat_id, audio_path))

    result = telegram_tts_reply.send_voice_reply(
        Bridge(),
        42,
        "Merhaba dunya",
        voice="AhmetNeural",
    )

    assert result is True
    assert sent == [(42, str(ogg_path))]
    assert not ogg_path.exists()
    assert not voice_dir.exists()


def test_whisper_skill_transcribe_audio_uses_groq_openai_sdk(monkeypatch, tmp_path):
    audio_path = tmp_path / "voice.ogg"
    audio_path.write_bytes(b"ogg")
    calls = {}

    class FakeTranscriptions:
        def create(self, **kwargs):
            calls["model"] = kwargs["model"]
            calls["language"] = kwargs["language"]
            calls["file_name"] = kwargs["file"].name
            return types.SimpleNamespace(text="Merhaba dunya")

    class FakeAudio:
        def __init__(self):
            self.transcriptions = FakeTranscriptions()

    class FakeOpenAI:
        def __init__(self, api_key, base_url):
            calls["api_key"] = api_key
            calls["base_url"] = base_url
            self.audio = FakeAudio()

    fake_openai_module = types.ModuleType("openai")
    fake_openai_module.OpenAI = FakeOpenAI

    monkeypatch.setenv("GROQ_API_KEY", "gsk_test")
    monkeypatch.setitem(sys.modules, "openai", fake_openai_module)
    monkeypatch.setattr(
        whisper_skill,
        "_transcribe_with_local_whisper",
        lambda source_path, language="tr": "fallback kullanilmamali",
    )

    result = whisper_skill.transcribe_audio(str(audio_path), language="tr")

    assert result == "Merhaba dunya"
    assert calls["api_key"] == "gsk_test"
    assert calls["base_url"] == whisper_skill.GROQ_BASE_URL
    assert calls["model"] == whisper_skill.GROQ_TRANSCRIPTION_MODEL
    assert calls["language"] == "tr"
    assert calls["file_name"].endswith("voice.ogg")
