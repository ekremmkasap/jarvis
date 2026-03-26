"""
JARVIS Knowledge Manager Agent
Vector DB + RAG implementation using ChromaDB
"""
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

import chromadb
from sentence_transformers import SentenceTransformer


class KnowledgeManagerAgent:
    """
    Vector database ile bilgi saklama ve RAG
    """

    def __init__(self, db_path: str = "server/knowledge_base/vector_db"):
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)

        print(f"[KnowledgeManager] Initializing ChromaDB at {self.db_path}")

        # ChromaDB setup
        self.chroma_client = chromadb.PersistentClient(path=str(self.db_path))
        self.collection = self.chroma_client.get_or_create_collection(
            name="jarvis_knowledge",
            metadata={"description": "JARVIS learned knowledge from web and interactions"}
        )

        # Embedding model
        print("[KnowledgeManager] Loading embedding model...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

        print("[KnowledgeManager] Ready!")

    def _generate_doc_id(self, text: str, source: str) -> str:
        """Unique ID for document"""
        content = f"{source}:{text[:100]}"
        return hashlib.md5(content.encode()).hexdigest()

    def ingest_text(
        self,
        text: str,
        source: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Tek bir text parçasını vector DB'ye ekle
        """
        if not text or len(text.strip()) < 10:
            return None

        doc_id = self._generate_doc_id(text, source)

        # Embedding oluştur
        embedding = self.embedding_model.encode(text).tolist()

        # Metadata hazırla
        doc_metadata = {
            "source": source,
            "timestamp": datetime.now().isoformat(),
            "char_count": len(text)
        }
        if metadata:
            doc_metadata.update(metadata)

        try:
            self.collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[text],
                metadatas=[doc_metadata]
            )
            return doc_id
        except Exception as e:
            print(f"[KnowledgeManager] Error ingesting text: {e}")
            return None

    def ingest_web_results(self, web_data: Dict[str, Any]) -> int:
        """
        Web crawler sonuçlarını toplu olarak ekle
        """
        count = 0
        sources = web_data.get("sources", {})

        for source_name, results in sources.items():
            if not results:
                continue

            for item in results:
                if isinstance(item, dict):
                    # Extract text content
                    text_parts = []

                    if "title" in item:
                        text_parts.append(f"Title: {item['title']}")
                    if "description" in item or "snippet" in item:
                        text_parts.append(item.get("description") or item.get("snippet", ""))
                    if "extract" in item:
                        text_parts.append(item["extract"])
                    if "content" in item:
                        text_parts.append(item["content"])

                    text = "\n".join(text_parts).strip()

                    if text:
                        source_url = item.get("url") or item.get("link") or source_name

                        metadata = {
                            "source_type": source_name,
                            "url": source_url
                        }

                        # Add optional fields
                        if "stars" in item:
                            metadata["stars"] = item["stars"]
                        if "language" in item:
                            metadata["language"] = item["language"]

                        doc_id = self.ingest_text(text, source_url, metadata)
                        if doc_id:
                            count += 1

        print(f"[KnowledgeManager] Ingested {count} documents from web results")
        return count

    def query(self, text: str, n_results: int = 5) -> List[Dict]:
        """
        RAG query: benzer dökümanları bul
        """
        if not text:
            return []

        query_embedding = self.embedding_model.encode(text).tolist()

        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )

            # Format results
            formatted = []
            if results and results.get('documents'):
                docs = results['documents'][0] if results['documents'] else []
                metadatas = results['metadatas'][0] if results.get('metadatas') else []
                distances = results['distances'][0] if results.get('distances') else []

                for i, doc in enumerate(docs):
                    formatted.append({
                        "text": doc,
                        "metadata": metadatas[i] if i < len(metadatas) else {},
                        "distance": distances[i] if i < len(distances) else None
                    })

            return formatted
        except Exception as e:
            print(f"[KnowledgeManager] Query error: {e}")
            return []

    def get_context_for_llm(self, query: str, max_tokens: int = 2000) -> str:
        """
        LLM için RAG context string oluştur
        """
        results = self.query(query, n_results=5)

        if not results:
            return ""

        context_parts = []
        total_chars = 0

        for item in results:
            text = item["text"]
            source = item["metadata"].get("url", "Unknown")

            # Approximate token count (1 token ≈ 4 chars)
            estimated_tokens = len(text) // 4

            if total_chars + estimated_tokens > max_tokens:
                break

            context_parts.append(f"[Source: {source}]\n{text}")
            total_chars += estimated_tokens

        return "\n\n---\n\n".join(context_parts)

    def get_stats(self) -> Dict[str, Any]:
        """Vector DB istatistikleri"""
        try:
            count = self.collection.count()
            return {
                "total_documents": count,
                "collection_name": self.collection.name,
                "db_path": str(self.db_path)
            }
        except Exception as e:
            return {"error": str(e)}


# ============================================
# CLI TEST
# ============================================
if __name__ == "__main__":
    import sys

    km = KnowledgeManagerAgent()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "stats":
            stats = km.get_stats()
            print(json.dumps(stats, indent=2))

        elif command == "add" and len(sys.argv) > 3:
            text = sys.argv[2]
            source = sys.argv[3]
            doc_id = km.ingest_text(text, source)
            print(f"Added document: {doc_id}")

        elif command == "query" and len(sys.argv) > 2:
            query = " ".join(sys.argv[2:])
            results = km.query(query, n_results=3)
            print(json.dumps(results, indent=2, ensure_ascii=False))

        elif command == "context" and len(sys.argv) > 2:
            query = " ".join(sys.argv[2:])
            context = km.get_context_for_llm(query)
            print(context)

        else:
            print("Usage:")
            print("  python knowledge_manager_agent.py stats")
            print("  python knowledge_manager_agent.py add 'text' 'source'")
            print("  python knowledge_manager_agent.py query <query>")
            print("  python knowledge_manager_agent.py context <query>")
    else:
        print(f"Knowledge Manager initialized. Stats: {km.get_stats()}")
