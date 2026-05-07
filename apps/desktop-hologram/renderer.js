const BACKEND = "http://127.0.0.1:8081";
const POLL_ACTIVE_MS = 900;
const POLL_IDLE_MS = 2500;
const IDLE_SWITCH_AFTER = 3;
let _idleStreak = 0;

const AGENTS = {
  jarvis: { name: "JARVIS", role: "AI Operating System", skills: ["Voice", "Memory", "Tasks", "Router"] },
  sabri: { name: "SABRI", role: "Reklam Ajansi", skills: ["Brief", "Creative", "Campaign"] },
  luna: { name: "LUNA", role: "Cyber / OSINT", skills: ["OSINT", "Pentest", "Reports"] },
  buse: { name: "BUSE", role: "Sosyal Medya", skills: ["Instagram", "Reels", "Calendar"] },
  deniz: { name: "DENIZ", role: "E-ticaret", skills: ["Marketplace", "Trendyol", "Margins"] },
  eren: { name: "EREN", role: "YouTube / Video", skills: ["Channels", "Retention", "Transcripts"] },
  mert: { name: "MERT", role: "Derin Arastirma", skills: ["Research", "Competitors", "Trends"] },
  zeynep: { name: "ZEYNEP", role: "Guvenlik / KVKK", skills: ["Compliance", "Audit", "Logs"] },
  seda: { name: "SEDA", role: "Kod / Debug / PR", skills: ["Code Review", "Implementer"] },
  sabrican: { name: "SABRICAN", role: "Deploy / Ops", skills: ["Deploy", "Ops"] },
  opencode: { name: "OPENCODE", role: "Code Agent", skills: ["Code", "Refactor", "Review", "Deploy"] },
  claude: { name: "CLAUDE", role: "Analysis Agent", skills: ["Research", "Analysis", "Writing", "Vision"] },
  research: { name: "RESEARCH", role: "Research Agent", skills: ["Web Search", "Summarize", "Cite"] },
  guard: { name: "GUARD", role: "Security Agent", skills: ["Audit", "Redaction", "Hardening"] },
  ollama: { name: "OLLAMA", role: "Local LLM", skills: ["Generate", "Reason", "Code"] },
  "telegram-bot": { name: "TELEGRAM", role: "Bot Interface", skills: ["Commands", "Dispatch", "Notify"] },
  video: { name: "VIDEO", role: "Media Agent", skills: ["Trends", "Clips", "Reports"] },
  backend: { name: "BACKEND", role: "System Agent", skills: ["APIs", "Bridge", "Runtime"] },
  voice: { name: "VOICE", role: "Conversation Agent", skills: ["Wake Word", "STT", "TTS"] },
  security: { name: "GUARD", role: "Security Agent", skills: ["Policy", "Audit", "Risk"] },
};

const STATE_LABELS = {
  idle: "Hazir",
  listening: "Dinliyor...",
  thinking: "Dusunuyor...",
  speaking: "Konusuyor...",
  muted: "Sessiz",
  offline: "Cevrimdisi",
};

let currentPhase = "idle";
let currentPersonaId = null;
let personaSwitchTimer = null;
let personaLabelTimer = null;
let particleCanvas = null;
let particleCtx = null;
let particleDpr = 1;
let particleWidth = 0;
let particleHeight = 0;
let particleCenterX = 0;
let particleCenterY = 0;
let particleAccentR = 0;
let particleAccentG = 212;
let particleAccentB = 255;
let voiceEnergy = 0;
let voiceKick = 0;
let conversationSeed = 1;
let lastVoiceSignature = "";
let lastVoiceActivityAt = 0;
let lastParticleFrameMs = 0;

const PARTICLE_COUNT = 9000;
const particleN = new Float32Array(PARTICLE_COUNT);
const particleA = new Float32Array(PARTICLE_COUNT);
const particleB = new Float32Array(PARTICLE_COUNT);
const particleR0 = new Float32Array(PARTICLE_COUNT);

for (let particleIndex = 0; particleIndex < PARTICLE_COUNT; particleIndex += 1) {
  const normalized = PARTICLE_COUNT > 1 ? particleIndex / (PARTICLE_COUNT - 1) : 0;
  const band = normalized * 2 - 1;
  particleN[particleIndex] = normalized;
  particleA[particleIndex] = particleIndex * 2.399963229728653;
  particleB[particleIndex] = band;
  particleR0[particleIndex] = Math.sqrt(Math.max(0, 1 - band * band));
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function clampByte(value) {
  return clamp(Math.round(value), 0, 255);
}

function hashString(value) {
  let hash = 2166136261;
  const text = String(value || "");
  for (let index = 0; index < text.length; index += 1) {
    hash ^= text.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function isLiveVoicePhase(phase) {
  return phase === "listening" || phase === "thinking" || phase === "speaking" || phase === "swarm";
}

function normalizeHex(value) {
  const raw = String(value || "").trim();
  if (/^#[0-9a-fA-F]{6}$/.test(raw)) {
    return raw.toLowerCase();
  }
  if (/^#[0-9a-fA-F]{3}$/.test(raw)) {
    return `#${raw[1]}${raw[1]}${raw[2]}${raw[2]}${raw[3]}${raw[3]}`.toLowerCase();
  }
  return "#00d4ff";
}

function hexToRgb(hex) {
  const normalized = normalizeHex(hex);
  return {
    r: Number.parseInt(normalized.slice(1, 3), 16),
    g: Number.parseInt(normalized.slice(3, 5), 16),
    b: Number.parseInt(normalized.slice(5, 7), 16),
  };
}

function rgbToCss(rgb) {
  return `${rgb.r}, ${rgb.g}, ${rgb.b}`;
}

function mixHex(baseHex, targetHex, ratio) {
  const base = hexToRgb(baseHex);
  const target = hexToRgb(targetHex);
  const mixRatio = clamp(Number(ratio) || 0, 0, 1);
  const channel = (from, to) => Math.round(from + ((to - from) * mixRatio));
  const mixed = {
    r: channel(base.r, target.r),
    g: channel(base.g, target.g),
    b: channel(base.b, target.b),
  };
  return `#${[mixed.r, mixed.g, mixed.b].map((value) => value.toString(16).padStart(2, "0")).join("")}`;
}

function particlePhaseEnergy() {
  if (currentPhase === "speaking") return 1.0;
  if (currentPhase === "listening") return 0.82;
  if (currentPhase === "thinking") return 0.72;
  if (currentPhase === "swarm") return 0.95;
  if (currentPhase === "muted") return 0.32;
  if (currentPhase === "offline") return 0.18;
  return 0.48;
}

function noteVoiceActivity(assistant, swarm, phase) {
  const voice = assistant?.voice && typeof assistant.voice === "object" ? assistant.voice : {};
  const signatureParts = [
    phase,
    voice.last_heard || "",
    voice.heard_at || "",
    voice.last_response || "",
    voice.response_at || "",
    voice.turn_count || "",
    swarm?.speaking || "",
    swarm?.text || "",
  ];
  const hasVoiceText = signatureParts.some((part, index) => index > 0 && String(part || "").trim());
  const signature = signatureParts.join("|");
  const now = performance.now();

  if (hasVoiceText && signature !== lastVoiceSignature) {
    lastVoiceSignature = signature;
    conversationSeed = hashString(signature) || 1;
    lastVoiceActivityAt = now;
    voiceKick = Math.min(1.1, voiceKick + 0.62);
  }

  if (isLiveVoicePhase(phase)) {
    lastVoiceActivityAt = now;
  }
}

function resizeParticleHologram() {
  if (!particleCanvas) return;

  const rect = particleCanvas.getBoundingClientRect();
  particleDpr = clamp(window.devicePixelRatio || 1, 1, 2);
  particleWidth = Math.max(1, Math.floor(rect.width * particleDpr));
  particleHeight = Math.max(1, Math.floor(rect.height * particleDpr));
  particleCenterX = particleWidth * 0.5;
  particleCenterY = particleHeight * 0.5;

  if (particleCanvas.width !== particleWidth || particleCanvas.height !== particleHeight) {
    particleCanvas.width = particleWidth;
    particleCanvas.height = particleHeight;
  }
}

function drawParticleHologram(nowMs) {
  if (!particleCtx || !particleCanvas) {
    return;
  }

  const frameDelta = lastParticleFrameMs ? clamp(nowMs - lastParticleFrameMs, 8, 48) : 16;
  lastParticleFrameMs = nowMs;
  const recentVoiceMs = lastVoiceActivityAt ? nowMs - lastVoiceActivityAt : Number.POSITIVE_INFINITY;
  const recentVoice = recentVoiceMs < 3600 ? 1 - (recentVoiceMs / 3600) : 0;
  const phaseTarget = currentPhase === "speaking"
    ? 1
    : currentPhase === "swarm"
      ? 0.92
      : currentPhase === "listening"
        ? 0.78
        : currentPhase === "thinking"
          ? 0.58
          : 0;
  const targetVoiceEnergy = Math.max(phaseTarget, recentVoice * 0.72) + voiceKick;
  const smoothing = clamp(frameDelta / 130, 0.06, 0.36);
  voiceEnergy += (targetVoiceEnergy - voiceEnergy) * smoothing;
  voiceKick *= Math.pow(0.84, frameDelta / 16.67);

  const vocal = clamp(voiceEnergy, 0, 1.18);
  const energy = clamp(particlePhaseEnergy() + vocal * 0.34, 0, 1.25);
  const timeSeconds = nowMs * 0.001;
  const speechBeat = Math.sin(timeSeconds * (8.6 + vocal * 7.8) + conversationSeed * 0.00037);
  const microBeat = Math.sin(timeSeconds * 19.0 + conversationSeed * 0.00019);
  const speed = 0.58 + energy * 1.08 + vocal * 0.84;
  const scale = 46 + vocal * 7.5 + speechBeat * vocal * 1.9;
  const fold = 2.2 + energy * 3.0 + vocal * 2.8;
  const flow = 1.1 + energy * 2.6 + vocal * 2.2;
  const bloom = 0.32 + energy * 0.4 + vocal * 0.28;
  const timeValue = timeSeconds * speed;
  const drawScale = Math.min(particleWidth, particleHeight) / 110;
  const colorLift = vocal * 62;
  const gradient = particleCtx.createLinearGradient(0, 0, particleWidth, particleHeight);
  gradient.addColorStop(0, `rgb(${clampByte(particleAccentR + 24)}, ${clampByte(particleAccentG + 84)}, ${clampByte(particleAccentB + colorLift)})`);
  gradient.addColorStop(0.46, `rgb(${clampByte(particleAccentR + 88 + colorLift)}, ${clampByte(particleAccentG + 112)}, ${clampByte(particleAccentB + 112)})`);
  gradient.addColorStop(1, `rgb(${clampByte(particleAccentR + 8)}, ${clampByte(particleAccentG + 24 + colorLift)}, ${clampByte(particleAccentB + 34)})`);

  particleCtx.clearRect(0, 0, particleWidth, particleHeight);
  particleCtx.globalCompositeOperation = "lighter";
  particleCtx.fillStyle = gradient;

  for (let particleIndex = 0; particleIndex < PARTICLE_COUNT; particleIndex += 1) {
    const n = particleN[particleIndex];
    const a = particleA[particleIndex];
    const b = particleB[particleIndex];
    const r0 = particleR0[particleIndex];
    const w1 = Math.sin(timeValue * 0.73 + b * fold);
    const w2 = Math.cos(timeValue * 0.51 + n * 31.4159265359);
    const w3 = Math.sin(timeValue * 0.37 + a * 1.61803398875);
    const voiceRipple = Math.sin(timeValue * (2.7 + vocal * 2.2) + n * 78.0 + conversationSeed * 0.0011) * vocal;
    const shell = scale * (0.72 + 0.19 * Math.sin(timeValue + n * 18.8495559215) + 0.08 * w3 + 0.13 * voiceRipple);
    const twist = a + timeValue * (0.18 + flow * 0.04) + fold * b + 0.55 * w1 + voiceRipple * 0.42;
    const xr = Math.cos(twist) * r0;
    const zr = Math.sin(twist) * r0;
    const knot = Math.sin(a * 3.0 + timeValue + b * 7.0) * Math.cos(a * 2.0 - timeValue * 0.8);
    const veil = 1.0 + 0.22 * knot + 0.13 * w2 + voiceRipple * 0.12;
    const x = shell * veil * xr + Math.sin(b * 9.0 + timeValue * 1.4) * fold;
    const y = shell * (b * (0.9 + vocal * 0.12) + 0.17 * w1) + Math.cos(a + timeValue) * fold * 0.7 + Math.sin(timeSeconds * 12.0 + n * 70.0) * vocal * 3.4;
    const z = shell * veil * zr + Math.cos(b * 8.0 - timeValue * 1.2) * fold;
    const projection = 1 / (2.58 + (z / scale) * 0.58);
    const sx = particleCenterX + x * drawScale * projection * 1.95;
    const sy = particleCenterY + y * drawScale * projection * 1.95;
    const heat = Math.abs(knot);
    const size = (0.52 + heat * 1.16 + bloom * 0.44 + Math.abs(voiceRipple) * 0.9 + Math.max(0, microBeat) * vocal * 0.18) * particleDpr * projection;

    particleCtx.globalAlpha = Math.min(0.94, 0.16 + heat * 0.3 + bloom * 0.2 + Math.abs(voiceRipple) * 0.12);
    particleCtx.fillRect(sx, sy, size, size);
  }

  if (vocal > 0.02) {
    const ringRadius = Math.min(particleWidth, particleHeight) * (0.24 + vocal * 0.1 + Math.max(0, speechBeat) * 0.035);
    particleCtx.beginPath();
    particleCtx.arc(particleCenterX, particleCenterY, ringRadius, 0, Math.PI * 2);
    particleCtx.lineWidth = Math.max(1, particleDpr * (0.8 + vocal * 1.6));
    particleCtx.strokeStyle = `rgba(${particleAccentR}, ${particleAccentG}, ${particleAccentB}, ${Math.min(0.42, 0.12 + vocal * 0.24)})`;
    particleCtx.stroke();
  }

  particleCtx.globalAlpha = 1;
  particleCtx.globalCompositeOperation = "source-over";
  requestAnimationFrame(drawParticleHologram);
}

function initializeParticleHologram() {
  particleCanvas = document.getElementById("particleHologram");
  if (!particleCanvas) return;

  particleCtx = particleCanvas.getContext("2d", { alpha: true });
  if (!particleCtx) return;

  resizeParticleHologram();
  window.addEventListener("resize", resizeParticleHologram);
  requestAnimationFrame(drawParticleHologram);
}

function normalizePhase(rawPhase) {
  const phase = String(rawPhase || "idle").trim().toLowerCase();
  if (["listening", "thinking", "speaking", "muted", "idle", "offline", "swarm"].includes(phase)) {
    return phase;
  }
  return "idle";
}

function applyHealthState(health, assistant) {
  if (!health || typeof health !== "object") {
    return assistant;
  }

  const liveVoice = health.live && typeof health.live === "object" && health.live.voice && typeof health.live.voice === "object"
    ? health.live.voice
    : {};
  const normalizedPhase = normalizePhase(health.voice_state || liveVoice.phase || assistant.phase);
  const runtime = {
    ...(assistant.runtime || {}),
    status: liveVoice.status || (assistant.runtime || {}).status || "offline",
    detail: health.voice_detail || liveVoice.detail || (assistant.runtime || {}).detail || "",
    source: "bridge-health",
  };
  const voice = {
    ...(assistant.voice || {}),
    last_heard: liveVoice.last_heard || (assistant.voice || {}).last_heard || "",
    last_response: liveVoice.last_response || (assistant.voice || {}).last_response || "",
    turn_count: liveVoice.turn_count || (assistant.voice || {}).turn_count || 0,
  };

  return {
    ...assistant,
    phase: normalizedPhase,
    runtime,
    voice,
    text: assistant.text || voice.last_response || "Jarvis hazir.",
    latestPreview: assistant.latestPreview || voice.last_heard || "",
  };
}

function setPhase(phase) {
  if (phase === currentPhase) return;
  currentPhase = phase;

  const hologram = document.getElementById("hologram");
  if (hologram) {
    hologram.className = `hologram ${phase}`;
  }

  if (window.jarvisDesktop) {
    window.jarvisDesktop.setPhase(phase);
    if (phase === "listening" || phase === "speaking") {
      window.jarvisDesktop.focusOverlay();
    }
  }
}

function showPersonaLabel(agent) {
  const label = document.getElementById("persona-label");
  if (!label || !agent) return;

  label.textContent = `${agent.name} | ${agent.role}`;
  label.classList.add("visible");
  if (personaLabelTimer) {
    clearTimeout(personaLabelTimer);
  }
  personaLabelTimer = window.setTimeout(() => {
    label.classList.remove("visible");
  }, 1800);
}

function triggerPersonaSwitch(agent, personaKey) {
  const shell = document.getElementById("shell");
  if (shell) {
    shell.classList.remove("persona-switching");
    void shell.offsetWidth;
    shell.classList.add("persona-switching");
    if (personaSwitchTimer) {
      clearTimeout(personaSwitchTimer);
    }
    personaSwitchTimer = window.setTimeout(() => {
      shell.classList.remove("persona-switching");
    }, 620);
  }

  showPersonaLabel(agent);
  currentPersonaId = personaKey;
}

function applyPersonaTheme(persona) {
  const color = normalizeHex(persona?.color);
  const glowRgb = hexToRgb(color);
  particleAccentR = glowRgb.r;
  particleAccentG = glowRgb.g;
  particleAccentB = glowRgb.b;
  const themeVars = {
    "--accent-color": color,
    "--glow-color": color,
    "--glow-rgb": rgbToCss(glowRgb),
    "--core-idle": mixHex(color, "#ffffff", 0.08),
    "--core-idle-dark": mixHex(color, "#08111c", 0.72),
    "--core-listening": mixHex(color, "#dff7ff", 0.18),
    "--core-listening-dark": mixHex(color, "#06233d", 0.72),
    "--core-thinking": mixHex(color, "#f4f8ff", 0.12),
    "--core-thinking-dark": mixHex(color, "#041225", 0.78),
    "--core-speaking": mixHex(color, "#ffffff", 0.16),
    "--core-speaking-dark": mixHex(color, "#13070a", 0.68),
    "--meter-end-color": mixHex(color, "#ffffff", 0.24),
  };

  [document.documentElement, document.body].forEach((target) => {
    if (!target) {
      return;
    }
    Object.entries(themeVars).forEach(([name, value]) => {
      target.style.setProperty(name, value);
    });
  });

  const shell = document.getElementById("shell");
  if (shell) {
    shell.classList.add("hologram-glow");
  }
}

function updateUI(assistant, presence, swarm, persona) {
  const personaKey = String(persona?.id || assistant.agent || "jarvis").toLowerCase();
  const fallbackAgent = AGENTS[personaKey] || AGENTS.jarvis;
  const agent = persona && typeof persona === "object"
    ? {
        name: String(persona.name || fallbackAgent.name).toUpperCase(),
        role: String(persona.role || fallbackAgent.role),
        skills: Array.isArray(persona.skills) ? persona.skills : fallbackAgent.skills,
      }
    : fallbackAgent;
  const runtime = assistant.runtime || {};
  const voice = assistant.voice || {};
  const phase = normalizePhase(swarm?.ceo_phase || assistant.phase || "idle");

  applyPersonaTheme(persona);
  noteVoiceActivity(assistant, swarm, phase);
  setPhase(phase);

  if (currentPersonaId === null) {
    currentPersonaId = personaKey;
  } else if (personaKey !== currentPersonaId) {
    triggerPersonaSwitch(agent, personaKey);
  }

  document.getElementById("agentName").textContent = agent.name;
  document.getElementById("agentRole").textContent = runtime.detail
    ? `${agent.role} | ${runtime.detail}`
    : agent.role;
  document.getElementById("agentState").textContent = STATE_LABELS[phase] || phase;
  document.getElementById("speechText").textContent = assistant.text || voice.last_response || "Jarvis hazir.";
  document.getElementById("previewText").textContent = assistant.latestPreview || voice.last_heard || "";
  document.getElementById("agentSkills").textContent = agent.skills.join(" | ");

  const onlineAgents = Array.isArray(presence.online_agents) ? presence.online_agents : [];
  const abilityBits = [];
  if (onlineAgents.length) {
    abilityBits.push(`Aktif: ${onlineAgents.join(", ")}`);
  }
  if (runtime.wake_mode) {
    abilityBits.push(`Wake: ${runtime.wake_mode}`);
  }
  if (runtime.stt_backend) {
    abilityBits.push(`STT: ${runtime.stt_backend}`);
  }
  if (runtime.tts_backend) {
    abilityBits.push(`TTS: ${runtime.tts_backend}`);
  }
  document.getElementById("abilityStatus").textContent = abilityBits.join(" | ");

  const meterWidths = { idle: 10, listening: 68, thinking: 84, speaking: 96, swarm: 100, muted: 2, offline: 0 };
  document.getElementById("activityFill").style.width = `${meterWidths[phase] || 20}%`;

  const connectionBits = [];
  connectionBits.push(runtime.status === "offline" ? "Cevrimdisi" : "Bagli");
  if (runtime.source) {
    connectionBits.push(runtime.source);
  }
  connectionBits.push(new Date().toLocaleTimeString("tr-TR"));
  document.getElementById("connectionState").textContent = connectionBits.join(" | ");

  const activeAgents = Array.isArray(swarm?.active_agents) ? swarm.active_agents : [];
  const participantAgents =
    swarm?.dialogue_active && Array.isArray(swarm?.participants) ? swarm.participants : [];
  const activeAgentSet = new Set(
    [...activeAgents, ...participantAgents]
      .map((item) => String(item || "").trim().toLowerCase())
      .filter(Boolean),
  );
  const speakingAgent = String(swarm?.speaking || "").trim().toLowerCase() || null;
  const swarmText = swarm?.text || "";
  const currentPersonaBusy = ["listening", "thinking", "speaking", "swarm"].includes(phase);

  document.querySelectorAll(".agent-icon").forEach((icon) => {
    const iconAgent = String(icon.getAttribute("data-agent") || "").trim().toLowerCase();
    icon.classList.remove("active", "speaking", "selected");
    if (iconAgent === personaKey) {
      icon.classList.add("selected");
    }
    if (iconAgent === speakingAgent) {
      icon.classList.add("speaking");
    } else if (activeAgentSet.has(iconAgent) || (currentPersonaBusy && iconAgent === personaKey)) {
      icon.classList.add("active");
    }
  });

  if (speakingAgent && swarmText) {
    const speakerNames = {
      sabri: "Sabri",
      luna: "Luna",
      buse: "Buse",
      deniz: "Deniz",
      eren: "Eren",
      mert: "Mert",
      zeynep: "Zeynep",
      seda: "Seda",
      sabrican: "Sabrican",
    };
    document.getElementById("agentName").textContent = speakerNames[speakingAgent] || speakingAgent.toUpperCase();
    document.getElementById("speechText").textContent = swarmText;
  }
}

async function poll() {
  try {
    const [healthResponse, assistantResponse, presenceResponse, swarmResponse, personaResponse] = await Promise.allSettled([
      fetch(`${BACKEND}/health`, { cache: "no-store" }),
      fetch(`${BACKEND}/api/desktop-assistant`, { cache: "no-store" }),
      fetch(`${BACKEND}/api/office/presence`, { cache: "no-store" }),
      fetch(`${BACKEND}/api/swarm-status`, { cache: "no-store" }),
      fetch(`${BACKEND}/api/persona/active`, { cache: "no-store" }),
    ]);

    const health =
      healthResponse.status === "fulfilled" && healthResponse.value.ok
        ? await healthResponse.value.json()
        : null;

    let assistant =
      assistantResponse.status === "fulfilled" && assistantResponse.value.ok
        ? await assistantResponse.value.json()
        : { phase: "offline", text: "", agent: "jarvis" };
    assistant = applyHealthState(health, assistant);

    const presence =
      presenceResponse.status === "fulfilled" && presenceResponse.value.ok
        ? await presenceResponse.value.json()
        : {};

    const swarm =
      swarmResponse.status === "fulfilled" && swarmResponse.value.ok
        ? await swarmResponse.value.json()
        : {};

    const persona =
      personaResponse.status === "fulfilled" && personaResponse.value.ok
        ? await personaResponse.value.json()
        : {
            id: "jarvis",
            name: "Jarvis",
            color: "#00d4ff",
            role: "AI Operating System",
            skills: ["Voice", "Memory", "Tasks", "Router"],
          };

    updateUI(assistant, presence, swarm, persona);
  } catch {
    setPhase("offline");
    document.getElementById("connectionState").textContent = "Baglanti yok";
  }
}

initializeParticleHologram();

function nextPollDelay() {
  const quiet = currentPhase === "idle" || currentPhase === "offline" || currentPhase === "muted";
  if (quiet) {
    _idleStreak = Math.min(_idleStreak + 1, IDLE_SWITCH_AFTER + 2);
  } else {
    _idleStreak = 0;
  }
  return _idleStreak >= IDLE_SWITCH_AFTER ? POLL_IDLE_MS : POLL_ACTIVE_MS;
}

async function pollLoop() {
  try {
    await poll();
  } finally {
    setTimeout(pollLoop, nextPollDelay());
  }
}

pollLoop();
