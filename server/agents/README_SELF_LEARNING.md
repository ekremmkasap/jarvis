# JARVIS Self-Learning System

## 🧠 Genel Bakış

JARVIS artık **kendi kendine öğrenebilen** bir AI asistanı! Web'den, Google AI Studio'dan veri çekerek kendini sürekli geliştiriyor.

## 🎯 Özellikler

### 1. **Web Crawler Agent** (`web_crawler_agent.py`)
- Google/DuckDuckGo arama
- Wikipedia API
- GitHub API
- Stack Overflow API
- Otomatik cache sistemi

### 2. **Knowledge Manager Agent** (`knowledge_manager_agent.py`)
- ChromaDB vector database
- Sentence Transformers embeddings
- RAG (Retrieval Augmented Generation)
- Semantik arama

### 3. **Google AI Studio Agent** (`google_ai_studio_agent.py`)
- Gemini 2.0 Flash entegrasyonu
- Otomatik knowledge generation
- Multiple knowledge types:
  - Explanation (Açıklama)
  - Tutorial (Eğitim)
  - Examples (Örnekler)
  - Troubleshooting (Sorun giderme)

### 4. **Self-Learning Orchestrator** (`self_learning_orchestrator.py`)
- Tüm agentları koordine eder
- Otomatik öğrenme döngüsü
- RAG-enhanced responses

### 5. **OpenCode Bridge** (`opencode_bridge.py`)
- OpenCode <-> JARVIS entegrasyonu
- Task routing
- Capabilities API

## 📦 Kurulum

### Dependencies
```bash
pip install chromadb sentence-transformers beautifulsoup4 requests google-generativeai
```

### API Keys (.env)
```.env
# Optional: Google AI Studio için
GOOGLE_API_KEY=your_api_key_here
```

## 🚀 Kullanım

### 1. Web'den Öğrenme
```bash
python server/agents/self_learning_orchestrator.py learn "Python async await nasıl kullanılır"
```

### 2. RAG Query (Bilgi Sorgulama)
```bash
python server/agents/self_learning_orchestrator.py query "Python'da async nedir?"
```

### 3. Google AI Studio ile Öğrenme
```bash
python server/agents/google_ai_studio_agent.py integrate "Python async programming"
```

### 4. OpenCode Bridge
```bash
# Capabilities
python server/agents/opencode_bridge.py capabilities

# Query
python server/agents/opencode_bridge.py query "Python async nedir?"

# Learn
python server/agents/opencode_bridge.py learn "Rust ownership model"
```

### 5. System Stats
```bash
python server/agents/self_learning_orchestrator.py stats
```

## 🔄 Continuous Learning Loop

```
Kullanıcı Sorusu
      ↓
RAG Context Ara
      ↓
Bilgi Var mı? ──→ EVET ──→ Context ile Yanıt Ver
      ↓
     HAYIR
      ↓
Web + Google AI Studio'dan Öğren
      ↓
Vector DB'ye Kaydet
      ↓
Context ile Yanıt Ver
```

## 📊 Architecture

```
┌─────────────────────────────────────────────┐
│         Self-Learning Orchestrator          │
│                                             │
│  ┌─────────────┐  ┌──────────────────┐    │
│  │ Web Crawler │  │  Google AI       │    │
│  │   Agent     │  │  Studio Agent    │    │
│  └──────┬──────┘  └────────┬─────────┘    │
│         │                  │               │
│         └──────┬───────────┘               │
│                ↓                           │
│    ┌───────────────────────┐              │
│    │  Knowledge Manager    │              │
│    │  (ChromaDB + RAG)     │              │
│    └───────────────────────┘              │
└─────────────────────────────────────────────┘
                ↕
    ┌───────────────────────┐
    │   OpenCode Bridge     │
    │  (Integration Layer)  │
    └───────────────────────┘
```

## 🎮 Integration with JARVIS Voice

`hey_jarvis.py` dosyasını self-learning ile entegre etmek için:

```python
# hey_jarvis.py içinde
from server.agents.self_learning_orchestrator import SelfLearningOrchestrator

# Init
orchestrator = SelfLearningOrchestrator()

# ask_llm fonksiyonunda RAG context ekle
def ask_llm(text: str, image_b64: str = None) -> str:
    # RAG context al
    rag_context = orchestrator.get_rag_context(text)

    # Bilgi yoksa öğren
    if not rag_context:
        orchestrator.learn_from_query(text)
        rag_context = orchestrator.get_rag_context(text)

    # LLM'e RAG context ile birlikte gönder
    full_prompt = f"{rag_context}\n\nEkrem: {text}\nJarvis:"
    # ... rest of LLM call
```

## 📁 File Structure

```
server/
├── agents/
│   ├── web_crawler_agent.py         # Web scraping
│   ├── knowledge_manager_agent.py   # Vector DB + RAG
│   ├── google_ai_studio_agent.py    # Google AI integration
│   ├── self_learning_orchestrator.py # Main orchestrator
│   ├── opencode_bridge.py           # OpenCode integration
│   └── README_SELF_LEARNING.md      # This file
├── config/
│   └── self_learning_config.json    # Configuration
└── knowledge_base/
    ├── vector_db/                   # ChromaDB storage
    ├── web_scraped/                 # Web cache
    └── google_ai_studio/            # Google AI cache
```

## 🔧 Configuration

`server/config/self_learning_config.json`:
```json
{
  "web_crawler": {
    "enabled": true,
    "rate_limits": {
      "google": 1,
      "wikipedia": 2,
      "github": 5,
      "stackoverflow": 2
    }
  },
  "knowledge_manager": {
    "enabled": true,
    "rag_enabled": true,
    "rag_top_k": 5,
    "rag_max_context_tokens": 2000
  },
  "continuous_learning": {
    "enabled": true,
    "learn_on_query": true,
    "learn_on_error": true
  }
}
```

## 🎯 Use Cases

### 1. Coding Assistant
```bash
python server/agents/opencode_bridge.py learn "Python decorators"
python server/agents/opencode_bridge.py query "Python'da decorator nasıl yazılır?"
```

### 2. Tech Support
```bash
python server/agents/opencode_bridge.py learn "Windows 11 performance optimization"
python server/agents/opencode_bridge.py query "Bilgisayarım neden yavaş?"
```

### 3. Learning New Tech
```bash
python server/agents/google_ai_studio_agent.py integrate "Rust programming"
python server/agents/opencode_bridge.py query "Rust'ta ownership nedir?"
```

## 📈 Performance

- **Web Crawler**: ~2-3 saniye per query
- **Google AI Studio**: ~3-5 saniye per topic
- **RAG Query**: <1 saniye
- **Vector DB**: ChromaDB (disk-based, persistent)

## 🔒 Security

- Google API key env variable'da saklanır
- Web scraping rate limiting ile yapılır
- Command execution default olarak disabled

## 🚧 Roadmap

- [x] Web crawler integration
- [x] ChromaDB + RAG
- [x] Google AI Studio integration
- [x] OpenCode bridge
- [ ] Voice assistant integration
- [ ] Auto-training loop (ReAct style)
- [ ] Multi-modal learning (images, videos)
- [ ] Fine-tuning local models

## 🤝 OpenCode Compatibility

OpenCode agent'ları bu bridge üzerinden JARVIS yeteneklerini kullanabilir:

```python
# OpenCode agent içinde
import requests

response = requests.post("http://localhost:5000/jarvis/task", json={
    "type": "learn",
    "content": "Docker containers",
    "metadata": {"source": "google_ai"}
})
```

## 📝 Examples

### Example 1: Learn and Query
```bash
# Öğren
python server/agents/self_learning_orchestrator.py learn "FastAPI tutorial"

# Sorgula
python server/agents/self_learning_orchestrator.py query "FastAPI ile API nasıl yazılır?"
```

### Example 2: Google AI Deep Learning
```bash
export GOOGLE_API_KEY="your_key"
python server/agents/google_ai_studio_agent.py integrate "Machine Learning basics"
```

### Example 3: Full Pipeline
```bash
# 1. Learn from web
python server/agents/web_crawler_agent.py "Kubernetes"

# 2. Learn from Google AI
python server/agents/google_ai_studio_agent.py integrate "Kubernetes"

# 3. Query with RAG
python server/agents/opencode_bridge.py query "Kubernetes nedir?"
```

## 🎉 Başarı Kriterleri

✅ Web'den otomatik veri toplama
✅ Vector DB'ye kaydetme
✅ Semantik arama (RAG)
✅ Google AI Studio entegrasyonu
✅ OpenCode bridge
🔄 Voice assistant entegrasyonu (devam ediyor)

---

**Made with ❤️ by Ekrem & Claude Code**
