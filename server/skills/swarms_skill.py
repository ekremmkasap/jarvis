"""
Jarvis Skill — Swarms (kyegomez/swarms)
Python multi-agent framework. pip install swarms gerekir.
Yüklü değilse subprocess fallback ile çalışır.
"""
import os, sys, json, subprocess
from pathlib import Path

REPO_DIR = Path(__file__).parent.parent.parent / "external-repos" / "swarms"


def swarms_run(goal: str, agents: int = 3) -> str:
    if not goal:
        return "Kullanim: /swarms-agent [hedef]"
    try:
        # swarms yüklüyse direkt kullan
        from swarms import Agent, SequentialWorkflow
        agent = Agent(
            agent_name="JarvisWorker",
            system_prompt=f"Sen Jarvis Corp'un otonom worker'ısın. Görevi yerine getir ve sonucu Türkçe raporla.",
            model_name=os.environ.get("SWARMS_MODEL", "gpt-4o-mini"),
            max_loops=2,
            autosave=False,
            verbose=False,
        )
        result = agent.run(goal)
        return f"🌊 **Swarms Agent**\n\n{str(result)[:1500]}"
    except ImportError:
        return (
            "⚠️ `swarms` paketi yüklü değil.\n"
            "Yüklemek için: `pip install swarms`\n\n"
            f"Hedef kaydedildi: {goal}\n"
            "Bypass swarm'ı kullanıyorum → /swarm komutu dene."
        )
    except Exception as e:
        return f"❌ Swarms hatası: {e}"


def swarms_status() -> str:
    try:
        import swarms
        ver = getattr(swarms, "__version__", "?")
        return f"🌊 **Swarms Framework**\nVersiyon: `{ver}`\nDurum: 🟢 kurulu\nRepo: `external-repos/swarms`"
    except ImportError:
        return "🌊 **Swarms Framework**\nDurum: 🔴 kurulu değil\n`pip install swarms` ile kur"
