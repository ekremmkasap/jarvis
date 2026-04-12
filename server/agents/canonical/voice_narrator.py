from __future__ import annotations

import re
from typing import Any

from .base import CanonicalAgent


class VoiceNarratorAgent(CanonicalAgent):
    agent_id = "voice_narrator"
    name = "VoiceNarratorAgent"
    role = "Short spoken Turkish summaries"
    model_chain = "chat"
    model_preference = "groq/llama-3.3-70b-versatile"

    async def _execute(self, task: str, context: dict[str, Any]) -> dict[str, Any]:
        raw_output = str(context.get("raw_output") or task).strip()
        narrated = self._call_llm(
            (
                "Teknik ciktiyi 2-3 kisa Turkce cumleye indir. "
                "Kod blogu, markdown, URL veya jargon kullanma. "
                f"Maksimum 200 karakter. Cikti:\n{raw_output[:4000]}"
            ),
            system="You are VoiceNarratorAgent. Return spoken Turkish only.",
            max_tokens=180,
        )
        tts_text = self._normalize_tts_text(narrated or raw_output)
        return {
            "tts_text": tts_text,
            "original_length": len(raw_output),
            "compressed_length": len(tts_text),
        }

    def _normalize_tts_text(self, text: str) -> str:
        cleaned = str(text or "").strip()
        cleaned = re.sub(r"```.*?```", " ", cleaned, flags=re.DOTALL)
        cleaned = re.sub(r"`([^`]*)`", r"\1", cleaned)
        cleaned = re.sub(r"https?://\S+", " ", cleaned)
        cleaned = re.sub(r"www\.\S+", " ", cleaned)
        cleaned = re.sub(r"[*_#>\[\]\(\)]", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        cleaned = cleaned.replace("JSON", "sonuc").replace("json", "sonuc")
        if not cleaned:
            cleaned = "Sonuc hazir."

        sentences = self._split_sentences(cleaned)
        if not sentences:
            sentences = ["Sonuc hazir."]

        condensed: list[str] = []
        for sentence in sentences:
            normalized = sentence.strip(" .,:;!-")
            if not normalized:
                continue
            normalized = normalized[0].upper() + normalized[1:]
            if not normalized.endswith("."):
                normalized += "."
            condensed.append(normalized)
            if len(condensed) == 3:
                break

        if not condensed:
            condensed = ["Sonuc hazir."]

        output = " ".join(condensed)
        if len(output) > 200:
            trimmed_sentences: list[str] = []
            current = ""
            for sentence in condensed:
                candidate = (current + " " + sentence).strip() if current else sentence
                if len(candidate) <= 200:
                    current = candidate
                    trimmed_sentences.append(sentence)
                else:
                    break
            output = current or condensed[0][:197].rstrip(" .,:;!-") + "."

        if len(output) > 200:
            output = output[:197].rstrip(" .,:;!-") + "."
        return output

    def _split_sentences(self, text: str) -> list[str]:
        parts = re.split(r"(?<=[.!?])\s+", text)
        if len(parts) == 1:
            comma_parts = [chunk.strip() for chunk in text.split(",") if chunk.strip()]
            return comma_parts
        return [part.strip() for part in parts if part.strip()]
