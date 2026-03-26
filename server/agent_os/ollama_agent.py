"""
Ollama Local LLM Agent
Gece otomasyonu için local LLM kullanımı
"""
import json
import requests
from typing import Dict, Any, Optional, List


class OllamaAgent:
    """
    Ollama local LLM integration
    """

    def __init__(self, base_url: str = "http://127.0.0.1:11434"):
        self.base_url = base_url
        self.default_model = "qwen3-vl:235b-cloud"

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """
        Generate response from Ollama
        """
        model = model or self.default_model

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }

        if system:
            payload["system"] = system

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=120
            )
            response.raise_for_status()

            data = response.json()
            return data.get("response", "")

        except Exception as e:
            return f"Error: {e}"

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7
    ) -> str:
        """
        Chat completion with Ollama
        """
        model = model or self.default_model

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }

        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=120
            )
            response.raise_for_status()

            data = response.json()
            return data.get("message", {}).get("content", "")

        except Exception as e:
            return f"Error: {e}"

    def analyze_code(self, code: str, analysis_type: str = "quality") -> str:
        """
        Code analysis
        """
        prompts = {
            "quality": f"""Analyze this code for quality issues:
- Code smell
- Best practices violations
- Potential bugs
- Performance issues

Code:
{code}

Provide a concise analysis in Turkish.""",

            "improvements": f"""Suggest improvements for this code:
- Refactoring opportunities
- Better patterns
- Optimization possibilities

Code:
{code}

Provide actionable suggestions in Turkish.""",

            "security": f"""Security analysis for this code:
- Vulnerabilities
- Unsafe practices
- Security best practices

Code:
{code}

Provide security assessment in Turkish."""
        }

        prompt = prompts.get(analysis_type, prompts["quality"])

        return self.generate(
            prompt=prompt,
            system="You are an expert code reviewer. Provide concise, actionable feedback.",
            temperature=0.5
        )

    def generate_docs(self, code: str, doc_type: str = "comprehensive") -> str:
        """
        Generate documentation
        """
        prompt = f"""Generate comprehensive documentation for this code:

Code:
{code}

Include:
- Overview
- Functions/Classes description
- Parameters and return values
- Usage examples
- Edge cases

Write in Turkish, use markdown format."""

        return self.generate(
            prompt=prompt,
            system="You are a technical documentation expert.",
            temperature=0.6
        )

    def research_topic(self, topic: str) -> str:
        """
        Research a technical topic
        """
        prompt = f"""Explain '{topic}' in detail:

1. Clear definition
2. Key concepts
3. Practical examples
4. Best practices
5. Common pitfalls

Write in Turkish."""

        return self.generate(
            prompt=prompt,
            system="You are a programming expert and educator.",
            temperature=0.7,
            max_tokens=3000
        )

    def health_check(self) -> Dict[str, Any]:
        """
        Check Ollama health
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()

            models = response.json().get("models", [])

            return {
                "status": "healthy",
                "available_models": [m["name"] for m in models],
                "total_models": len(models)
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# ============================================
# CLI TEST
# ============================================
if __name__ == "__main__":
    import sys

    agent = OllamaAgent()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "health":
            result = agent.health_check()
            print(json.dumps(result, indent=2))

        elif command == "analyze" and len(sys.argv) > 2:
            code_file = sys.argv[2]
            with open(code_file, 'r', encoding='utf-8') as f:
                code = f.read()

            analysis = agent.analyze_code(code, "quality")
            print(analysis)

        elif command == "research" and len(sys.argv) > 2:
            topic = " ".join(sys.argv[2:])
            result = agent.research_topic(topic)
            print(result)

        else:
            print("Usage:")
            print("  python ollama_agent.py health")
            print("  python ollama_agent.py analyze <file>")
            print("  python ollama_agent.py research <topic>")

    else:
        print("Ollama Agent initialized")
        print(json.dumps(agent.health_check(), indent=2))
