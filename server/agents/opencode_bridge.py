"""
OpenCode Integration Bridge
JARVIS ve OpenCode arasında entegrasyon sağlar
"""
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from self_learning_orchestrator import SelfLearningOrchestrator
    from google_ai_studio_agent import GoogleAIStudioAgent
    HAS_SELF_LEARNING = True
except ImportError:
    HAS_SELF_LEARNING = False


class OpenCodeBridge:
    """
    OpenCode <-> JARVIS bridge

    OpenCode'dan gelen task'leri JARVIS'e yönlendirir
    JARVIS'in yeteneklerini OpenCode'a sunar
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or "server/config/opencode_bridge_config.json"
        self.config = self._load_config()

        # Initialize components
        self.self_learning = None
        self.google_ai = None

        if HAS_SELF_LEARNING:
            try:
                self.self_learning = SelfLearningOrchestrator()
                print("[OpenCodeBridge] Self-learning system initialized")
            except Exception as e:
                print(f"[OpenCodeBridge] Could not init self-learning: {e}")

        # Google AI (optional, requires API key)
        google_api_key = os.environ.get("GOOGLE_API_KEY")
        if google_api_key:
            try:
                self.google_ai = GoogleAIStudioAgent(google_api_key)
                print("[OpenCodeBridge] Google AI Studio initialized")
            except Exception as e:
                print(f"[OpenCodeBridge] Could not init Google AI: {e}")

        print("[OpenCodeBridge] Ready!")

    def _load_config(self) -> Dict:
        """Load configuration"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "enabled": True,
            "capabilities": {
                "self_learning": True,
                "google_ai": True,
                "web_search": True,
                "knowledge_rag": True
            }
        }

    # ============================================
    # OPENCODE -> JARVIS INTERFACE
    # ============================================

    def handle_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        OpenCode'dan gelen task'i handle et

        Task format:
        {
            "type": "query" | "learn" | "search" | "execute",
            "content": "...",
            "metadata": {...}
        }
        """
        task_type = task.get("type", "query")
        content = task.get("content", "")
        metadata = task.get("metadata", {})

        result = {
            "task_type": task_type,
            "timestamp": datetime.now().isoformat(),
            "success": False
        }

        try:
            if task_type == "query":
                # Answer with RAG
                result.update(self._handle_query(content, metadata))

            elif task_type == "learn":
                # Learn from web or Google AI
                result.update(self._handle_learn(content, metadata))

            elif task_type == "search":
                # Web search
                result.update(self._handle_search(content, metadata))

            elif task_type == "execute":
                # Execute command (careful!)
                result.update(self._handle_execute(content, metadata))

            else:
                result["error"] = f"Unknown task type: {task_type}"

        except Exception as e:
            result["error"] = str(e)

        return result

    def _handle_query(self, query: str, metadata: Dict) -> Dict:
        """Query with RAG enhancement"""
        if not self.self_learning:
            return {"error": "Self-learning system not available"}

        # Get RAG context
        rag_context = self.self_learning.get_rag_context(query)

        # If no context and Google AI available, generate knowledge
        if not rag_context and self.google_ai:
            print("[OpenCodeBridge] No RAG context found, generating with Google AI...")
            ai_result = self.google_ai.generate_knowledge(query, "explanation")
            if ai_result.get("success"):
                # Ingest into knowledge base
                self.self_learning.knowledge_manager.ingest_text(
                    text=ai_result["content"],
                    source="Google AI Studio",
                    metadata={"query": query}
                )
                rag_context = ai_result["content"]

        return {
            "success": True,
            "query": query,
            "rag_context": rag_context,
            "has_knowledge": len(rag_context) > 0 if rag_context else False
        }

    def _handle_learn(self, topic: str, metadata: Dict) -> Dict:
        """Learn from multiple sources"""
        if not self.self_learning:
            return {"error": "Self-learning system not available"}

        learn_source = metadata.get("source", "auto")

        if learn_source == "google_ai" and self.google_ai:
            # Learn from Google AI Studio
            ai_result = self.google_ai.learn_topic_deeply(topic)

            # Ingest into knowledge base
            ingested = 0
            for item in ai_result.get("knowledge_items", []):
                if item.get("success") and item.get("content"):
                    doc_id = self.self_learning.knowledge_manager.ingest_text(
                        text=item["content"],
                        source="Google AI Studio",
                        metadata={
                            "topic": topic,
                            "knowledge_type": item.get("knowledge_type")
                        }
                    )
                    if doc_id:
                        ingested += 1

            return {
                "success": True,
                "topic": topic,
                "source": "google_ai",
                "generated_items": len(ai_result.get("knowledge_items", [])),
                "ingested_count": ingested
            }

        else:
            # Default: learn from web
            result = self.self_learning.learn_from_query(topic)
            return {
                "success": result.get("learned", False),
                "topic": topic,
                "source": "web_crawler",
                "documents_added": result.get("documents_added", 0)
            }

    def _handle_search(self, query: str, metadata: Dict) -> Dict:
        """Web search"""
        if not self.self_learning or not self.self_learning.web_crawler:
            return {"error": "Web crawler not available"}

        web_data = self.self_learning.web_crawler.learn_from_query(query)

        return {
            "success": True,
            "query": query,
            "sources": web_data.get("sources", {})
        }

    def _handle_execute(self, command: str, metadata: Dict) -> Dict:
        """Execute system command (DANGEROUS - use with caution)"""
        # Safety check
        if not self.config.get("capabilities", {}).get("execute_commands", False):
            return {"error": "Command execution disabled for security"}

        # Add more safety checks here
        dangerous_commands = ["rm", "del", "format", "shutdown"]
        if any(cmd in command.lower() for cmd in dangerous_commands):
            return {"error": "Dangerous command blocked"}

        # Execute (not implemented for safety)
        return {"error": "Command execution not implemented"}

    # ============================================
    # JARVIS -> OPENCODE INTERFACE
    # ============================================

    def get_capabilities(self) -> Dict[str, Any]:
        """Return JARVIS capabilities for OpenCode"""
        return {
            "name": "JARVIS",
            "version": "1.0.0",
            "capabilities": {
                "self_learning": self.self_learning is not None,
                "google_ai": self.google_ai is not None,
                "web_search": self.self_learning is not None,
                "knowledge_rag": self.self_learning is not None,
                "voice_control": True,
                "pc_control": True
            },
            "supported_tasks": [
                "query",
                "learn",
                "search"
            ]
        }

    def get_system_stats(self) -> Dict[str, Any]:
        """System statistics"""
        stats = {
            "bridge": {
                "status": "active",
                "timestamp": datetime.now().isoformat()
            }
        }

        if self.self_learning:
            stats["self_learning"] = self.self_learning.get_system_stats()

        return stats


# ============================================
# CLI TEST
# ============================================
if __name__ == "__main__":
    import sys

    bridge = OpenCodeBridge()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "capabilities":
            print(json.dumps(bridge.get_capabilities(), indent=2))

        elif command == "stats":
            print(json.dumps(bridge.get_system_stats(), indent=2, ensure_ascii=False))

        elif command == "query" and len(sys.argv) > 2:
            query = " ".join(sys.argv[2:])
            task = {"type": "query", "content": query}
            result = bridge.handle_task(task)
            print(json.dumps(result, indent=2, ensure_ascii=False))

        elif command == "learn" and len(sys.argv) > 2:
            topic = " ".join(sys.argv[2:])
            task = {
                "type": "learn",
                "content": topic,
                "metadata": {"source": "google_ai"}  # or "web"
            }
            result = bridge.handle_task(task)
            print(json.dumps(result, indent=2, ensure_ascii=False))

        else:
            print("Usage:")
            print("  python opencode_bridge.py capabilities")
            print("  python opencode_bridge.py stats")
            print("  python opencode_bridge.py query <question>")
            print("  python opencode_bridge.py learn <topic>")

    else:
        print("OpenCode Bridge initialized!")
        print(json.dumps(bridge.get_capabilities(), indent=2))
