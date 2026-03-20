import os
import glob
import logging

log = logging.getLogger("claude_agents")

# Dinamik olarak agent_prompts klasörünü bul (Windows ve Linux uyumlu)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_DIR = os.path.join(BASE_DIR, "agent_prompts")
_agents_cache = {}

def refresh_agents():
    global _agents_cache
    _agents_cache = {}
    if not os.path.exists(AGENT_DIR):
        os.makedirs(AGENT_DIR, exist_ok=True)
        log.warning(f"{AGENT_DIR} bulunamadi, olusturuldu.")
        
    for root, dirs, files in os.walk(AGENT_DIR):
        for file in files:
            if file.endswith(".md") and file.lower() != "readme.md":
                path = os.path.join(root, file)
                name = os.path.splitext(file)[0].lower()
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read().strip()
                if len(content) > 20: 
                    # If same name exists, we prefix it by parent dir
                    if name in _agents_cache:
                        parent = os.path.basename(root).lower()
                        name = f"{parent}/{name}"
                    _agents_cache[name] = content
                    
    log.info(f"Loaded {len(_agents_cache)} zero-shot agent prompts from GitHub sources.")

def list_all_agents():
    if not _agents_cache:
        refresh_agents()
    return list(_agents_cache.keys())

def get_agent_prompt(query):
    if not _agents_cache:
        refresh_agents()
        
    query = query.lower()
    
    prompt = None

    # Exact match
    if query in _agents_cache:
        prompt = _agents_cache[query]
    else:
        # Partial match
        matches = [k for k in _agents_cache.keys() if query in k]
        if matches:
            prompt = _agents_cache[matches[0]]
            
    if prompt:
        prompt += "\n\n[SISTEM ONAYI]: Artik aktif edildin. BUNDAN SONRAKI BUTUN YANITLARINI (kodlar, aciklamalar, analizler) YALNIZCA TURKCE (Turkish) OLARAK VERMELISIN. Baska bir dil kullanma."
        
    return prompt

refresh_agents()
