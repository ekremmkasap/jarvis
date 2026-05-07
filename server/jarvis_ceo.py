"""
jarvis_ceo.py
CEO modülü: Swarm ajanlarını yönetir ve görev başlatır.
/swarm-konuş komutlarının trigger noktasıdır.
"""

import asyncio
from typing import Optional

def get_engine():
    # Lazy import to avoid circular dependencies if any down the road
    from agents.clones.conversation_engine import ConversationEngine, route_keywords
    return ConversationEngine, route_keywords

def start_dialogue_sync(topic: str, rounds: int = 2) -> list[dict]:
    """Senkron sarıcı, CEO komutu ile tetiklenmek için kullanılır."""
    return asyncio.run(start_dialogue(topic, rounds))

async def start_dialogue(topic: str, rounds: int = 1) -> list[dict]:
    """
    Verilen konu (topic) üzerinde uygun ajanları seçip sesli diyalog başlatır.
    """
    ConversationEngine, route_keywords = get_engine()
    
    # Konuya göre ilgilenen ajanları seç
    participants = route_keywords(topic)
    
    print(f"[CEO] '{topic}' görevi başlatıldı.")
    print(f"[CEO] Katılımcılar: {', '.join(participants)}")
    
    engine = ConversationEngine()
    results = await engine.dialogue(topic, participants, rounds)
    
    print("[CEO] Diyalog tamamlandı. Sonuçlar loga yazıldı.")
    return results

if __name__ == "__main__":
    import sys
    topic = "Şirketin ana landing page yenilemesi ve güvenlik riskleri"
    if len(sys.argv) > 1:
        topic = " ".join(sys.argv[1:])
    
    results = start_dialogue_sync(topic, rounds=1)
    
    print("--- Diyalog Özeti ---")
    for r in results:
        print(f"{r['agent']}: {r['text']}")
