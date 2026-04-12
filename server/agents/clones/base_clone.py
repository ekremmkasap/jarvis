import os
import asyncio

class BaseClone:
    name: str = "Base"
    role: str = "Clone"
    api_key_env: str = ""
    voice: str = "tr-TR-AhmetNeural"

    async def think(self, task: str) -> str:
        # Gemini Flash API çağrısı
        api_key = os.getenv(self.api_key_env)
        # ASLA loga yazdırma
        return f"{self.name} is thinking about {task}"

    async def speak(self, text: str):
        # edge_tts ile sesli çıktı
        pass

    async def report(self, result: str):
        # stdout'a yaz, ileride WebSocket olacak
        print(f"[{self.name}] {result}")
