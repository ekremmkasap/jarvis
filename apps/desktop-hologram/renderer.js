const BACKEND = 'http://127.0.0.1:8081';
const POLL_MS = 1500;

const AGENTS = {
  jarvis:       { name: 'JARVIS',       role: 'AI Operating System',  skills: ['Voice','Memory','Tasks','Router'] },
  opencode:     { name: 'OPENCODE',     role: 'Code Agent',           skills: ['Code','Refactor','Review','Deploy'] },
  claude:       { name: 'CLAUDE',       role: 'Analysis Agent',       skills: ['Research','Analysis','Writing','Vision'] },
  research:     { name: 'RESEARCH',     role: 'Research Agent',       skills: ['Web Search','Summarize','Cite'] },
  guard:        { name: 'GUARD',        role: 'Security Agent',       skills: ['Audit','Redaction','Hardening'] },
  ollama:       { name: 'OLLAMA',       role: 'Local LLM',            skills: ['Generate','Reason','Code'] },
  'telegram-bot': { name: 'TELEGRAM',  role: 'Bot Interface',        skills: ['Commands','Dispatch','Notify'] },
};

const STATE_LABELS = {
  idle: 'Hazir', listening: 'Dinliyor...', thinking: 'Dusunuyor...',
  speaking: 'Konusuyor...', offline: 'Cevrimdisi',
};

let currentPhase = 'idle';
let presenceData = {};

function updateUI(assistant, presence) {
  const agentKey = (assistant.agent || 'jarvis').toLowerCase();
  const agent = AGENTS[agentKey] || AGENTS.jarvis;
  const phase = assistant.phase || 'idle';

  if (phase !== currentPhase) {
    currentPhase = phase;
    document.getElementById('hologram').className = 'hologram ' + phase;
    if (window.jarvisDesktop) window.jarvisDesktop.setPhase(phase);
    if (phase === 'listening' || phase === 'speaking') {
      if (window.jarvisDesktop) window.jarvisDesktop.focusOverlay();
    }
  }

  document.getElementById('agentName').textContent = agent.name;
  document.getElementById('agentRole').textContent = agent.role;
  document.getElementById('agentState').textContent = STATE_LABELS[phase] || phase;
  document.getElementById('speechText').textContent = assistant.text || '';
  document.getElementById('previewText').textContent = assistant.latestPreview || '';
  document.getElementById('agentSkills').textContent = agent.skills.join(' · ');

  // Presence info
  const online = presence.online_agents || [];
  document.getElementById('abilityStatus').textContent = online.length ? 'Aktif: ' + online.join(', ') : '';

  // Activity meter
  const meter = { idle: 10, listening: 65, thinking: 85, speaking: 95, offline: 0 };
  document.getElementById('activityFill').style.width = (meter[phase] || 20) + '%';
  document.getElementById('connectionState').textContent = 'Bagli · ' + new Date().toLocaleTimeString('tr-TR');
}

async function poll() {
  try {
    const [ra, rp] = await Promise.allSettled([
      fetch(BACKEND + '/api/desktop-assistant'),
      fetch(BACKEND + '/api/office/presence'),
    ]);

    const assistant = (ra.status === 'fulfilled' && ra.value.ok)
      ? await ra.value.json() : { phase: 'offline', text: '', agent: 'jarvis' };

    const presence = (rp.status === 'fulfilled' && rp.value.ok)
      ? await rp.value.json() : {};

    presenceData = presence;
    updateUI(assistant, presence);
  } catch {
    document.getElementById('connectionState').textContent = 'Baglanti yok';
    document.getElementById('hologram').className = 'hologram offline';
  }
}

poll();
setInterval(poll, POLL_MS);
