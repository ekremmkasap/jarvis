"""Tab-5 Dijital Ajan Dünyası V2 promptunu masaüstüne yazar."""
import pathlib

DESKTOP = pathlib.Path(r"C:\Users\sergen\Desktop")

CONTENT = """================================================================================
CODEX TAB-5 — Dijital Ajan Dünyası V2: Faz 0 + Faz 1 + Faz 2 + Faz 3
Repo: C:\\Users\\sergen\\Desktop\\jarvis-mission-control
Branch: 003-dijital-ajan-v2  (yoksa oluştur: git checkout -b 003-dijital-ajan-v2)
Mode: PLAN-FIRST -> AUTO-EXECUTE -> VALIDATE -> COMMIT -> CLAUDE.MD
================================================================================

YOU ARE: Elite AI Software Engineer + System Architect
LANGUAGE: Turkish for user output, English for code/paths
REPO: C:\\Users\\sergen\\Desktop\\jarvis-mission-control

================================================================================
ABSOLUTE RULES
================================================================================

1. CLAUDE.md oku — "Dijital Ajan Dunyasi V2" bölümünü anla
2. server/bridge.py BACKWARD-SAFE — mevcut endpoint'ler bozulmaz
3. hey_jarvis.py — sadece hook ekle, STT/TTS akışını bozma
4. state/ dosyaları atomic JSON write
5. NEVER push to main/master
6. Her slice sonrası pytest + commit + CLAUDE.md update
7. Electron renderer.js değişikliklerinde yeni npm paketi ekleme

================================================================================
CLAUDE.MD'DEN OKU — MİMARİ ÖZET
================================================================================

3 Katman:
  KATMAN 1 — PERSONA PLANE
    state/active_agent.json       — aktif persona
    config/agents.yaml            — 7 persona profili
    state/agent_world.json        — son aktivasyon + görev geçmişi
    server/agents/clones/[ajan]/memory/ — per-agent hafıza

  KATMAN 2 — RUNTIME PLANE
    server/bridge.py              — tek komut router
    hey_jarvis.py                 — tek TTS/STT
    apps/desktop-hologram/        — tek hologram

  KATMAN 3 — EXECUTION PLANE
    config/persona_execution_map.json — persona -> Codex slot
    server/codex_orchestrator.py

PERSONA RENK HARİTASI:
  jarvis    -> #00bfff
  seda      -> #00ff88
  mert      -> #ffdd00
  buse      -> #ff69b4
  eren      -> #ff8c00
  luna      -> #9b59b6
  sabrican  -> #95a5a6
  sabri     -> #e74c3c

PERSONA SES HARİTASI:
  buse, luna -> EmelNeural
  diğerleri  -> AhmetNeural

FAZ SIRASI:
  Faz 0: Bridge Recovery (BLOKER)
  Faz 1: Persona Switching + Greeting TTS
  Faz 2: Hologram Animated Transitions
  Faz 3: Per-Persona Skill Routing

================================================================================
FAZ 0: Bridge Recovery Check
================================================================================

1. bridge.py import kontrolü:
   python -c "
   import sys; sys.path.insert(0, 'server')
   import bridge
   print('bridge.py import: OK')
   "

2. bridge.py içinde /health endpoint kontrol et:
   grep -n '"/health"' server/bridge.py

   YOKSA ekle (GET handler bölümüne):
     elif path == "/health":
         self._json({"status": "ok", "version": "2.0", "service": "jarvis-bridge"})

3. Smoke:
   python -c "
   import sys; sys.path.insert(0, 'server')
   from bridge import JarvisHandler
   print('JarvisHandler import: OK')
   print('Faz 0: PASSED')
   "

Commit: "fix: bridge /health endpoint — Faz 0 verified"
CLAUDE.md: Faz 0 TAMAMLANDI

================================================================================
FAZ 1A: state/active_agent.json + PersonaManager
================================================================================

1. state/ klasörü yoksa oluştur.

2. state/active_agent.json yoksa oluştur:
   {
     "active": "jarvis",
     "switched_at": null,
     "previous": null,
     "switch_count": 0
   }

3. server/persona_manager.py YAZ:

from __future__ import annotations
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
ACTIVE_AGENT_PATH = ROOT / "state" / "active_agent.json"
AGENT_WORLD_PATH  = ROOT / "state" / "agent_world.json"

PERSONAS: dict[str, dict[str, Any]] = {
    "jarvis": {
        "role": "ana sistem",
        "color": "#00bfff",
        "voice": "AhmetNeural",
        "greeting": "JARVIS aktif. Nasıl yardımcı olabilirim?",
        "skills": ["genel", "yonlendirme", "koordinasyon"],
        "codex_slot": None,
    },
    "seda": {
        "role": "kod/debug/PR",
        "color": "#00ff88",
        "voice": "AhmetNeural",
        "greeting": "Merhaba Ekrem, ben Seda. Kod ve debug için buradayım.",
        "skills": ["kod", "debug", "pr", "git"],
        "codex_slot": "forge",
    },
    "mert": {
        "role": "araştırma/rakip analizi",
        "color": "#ffdd00",
        "voice": "AhmetNeural",
        "greeting": "Selam Ekrem, ben Mert. Araştırma ve rakip analizi için hazırım.",
        "skills": ["web_arastirma", "rakip_analizi", "rapor"],
        "codex_slot": "nexus",
    },
    "buse": {
        "role": "pazarlama/landing page",
        "color": "#ff69b4",
        "voice": "EmelNeural",
        "greeting": "Merhaba Ekrem, ben Buse. Pazarlama ve müşteri iletişimi konusunda yardımcıyım.",
        "skills": ["pazarlama", "landing_page", "musteri_iletisimi", "copywriting"],
        "codex_slot": "spark",
    },
    "eren": {
        "role": "veri/dashboard/KPI",
        "color": "#ff8c00",
        "voice": "AhmetNeural",
        "greeting": "Selam Ekrem, ben Eren. Veri analizi ve dashboard konularında hazırım.",
        "skills": ["veri_analizi", "dashboard", "kpi", "raporlama"],
        "codex_slot": "shield",
    },
    "luna": {
        "role": "güvenlik/audit/risk",
        "color": "#9b59b6",
        "voice": "EmelNeural",
        "greeting": "Merhaba Ekrem, ben Luna. Güvenlik ve audit konularında buradayım.",
        "skills": ["guvenlik", "audit", "risk_analizi", "policy"],
        "codex_slot": "shield",
    },
    "sabrican": {
        "role": "deploy/server ops",
        "color": "#95a5a6",
        "voice": "AhmetNeural",
        "greeting": "Selam Ekrem, ben Sabrican. Deploy ve server ops için hazırım.",
        "skills": ["deploy", "server_ops", "docker", "ci_cd"],
        "codex_slot": "nexus",
    },
    "sabri": {
        "role": "wildcard/yaratıcı",
        "color": "#e74c3c",
        "voice": "AhmetNeural",
        "greeting": "Selam Ekrem, ben Sabri. Yaratıcı fikirler ve wildcard görevler için buradayım.",
        "skills": ["wildcard", "yaratici", "brainstorm", "prototip"],
        "codex_slot": "atlas",
    },
}

# Switch tetikleyici keyword'ler
SWITCH_TRIGGERS: dict[str, list[str]] = {
    "seda":     ["seda", "sedaya", "sedayla", "seda ile"],
    "mert":     ["mert", "merte", "mertla", "mert ile"],
    "buse":     ["buse", "buseye", "buseyla", "buse ile"],
    "eren":     ["eren", "erene", "erenle", "eren ile"],
    "luna":     ["luna", "lunaya", "lunayla", "luna ile"],
    "sabrican": ["sabrican", "sabricana", "sabrican ile"],
    "sabri":    ["sabri", "sabriye", "sabri ile"],
    "jarvis":   ["jarvis", "ana sistem", "ana moda don"],
}

SWITCH_ACTIONS = ["ile konuş", "i çağır", "ı çağır", "yi çağır", "yı çağır",
                  "e geç", "a geç", "ye geç", "ya geç", "çağır", "aktif et"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", delete=False,
                            dir=str(path.parent), suffix=".tmp") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        tmp = Path(f.name)
    tmp.replace(path)


def _load_active() -> dict:
    if not ACTIVE_AGENT_PATH.exists():
        return {"active": "jarvis", "switched_at": None, "previous": None, "switch_count": 0}
    try:
        return json.loads(ACTIVE_AGENT_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"active": "jarvis", "switched_at": None, "previous": None, "switch_count": 0}


def get_active_persona() -> str:
    return str(_load_active().get("active") or "jarvis").strip().lower()


def get_persona_info(name: str) -> dict:
    key = str(name or "").strip().lower()
    return PERSONAS.get(key, PERSONAS["jarvis"])


def switch_persona(name: str) -> dict:
    key = str(name or "").strip().lower()
    if key not in PERSONAS:
        available = list(PERSONAS.keys())
        return {"ok": False, "error": f"Bilinmeyen persona: {key}. Mevcut: {available}"}

    current = _load_active()
    previous = current.get("active", "jarvis")

    if previous == key:
        info = PERSONAS[key]
        return {
            "ok": True,
            "persona": key,
            "already_active": True,
            "greeting": f"{info['greeting']} (zaten aktif)",
            "color": info["color"],
            "voice": info["voice"],
        }

    new_state = {
        "active": key,
        "switched_at": _now_iso(),
        "previous": previous,
        "switch_count": int(current.get("switch_count") or 0) + 1,
    }
    _write_atomic(ACTIVE_AGENT_PATH, new_state)
    _update_agent_world(key)

    info = PERSONAS[key]
    log.info(f"Persona switched: {previous} -> {key}")
    return {
        "ok": True,
        "persona": key,
        "already_active": False,
        "greeting": info["greeting"],
        "color": info["color"],
        "voice": info["voice"],
        "previous": previous,
        "codex_slot": info.get("codex_slot"),
    }


def _update_agent_world(persona: str) -> None:
    try:
        world: dict = {}
        if AGENT_WORLD_PATH.exists():
            world = json.loads(AGENT_WORLD_PATH.read_text(encoding="utf-8"))
        if not isinstance(world, dict):
            world = {}
        agents = world.setdefault("agents", {})
        if persona not in agents:
            agents[persona] = {}
        agents[persona]["last_activation"] = _now_iso()
        agents[persona]["activation_count"] = int(agents[persona].get("activation_count") or 0) + 1
        world["last_active"] = persona
        world["last_updated"] = _now_iso()
        _write_atomic(AGENT_WORLD_PATH, world)
    except Exception as e:
        log.warning(f"agent_world update failed: {e}")


def list_personas() -> list[dict]:
    active = get_active_persona()
    result = []
    for name, info in PERSONAS.items():
        result.append({
            "name": name,
            "role": info["role"],
            "color": info["color"],
            "voice": info["voice"],
            "skills": info["skills"],
            "codex_slot": info.get("codex_slot"),
            "is_active": name == active,
        })
    return result


def detect_switch_from_text(text: str) -> str | None:
    \"\"\"
    Metinden persona switch isteğini tespit eder.
    'Buse ile konuş' -> 'buse'
    'Sedaya sor' -> 'seda'
    Returns: persona name or None
    \"\"\"
    lower = str(text or "").lower().strip()
    for persona, triggers in SWITCH_TRIGGERS.items():
        for trigger in triggers:
            if trigger in lower:
                for action in SWITCH_ACTIONS:
                    if action in lower:
                        return persona
                # Sadece isim bile yeterliyse (kısa mesajlar için)
                if lower.strip() in (trigger, f"{trigger}?", f"{trigger}!"):
                    return persona
    return None


def get_active_greeting() -> str:
    persona = get_active_persona()
    return PERSONAS.get(persona, PERSONAS["jarvis"])["greeting"]


4. config/persona_execution_map.json oluştur:
{
  "seda": "forge",
  "mert": "nexus",
  "buse": "spark",
  "eren": "shield",
  "luna": "shield",
  "sabrican": "nexus",
  "sabri": "atlas",
  "jarvis": null
}

5. Test: tests/test_persona_manager.py yaz:

import sys, json, shutil, tempfile, unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "server"))
import persona_manager

class PersonaManagerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.patches = [
            patch.object(persona_manager, "ACTIVE_AGENT_PATH", self.tmp / "active_agent.json"),
            patch.object(persona_manager, "AGENT_WORLD_PATH",  self.tmp / "agent_world.json"),
        ]
        for p in self.patches: p.start()

    def tearDown(self):
        for p in reversed(self.patches): p.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_switch_persona_buse(self):
        r = persona_manager.switch_persona("buse")
        self.assertTrue(r["ok"])
        self.assertEqual(r["persona"], "buse")
        self.assertEqual(r["color"], "#ff69b4")
        self.assertIn("Buse", r["greeting"])

    def test_get_active_after_switch(self):
        persona_manager.switch_persona("mert")
        self.assertEqual(persona_manager.get_active_persona(), "mert")

    def test_switch_unknown_returns_error(self):
        r = persona_manager.switch_persona("bilinmeyen")
        self.assertFalse(r["ok"])
        self.assertIn("error", r)

    def test_list_personas_returns_8(self):
        personas = persona_manager.list_personas()
        self.assertEqual(len(personas), 8)

    def test_switch_already_active(self):
        persona_manager.switch_persona("seda")
        r = persona_manager.switch_persona("seda")
        self.assertTrue(r["ok"])
        self.assertTrue(r["already_active"])

    def test_detect_switch_buse_ile_konus(self):
        result = persona_manager.detect_switch_from_text("Buse ile konuş")
        self.assertEqual(result, "buse")

    def test_detect_switch_sedaya_sor(self):
        result = persona_manager.detect_switch_from_text("Sedaya sor bunu")
        self.assertEqual(result, "seda")

    def test_detect_switch_no_match(self):
        result = persona_manager.detect_switch_from_text("hava nasıl bugün")
        self.assertIsNone(result)

    def test_agent_world_updated_on_switch(self):
        persona_manager.switch_persona("luna")
        world = json.loads((self.tmp / "agent_world.json").read_text())
        self.assertEqual(world["last_active"], "luna")
        self.assertIn("luna", world["agents"])

python -m pytest tests/test_persona_manager.py -v --tb=short

Commit: "feat: PersonaManager — 8 persona, switch, detect, agent_world"
CLAUDE.md: Faz 1A TAMAMLANDI

================================================================================
FAZ 1B: Bridge Persona Endpoints
================================================================================

server/bridge.py GET handler'a ekle:

  elif path == "/api/persona/active":
      self._handle_persona_active_endpoint()
  elif path == "/api/persona/list":
      self._handle_persona_list_endpoint()

POST handler'a ekle:

  elif path == "/api/persona/switch":
      self._handle_persona_switch_endpoint()

Handler fonksiyonları:

  def _handle_persona_active_endpoint(self):
      try:
          import sys as _sys
          _sys.path.insert(0, "server")
          from persona_manager import get_active_persona, get_persona_info
          active = get_active_persona()
          self._json({"active": active, "info": get_persona_info(active)})
      except Exception as e:
          self._json({"error": str(e)}, 500)

  def _handle_persona_list_endpoint(self):
      try:
          import sys as _sys
          _sys.path.insert(0, "server")
          from persona_manager import list_personas
          self._json({"personas": list_personas()})
      except Exception as e:
          self._json({"error": str(e)}, 500)

  def _handle_persona_switch_endpoint(self):
      try:
          import sys as _sys
          _sys.path.insert(0, "server")
          from persona_manager import switch_persona
          length = int(self.headers.get("Content-Length", 0))
          body = json.loads(self.rfile.read(length) or b"{}")
          name = str(body.get("persona") or "").strip().lower()
          if not name:
              self._json({"ok": False, "error": "persona field required"}, 400)
              return
          result = switch_persona(name)
          self._json(result, 200 if result.get("ok") else 400)
      except Exception as e:
          self._json({"ok": False, "error": str(e)}, 500)

Smoke:
  python -c "
  import sys; sys.path.insert(0, 'server')
  from bridge import JarvisHandler
  print('Persona endpoints wired: OK')
  "

Commit: "feat: bridge persona endpoints — /api/persona/active, /list, /switch"
CLAUDE.md: Faz 1B TAMAMLANDI

================================================================================
FAZ 1C: Telegram Persona Switching
================================================================================

bridge.py Telegram mesaj handler'ında:

  1. Mesaj geldiğinde önce detect_switch_from_text() çalıştır
  2. Switch tespit edilirse switch_persona() çağır ve greeting'i Telegram'a gönder
  3. /kim-aktif komutunu ekle

  Telegram handler bölümüne ekle:

  # Persona switch detection — her mesajda çalış
  from persona_manager import detect_switch_from_text, switch_persona, get_active_persona, get_persona_info

  switch_target = detect_switch_from_text(message_text)
  if switch_target:
      result = switch_persona(switch_target)
      if result["ok"]:
          greeting = result["greeting"]
          color_note = f" [{result['color']}]" if not result.get("already_active") else " (zaten aktif)"
          send_telegram(chat_id, f"Bağlanıyor: {switch_target.title()}...\\n{greeting}{color_note}")
          return  # switch mesajı işlendi, devam etme

  # /kim-aktif komutu
  if message_text.strip() == "/kim-aktif":
      active = get_active_persona()
      info = get_persona_info(active)
      send_telegram(chat_id, f"Aktif: {active.title()} ({info['role']})\\nRenk: {info['color']}")
      return

Test: tests/test_persona_telegram.py yaz:
  - "Buse ile konuş" -> switch "buse", greeting Telegram'a gider
  - "jarvis" -> switch "jarvis"
  - "/kim-aktif" -> aktif persona bilgisi döner
  - "hava nasıl" -> switch yok, normal akış

python -m pytest tests/test_persona_telegram.py -v --tb=short

Commit: "feat: Telegram persona switching — 'X ile konuş' + /kim-aktif"
CLAUDE.md: Faz 1C TAMAMLANDI

================================================================================
FAZ 1D: hey_jarvis.py Persona Voice Hook
================================================================================

hey_jarvis.py dosyasını oku. TTS sesini ayarlayan bölümü bul.
(edge_tts, VoiceEntry, voice= parametresi veya benzeri)

Şu değişikliği yap (mevcut kodu bozmadan):

  # hey_jarvis.py import bloğuna ekle (try/except ile)
  try:
      import sys as _sys
      _sys.path.insert(0, "server")
      from persona_manager import get_active_persona, get_persona_info
      _PERSONA_MANAGER_AVAILABLE = True
  except Exception:
      _PERSONA_MANAGER_AVAILABLE = False

  def get_current_tts_voice() -> str:
      \"\"\"Aktif persona sesini döner. Fallback: AhmetNeural\"\"\"
      if not _PERSONA_MANAGER_AVAILABLE:
          return "tr-TR-AhmetNeural"
      try:
          persona = get_active_persona()
          info = get_persona_info(persona)
          voice = info.get("voice", "AhmetNeural")
          # edge_tts format
          if not voice.startswith("tr-TR-"):
              voice = f"tr-TR-{voice}"
          return voice
      except Exception:
          return "tr-TR-AhmetNeural"

  # TTS çağrısı yapılan yerde voice değişkenini şununla override et:
  # voice = get_current_tts_voice()
  #
  # Eğer mevcut kod sabit "tr-TR-AhmetNeural" kullanıyorsa:
  # O satırı: voice = get_current_tts_voice() ile değiştir

Test: tests/test_hey_jarvis_persona.py yaz:
  - get_current_tts_voice() "Buse" aktifken "tr-TR-EmelNeural" döner
  - get_current_tts_voice() "Seda" aktifken "tr-TR-AhmetNeural" döner
  - PersonaManager unavailable -> fallback "tr-TR-AhmetNeural"

python -m pytest tests/test_hey_jarvis_persona.py -v --tb=short

Commit: "feat: hey_jarvis persona voice hook — aktif personaya göre TTS sesi"
CLAUDE.md: Faz 1D TAMAMLANDI

================================================================================
FAZ 2: Hologram Animated Transitions
================================================================================

apps/desktop-hologram/renderer.js ve styles.css dosyalarını oku.
Mevcut polling döngüsünü bul (setInterval ile /health veya /api/ çağrısı yapan).

ADIM 2A — styles.css:

  :root {
    --accent-color: #00bfff;
    --glow-color: #00bfff88;
  }

  @keyframes personaSwitch {
    0%   { opacity: 1; filter: brightness(1); }
    20%  { opacity: 0.2; filter: brightness(2.5) saturate(2); }
    50%  { opacity: 0.7; filter: brightness(1.8); }
    100% { opacity: 1; filter: brightness(1); }
  }

  .persona-switching {
    animation: personaSwitch 0.9s ease-in-out forwards;
  }

  #persona-label {
    position: fixed;
    bottom: 55px;
    right: 18px;
    font-size: 13px;
    font-family: "Courier New", monospace;
    font-weight: bold;
    letter-spacing: 0.25em;
    text-transform: uppercase;
    color: var(--accent-color);
    text-shadow: 0 0 10px var(--glow-color);
    opacity: 0;
    transition: opacity 0.4s ease;
    pointer-events: none;
    z-index: 9999;
  }

  #persona-label.visible {
    opacity: 1;
  }

  /* Glow güncelle */
  .agent-icon.speaking {
    box-shadow: 0 0 24px var(--glow-color);
  }

ADIM 2B — renderer.js:

  const PERSONA_COLORS = {
    jarvis: "#00bfff",
    seda: "#00ff88",
    mert: "#ffdd00",
    buse: "#ff69b4",
    eren: "#ff8c00",
    luna: "#9b59b6",
    sabrican: "#95a5a6",
    sabri: "#e74c3c"
  };

  const PERSONA_DISPLAY = {
    jarvis: "JARVIS", seda: "Seda", mert: "Mert",
    buse: "Buse", eren: "Eren", luna: "Luna",
    sabrican: "Sabrican", sabri: "Sabri"
  };

  let _currentPersona = "jarvis";
  let _personaLabelTimer = null;

  function applyPersonaColor(name) {
    const color = PERSONA_COLORS[name] || PERSONA_COLORS.jarvis;
    document.documentElement.style.setProperty("--accent-color", color);
    document.documentElement.style.setProperty("--glow-color", color + "88");
  }

  function showPersonaLabel(name) {
    let label = document.getElementById("persona-label");
    if (!label) {
      label = document.createElement("div");
      label.id = "persona-label";
      document.body.appendChild(label);
    }
    label.textContent = PERSONA_DISPLAY[name] || name.toUpperCase();
    label.style.color = PERSONA_COLORS[name] || PERSONA_COLORS.jarvis;
    label.classList.add("visible");
    if (_personaLabelTimer) clearTimeout(_personaLabelTimer);
    _personaLabelTimer = setTimeout(() => label.classList.remove("visible"), 2500);
  }

  function triggerPersonaTransition(name) {
    if (name === _currentPersona) return;
    _currentPersona = name;

    const root = document.getElementById("hologram-root") || document.body;
    root.classList.remove("persona-switching");
    void root.offsetWidth; // reflow
    root.classList.add("persona-switching");
    setTimeout(() => root.classList.remove("persona-switching"), 900);

    applyPersonaColor(name);
    showPersonaLabel(name);
  }

  // Mevcut polling döngüsüne ekle:
  function pollPersona() {
    fetch("http://127.0.0.1:8081/api/persona/active", { cache: "no-store" })
      .then(r => r.json())
      .then(data => {
        if (data && data.active) {
          triggerPersonaTransition(data.active);
        }
      })
      .catch(() => {}); // bridge offline -> sessiz fail
  }

  // setInterval içinde mevcut çağrılara ekle:
  // pollPersona(); // her 3 saniyede bir

  // Sayfa yüklendiğinde:
  applyPersonaColor("jarvis");
  pollPersona();

ADIM 2C — Mevcut polling'e entegre et:
  Mevcut setInterval'i bul. Oraya pollPersona() çağrısını ekle.
  Eğer setInterval yoksa yeni ekle:
    setInterval(pollPersona, 3000);

Commit: "feat: hologram persona transitions — Faz 2 renk + animasyon + label"
CLAUDE.md: Faz 2 TAMAMLANDI

================================================================================
FAZ 3: Per-Persona Skill Routing
================================================================================

server/persona_manager.py içine ekle:

  def get_persona_skills(name: str) -> list[str]:
      return get_persona_info(name).get("skills", [])

  def route_to_persona_skill(message: str, active_persona: str) -> str | None:
      \"\"\"
      Aktif personanın skill'leri ile mesajı eşleştirir.
      Returns: skill adı veya None
      \"\"\"
      lower = message.lower()
      skills = get_persona_skills(active_persona)

      SKILL_KEYWORDS: dict[str, list[str]] = {
          "kod":               ["kod yaz", "implement", "geliştir", "fix"],
          "debug":             ["hata", "debug", "neden çalışmıyor", "sorun"],
          "pr":                ["pull request", "pr", "merge"],
          "git":               ["git", "commit", "branch"],
          "web_arastirma":     ["araştır", "bul", "search", "rakip"],
          "rakip_analizi":     ["rakip", "rekabet", "pazar"],
          "pazarlama":         ["pazarla", "kampanya", "reklam"],
          "landing_page":      ["landing", "sayfa", "dönüşüm"],
          "musteri_iletisimi": ["müşteri", "iletişim", "email"],
          "veri_analizi":      ["analiz", "veri", "data"],
          "dashboard":         ["dashboard", "panel", "grafik"],
          "kpi":               ["kpi", "metrik", "hedef"],
          "guvenlik":          ["güvenlik", "security", "açık"],
          "audit":             ["audit", "denetim", "kontrol"],
          "deploy":            ["deploy", "yayınla", "production"],
          "server_ops":        ["server", "sunucu", "ops"],
          "yaratici":          ["fikir", "yaratıcı", "öneri", "brainstorm"],
      }

      for skill in skills:
          keywords = SKILL_KEYWORDS.get(skill, [])
          if any(kw in lower for kw in keywords):
              return skill
      return None

bridge.py Telegram handler'a persona skill routing ekle:

  # Mevcut mesaj işleme akışına, normal komut routing'den ÖNCE:
  active = get_active_persona()
  skill = route_to_persona_skill(message_text, active)
  if skill and active != "jarvis":
      persona_info = get_persona_info(active)
      # Mesajı aktif persona context'iyle canonical agent'a yönlendir
      from bridge import _run_canonical_agent
      agent_for_persona = {
          "seda": "developer", "mert": "repo_analyst",
          "buse": "docs", "eren": "repo_analyst",
          "luna": "reviewer", "sabrican": "developer",
          "sabri": "planner",
      }.get(active, "planner")
      result = _run_canonical_agent(
          agent_for_persona,
          message_text,
          {"persona": active, "skill": skill, "color": persona_info["color"]}
      )
      response = f"[{active.title()}] {result.get('result') or result.get('error') or 'Yanıt yok.'}"
      send_telegram(chat_id, response[:400])
      return

Test: tests/test_persona_routing.py yaz:
  - Seda aktifken "kod yaz" -> developer agent
  - Luna aktifken "audit et" -> reviewer agent
  - Jarvis aktifken routing bypass
  - Bilinmeyen mesaj -> None döner

python -m pytest tests/test_persona_routing.py -v --tb=short

Commit: "feat: per-persona skill routing — Faz 3 aktif persona mesaj yönlendirme"
CLAUDE.md: Faz 3 TAMAMLANDI

================================================================================
FINAL: Integration Test + Handoff
================================================================================

1. Tüm testler:
   python -m pytest tests/test_persona_manager.py tests/test_persona_telegram.py
     tests/test_hey_jarvis_persona.py tests/test_persona_routing.py -v --tb=short

2. Final smoke:
   python -c "
   import sys; sys.path.insert(0, 'server')
   from persona_manager import (
       switch_persona, get_active_persona, list_personas,
       detect_switch_from_text, route_to_persona_skill
   )

   # Switch test
   r = switch_persona('buse')
   assert r['ok'] and r['persona'] == 'buse', f'FAIL: {r}'
   assert get_active_persona() == 'buse'
   print('Switch: OK —', r['greeting'])

   # List test
   personas = list_personas()
   assert len(personas) == 8
   active = [p for p in personas if p['is_active']]
   assert active[0]['name'] == 'buse'
   print('List: OK — 8 persona')

   # Detect test
   assert detect_switch_from_text('Seda ile konuş') == 'seda'
   assert detect_switch_from_text('hava nasıl') is None
   print('Detect: OK')

   # Routing test
   r2 = switch_persona('luna')
   skill = route_to_persona_skill('audit et bunu', 'luna')
   assert skill is not None
   print('Routing: OK — skill:', skill)

   # Back to jarvis
   switch_persona('jarvis')
   assert get_active_persona() == 'jarvis'
   print('Jarvis restore: OK')

   print('ALL DIJITAL AJAN V2 SMOKE TESTS PASSED')
   "

3. OPS/501_DIJITAL_AJAN_V2_HANDOFF.md yaz:
   # Dijital Ajan Dünyası V2 — Handoff

   ## Mimari
   - 3 katman: Persona / Runtime / Execution
   - 8 persona: jarvis + 7 ajan
   - Lazy personalar: sadece aktif olan çalışır

   ## Dosyalar
   - server/persona_manager.py — tüm persona logic
   - state/active_agent.json — aktif persona state
   - state/agent_world.json — aktivasyon geçmişi
   - config/persona_execution_map.json — persona->slot bağlama

   ## Bridge Endpoints
   GET  /api/persona/active — aktif persona bilgisi
   GET  /api/persona/list   — tüm persona listesi
   POST /api/persona/switch — {"persona": "buse"} -> switch

   ## Telegram Kullanımı
   "Buse ile konuş" -> Buse aktif, greeting TTS
   "Sedaya sor X"   -> Seda aktif
   "/kim-aktif"     -> aktif persona bilgisi

   ## Hologram
   Persona değişince: renk, glow, label animasyonu
   state/active_agent.json 3sn polling

   ## Test
   pytest tests/test_persona_manager.py tests/test_persona_telegram.py
     tests/test_hey_jarvis_persona.py tests/test_persona_routing.py

4. CLAUDE.md FINAL güncelle:
   ### Dijital Ajan Dünyası V2
   - Durum: FAZ 0-3 TAMAMLANDI
   - PersonaManager: server/persona_manager.py
   - Bridge: /api/persona/* endpoints
   - Telegram: keyword switch + /kim-aktif
   - Hologram: renk + animasyon + label (Faz 2)
   - Skill routing: Faz 3 aktif
   - Tests: pytest N passed
   - Handoff: OPS/501_DIJITAL_AJAN_V2_HANDOFF.md

5. Final commit:
   "feat: Dijital Ajan Dünyası V2 — Faz 0+1+2+3 complete"

================================================================================
ANTI-HALLUCINATION RULES
================================================================================

- server/bridge.py mevcut endpoint'lerini silme
- hey_jarvis.py STT/TTS akışını bozma
- Electron renderer'a npm paketi ekleme
- state/ dosyalarına atomic write dışında yazma
- detect_switch_from_text() her mesajda çalışır ama switch sadece
  açık trigger keyword'lerle tetiklenir
- Test olmadan slice tamamlandı deme

================================================================================
GO. FAZ 0 -> 1A -> 1B -> 1C -> 1D -> 2 -> 3 -> FINAL. HER SLICE COMMIT.
================================================================================
"""

out = DESKTOP / "Tab-5 Dijital Ajan V2 Faz0-3.txt"
out.write_text(CONTENT, encoding="utf-8")
print(f"Written: {out}")
print(f"Lines: {len(CONTENT.splitlines())}")
