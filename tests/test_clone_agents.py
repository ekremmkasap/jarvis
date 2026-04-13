from pathlib import Path

def test_clone_files_exist():
    clones = ["seda","mert","buse","eren","luna","sabrican","sabri"]
    for c in clones:
        assert Path(f"server/agents/clones/{c}/core/prompt.txt").exists()
        assert Path(f"server/agents/clones/{c}/agent.py").exists()

def test_base_clone_no_key_leak():
    # BaseClone think() metodunda api_key string'i
    # return değerinde veya print'te çıkmamalı
    import inspect
    from server.agents.clones.base_clone import BaseClone
    src = inspect.getsource(BaseClone.think)
    assert "print(api_key)" not in src
    assert "log.info(api_key)" not in src

def test_env_keys_in_example():
    example = Path(".env.example").read_text(encoding="utf-8", errors="ignore")
    for k in ["GEMINI_KEY_SEDA","GEMINI_KEY_MERT","GEMINI_KEY_BUSE",
              "GEMINI_KEY_EREN","GEMINI_KEY_LUNA","GEMINI_KEY_SABRICAN","GEMINI_KEY_SABRI"]:
        assert k in example
