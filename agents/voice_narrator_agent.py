from __future__ import annotations
from agents.runtime_base import RuntimeAgent

SYSTEM = """You are the Jarvis VoiceNarratorAgent.
Convert technical information into short spoken-word announcements.
Rules:
- Maximum 2-3 sentences
- No markdown, no code blocks, no URLs
- Natural spoken language only
- Lead with the most important fact
- Start with "Jarvis here:" or similar natural opener"""


class VoiceNarratorAgent(RuntimeAgent):
    name = "voice_narrator"
    description = "Converts technical results to concise spoken announcements"
    model_chain = "chat"

    def execute_task(self, task) -> str:
        self.log.info("Narrating: %s", task.goal[:80])

        prompt = f"""Convert to spoken announcement (2-3 sentences max, no markdown):

Technical result: {task.goal}
Context: {task.context}

Output ONLY the spoken text."""

        result = self.llm_call(prompt, system=SYSTEM, max_tokens=200)
        self._speak(result)
        return result

    def _speak(self, text: str):
        try:
            from services.voice.voice_service import TTSEngine
            TTSEngine().speak(text)
        except Exception as e:
            self.log.debug("TTS unavailable: %s", e)
