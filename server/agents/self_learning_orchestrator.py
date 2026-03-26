"""
JARVIS Self-Learning Orchestrator
Web Crawler + Knowledge Manager + Auto-Trainer koordinasyonu
"""
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

import sys
import os

# Add agents directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from web_crawler_agent import WebCrawlerAgent
    from knowledge_manager_agent import KnowledgeManagerAgent
except ImportError:
    # Fallback: try importing from current directory
    import importlib.util

    web_crawler_path = os.path.join(current_dir, 'web_crawler_agent.py')
    spec = importlib.util.spec_from_file_location("web_crawler_agent", web_crawler_path)
    web_crawler_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(web_crawler_module)
    WebCrawlerAgent = web_crawler_module.WebCrawlerAgent

    km_path = os.path.join(current_dir, 'knowledge_manager_agent.py')
    spec = importlib.util.spec_from_file_location("knowledge_manager_agent", km_path)
    km_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(km_module)
    KnowledgeManagerAgent = km_module.KnowledgeManagerAgent


class SelfLearningOrchestrator:
    """
    Self-learning sistemini orkestra eden ana agent
    """

    def __init__(self, config_path: str = "server/config/self_learning_config.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()

        # Sub-agents
        print("[SelfLearning] Initializing Web Crawler Agent...")
        self.web_crawler = WebCrawlerAgent()

        print("[SelfLearning] Initializing Knowledge Manager Agent...")
        self.knowledge_manager = KnowledgeManagerAgent(
            db_path=self.config["storage"]["vector_db_path"]
        )

        # Stats
        self.stats = {
            "total_queries_learned": 0,
            "total_documents_ingested": 0,
            "last_learning_session": None,
            "session_start_time": datetime.now().isoformat()
        }

        print("[SelfLearning] Orchestrator initialized!")

    def _load_config(self) -> Dict:
        """Config yükle"""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        print(f"[SelfLearning] Config not found: {self.config_path}")
        return {}

    # ============================================
    # CONTINUOUS LEARNING LOOP
    # ============================================
    def learn_from_query(self, query: str, user_context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Kullanıcı sorgusu geldiğinde öğrenme döngüsü başlat
        """
        if not self.config.get("continuous_learning", {}).get("learn_on_query", True):
            return {"learned": False, "reason": "learn_on_query disabled"}

        print(f"\n{'='*60}")
        print(f"[SelfLearning] LEARNING SESSION STARTED")
        print(f"Query: '{query}'")
        print(f"{'='*60}\n")

        start_time = time.time()
        result = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "steps": [],
            "learned": False
        }

        try:
            # STEP 1: Web'den bilgi topla
            print("[SelfLearning] STEP 1: Web crawling...")
            web_data = self.web_crawler.learn_from_query(query)
            result["steps"].append({
                "step": "web_crawling",
                "success": True,
                "sources_count": len(web_data.get("sources", {}))
            })

            # STEP 2: Knowledge base'e ekle
            print("\n[SelfLearning] STEP 2: Ingesting into knowledge base...")
            ingested_count = self.knowledge_manager.ingest_web_results(web_data)
            result["steps"].append({
                "step": "knowledge_ingestion",
                "success": True,
                "documents_ingested": ingested_count
            })

            # STEP 3: Stats güncelle
            self.stats["total_queries_learned"] += 1
            self.stats["total_documents_ingested"] += ingested_count
            self.stats["last_learning_session"] = datetime.now().isoformat()

            result["learned"] = True
            result["documents_added"] = ingested_count

        except Exception as e:
            print(f"[SelfLearning] ERROR in learning loop: {e}")
            result["steps"].append({
                "step": "error",
                "error": str(e)
            })

        elapsed_time = time.time() - start_time
        result["elapsed_seconds"] = round(elapsed_time, 2)

        print(f"\n{'='*60}")
        print(f"[SelfLearning] LEARNING SESSION COMPLETE")
        print(f"Documents added: {result.get('documents_added', 0)}")
        print(f"Time: {elapsed_time:.2f}s")
        print(f"{'='*60}\n")

        return result

    # ============================================
    # RAG-ENHANCED RESPONSE
    # ============================================
    def get_rag_context(self, query: str) -> str:
        """
        Query için RAG context getir
        """
        if not self.config.get("knowledge_manager", {}).get("rag_enabled", True):
            return ""

        print(f"[SelfLearning] Building RAG context for query: '{query[:50]}...'")
        context = self.knowledge_manager.get_context_for_llm(
            query,
            max_tokens=self.config.get("knowledge_manager", {}).get("rag_max_context_tokens", 2000)
        )
        return context

    def enhance_response_with_knowledge(self, query: str, base_response: str) -> Dict[str, Any]:
        """
        LLM yanıtını knowledge base ile zenginleştir
        """
        # RAG context al
        rag_context = self.get_rag_context(query)

        enhanced_response = {
            "base_response": base_response,
            "rag_context": rag_context,
            "has_knowledge": len(rag_context) > 0,
            "sources": []
        }

        # Context'ten source'ları çıkar
        if rag_context:
            lines = rag_context.split("\n\n")
            for line in lines:
                if "(Source:" in line:
                    source_url = line.split("(Source:")[-1].strip().rstrip(")")
                    enhanced_response["sources"].append(source_url)

        return enhanced_response

    # ============================================
    # STATS & MANAGEMENT
    # ============================================
    def get_system_stats(self) -> Dict[str, Any]:
        """Sistem istatistikleri"""
        kb_stats = self.knowledge_manager.get_stats()

        return {
            "orchestrator": self.stats,
            "knowledge_base": kb_stats,
            "config": {
                "web_crawler_enabled": self.config.get("web_crawler", {}).get("enabled", False),
                "knowledge_manager_enabled": self.config.get("knowledge_manager", {}).get("enabled", False),
                "continuous_learning_enabled": self.config.get("continuous_learning", {}).get("enabled", False)
            }
        }

    def health_check(self) -> Dict[str, bool]:
        """Sistem sağlık kontrolü"""
        return {
            "web_crawler": self.web_crawler is not None,
            "knowledge_manager": self.knowledge_manager is not None,
            "vector_db": self.knowledge_manager.collection is not None,
            "embedding_model": self.knowledge_manager.embedding_model is not None
        }

    # ============================================
    # INTEGRATION WITH AGENT OS
    # ============================================
    def process_user_request(self, user_query: str, learn: bool = True) -> Dict[str, Any]:
        """
        Agent OS'tan gelen request'i işle
        """
        result = {
            "query": user_query,
            "timestamp": datetime.now().isoformat(),
        }

        # 1. RAG context al (mevcut bilgilerden)
        rag_context = self.get_rag_context(user_query)
        result["rag_context"] = rag_context
        result["has_existing_knowledge"] = len(rag_context) > 0

        # 2. Eğer yeterli bilgi yoksa ve learn=True ise, öğren
        if learn and not result["has_existing_knowledge"]:
            print("[SelfLearning] No existing knowledge found. Starting learning session...")
            learning_result = self.learn_from_query(user_query)
            result["learning_session"] = learning_result

            # Yeni öğrenilen bilgilerle RAG context güncelle
            rag_context = self.get_rag_context(user_query)
            result["rag_context"] = rag_context
            result["has_existing_knowledge"] = len(rag_context) > 0

        return result


# ============================================
# CLI TEST
# ============================================
if __name__ == "__main__":
    import sys

    orchestrator = SelfLearningOrchestrator()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "stats":
            stats = orchestrator.get_system_stats()
            print(json.dumps(stats, indent=2, ensure_ascii=False))

        elif command == "health":
            health = orchestrator.health_check()
            print(json.dumps(health, indent=2))

        elif command == "learn" and len(sys.argv) > 2:
            query = " ".join(sys.argv[2:])
            result = orchestrator.learn_from_query(query)
            print(json.dumps(result, indent=2, ensure_ascii=False))

        elif command == "query" and len(sys.argv) > 2:
            query = " ".join(sys.argv[2:])
            result = orchestrator.process_user_request(query, learn=True)
            print(json.dumps(result, indent=2, ensure_ascii=False))

        else:
            print("Usage:")
            print("  python self_learning_orchestrator.py stats")
            print("  python self_learning_orchestrator.py health")
            print("  python self_learning_orchestrator.py learn <query>")
            print("  python self_learning_orchestrator.py query <query>")
    else:
        print("Self-Learning Orchestrator initialized.")
        print(f"Stats: {orchestrator.get_system_stats()}")
