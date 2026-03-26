"""
Google AI Studio Integration Agent
Google AI Studio'dan veri çeker ve knowledge base'e ekler
"""
import json
import os
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False
    print("[GoogleAI] Warning: google-generativeai not installed")


class GoogleAIStudioAgent:
    """
    Google AI Studio ile entegrasyon
    """

    def __init__(self, api_key: Optional[str] = None):
        if not HAS_GEMINI:
            raise ImportError("google-generativeai is required. Install: pip install google-generativeai")

        # API key
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment or constructor")

        # Configure Gemini
        genai.configure(api_key=self.api_key)

        # Model setup
        self.model_name = "gemini-2.0-flash-exp"
        self.model = genai.GenerativeModel(self.model_name)

        # Cache directory
        self.cache_dir = Path("server/knowledge_base/google_ai_studio")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        print(f"[GoogleAI] Initialized with model: {self.model_name}")

    def generate_knowledge(
        self,
        topic: str,
        knowledge_type: str = "explanation",
        max_tokens: int = 2000
    ) -> Dict[str, Any]:
        """
        Topic hakkında bilgi üret

        knowledge_type:
        - explanation: Detaylı açıklama
        - tutorial: Adım adım öğretici
        - examples: Kod örnekleri
        - comparison: Karşılaştırma
        - troubleshooting: Sorun giderme
        """

        prompts = {
            "explanation": f"""Explain '{topic}' in detail. Provide:
1. Clear definition
2. Key concepts
3. Use cases
4. Best practices
5. Common pitfalls

Be comprehensive but concise. Use Turkish if the query is in Turkish.""",

            "tutorial": f"""Create a step-by-step tutorial for '{topic}':
1. Prerequisites
2. Step-by-step instructions with code examples
3. Explanation of each step
4. Testing and validation
5. Next steps

Use Turkish if the query is in Turkish.""",

            "examples": f"""Provide practical code examples for '{topic}':
1. Basic example
2. Intermediate example
3. Advanced example
4. Real-world use case

Include comments explaining the code. Use Turkish if the query is in Turkish.""",

            "comparison": f"""Compare and contrast different approaches related to '{topic}':
1. Option A vs Option B
2. Pros and cons of each
3. When to use which
4. Performance considerations

Use Turkish if the query is in Turkish.""",

            "troubleshooting": f"""Common problems and solutions for '{topic}':
1. Frequent errors
2. Debugging steps
3. Solutions
4. Prevention tips

Use Turkish if the query is in Turkish."""
        }

        prompt = prompts.get(knowledge_type, prompts["explanation"])

        try:
            print(f"[GoogleAI] Generating {knowledge_type} for: '{topic}'")

            # Generate content
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "max_output_tokens": max_tokens,
                    "temperature": 0.7,
                }
            )

            result = {
                "topic": topic,
                "knowledge_type": knowledge_type,
                "content": response.text,
                "timestamp": datetime.now().isoformat(),
                "model": self.model_name,
                "success": True
            }

            # Cache result
            self._cache_result(topic, knowledge_type, result)

            print(f"[GoogleAI] Generated {len(response.text)} chars")
            return result

        except Exception as e:
            print(f"[GoogleAI] Error generating knowledge: {e}")
            return {
                "topic": topic,
                "knowledge_type": knowledge_type,
                "error": str(e),
                "success": False
            }

    def learn_topic_deeply(self, topic: str) -> Dict[str, Any]:
        """
        Bir topic hakkında çoklu knowledge türleri üret
        """
        print(f"\n[GoogleAI] DEEP LEARNING SESSION: {topic}")
        print("=" * 60)

        results = {
            "topic": topic,
            "timestamp": datetime.now().isoformat(),
            "knowledge_items": []
        }

        # Multiple knowledge types
        knowledge_types = ["explanation", "examples", "troubleshooting"]

        for k_type in knowledge_types:
            result = self.generate_knowledge(topic, k_type, max_tokens=1500)
            if result.get("success"):
                results["knowledge_items"].append(result)
                time.sleep(1)  # Rate limiting

        print(f"\n[GoogleAI] Deep learning complete: {len(results['knowledge_items'])} items")
        return results

    def answer_question(self, question: str, context: str = "") -> str:
        """
        Soru-cevap
        """
        prompt = question
        if context:
            prompt = f"""Context:\n{context}\n\nQuestion: {question}\n\nProvide a clear, accurate answer based on the context and your knowledge."""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "max_output_tokens": 500,
                    "temperature": 0.5,
                }
            )
            return response.text
        except Exception as e:
            return f"Error: {e}"

    def _cache_result(self, topic: str, knowledge_type: str, result: Dict):
        """Cache sonucu kaydet"""
        safe_topic = "".join(c for c in topic if c.isalnum() or c in " _-")[:50]
        filename = f"{safe_topic}_{knowledge_type}_{int(time.time())}.json"
        path = self.cache_dir / filename

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"[GoogleAI] Cached: {filename}")

    def get_cached_knowledge(self, topic: str = None) -> List[Dict]:
        """Cache'den bilgi çek"""
        results = []
        for file in self.cache_dir.glob("*.json"):
            if topic:
                safe_topic = "".join(c for c in topic if c.isalnum() or c in " _-")[:50]
                if safe_topic.lower() not in file.name.lower():
                    continue

            with open(file, 'r', encoding='utf-8') as f:
                results.append(json.load(f))

        return results


# ============================================
# INTEGRATION WITH KNOWLEDGE MANAGER
# ============================================
def integrate_with_knowledge_base(
    topic: str,
    api_key: Optional[str] = None,
    knowledge_manager = None
) -> Dict[str, Any]:
    """
    Google AI Studio'dan öğren ve Knowledge Base'e ekle
    """
    google_ai = GoogleAIStudioAgent(api_key)

    # Deep learning
    deep_results = google_ai.learn_topic_deeply(topic)

    # Knowledge Manager'a ekle
    if knowledge_manager:
        from knowledge_manager_agent import KnowledgeManagerAgent

        if not isinstance(knowledge_manager, KnowledgeManagerAgent):
            knowledge_manager = KnowledgeManagerAgent()

        ingested_count = 0
        for item in deep_results["knowledge_items"]:
            if item.get("success") and item.get("content"):
                doc_id = knowledge_manager.ingest_text(
                    text=item["content"],
                    source=f"Google AI Studio - {item['knowledge_type']}",
                    metadata={
                        "topic": topic,
                        "knowledge_type": item["knowledge_type"],
                        "model": item.get("model", "unknown")
                    }
                )
                if doc_id:
                    ingested_count += 1

        print(f"\n[Integration] Added {ingested_count} documents to knowledge base")

        return {
            "topic": topic,
            "generated_items": len(deep_results["knowledge_items"]),
            "ingested_count": ingested_count,
            "success": True
        }

    return deep_results


# ============================================
# CLI TEST
# ============================================
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python google_ai_studio_agent.py learn <topic>")
        print("  python google_ai_studio_agent.py question '<question>'")
        print("  python google_ai_studio_agent.py integrate <topic>")
        print("\nSet GOOGLE_API_KEY environment variable first!")
        sys.exit(1)

    command = sys.argv[1]

    if command == "learn" and len(sys.argv) > 2:
        topic = " ".join(sys.argv[2:])
        agent = GoogleAIStudioAgent()
        result = agent.learn_topic_deeply(topic)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif command == "question" and len(sys.argv) > 2:
        question = " ".join(sys.argv[2:])
        agent = GoogleAIStudioAgent()
        answer = agent.answer_question(question)
        print(f"\nAnswer:\n{answer}")

    elif command == "integrate" and len(sys.argv) > 2:
        topic = " ".join(sys.argv[2:])
        result = integrate_with_knowledge_base(topic, knowledge_manager=True)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    else:
        print("Invalid command. See usage.")
