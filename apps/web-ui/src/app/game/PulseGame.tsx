'use client';

import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';

const WORLD_WIDTH = 960;
const WORLD_HEIGHT = 540;
const FRAME_MS = 1000 / 60;
const PLAYER_Y = WORLD_HEIGHT - 78;
const PLAYER_WIDTH = 78;
const PLAYER_HEIGHT = 26;
const PLAYER_SPEED = 360;
const PLAYER_COOLDOWN = 0.22;
const MAX_SHIELD = 3;
const FINAL_WAVE = 3;
const LANES = [116, 240, 360, 480, 600, 720, 844];
const STARFIELD = Array.from({ length: 64 }, (_, index) => ({
  x: (index * 149) % WORLD_WIDTH,
  y: (index * 83) % WORLD_HEIGHT,
  r: index % 3 === 0 ? 2 : 1,
  alpha: 0.15 + ((index * 17) % 60) / 100,
}));

type Mode = 'menu' | 'playing' | 'victory' | 'defeat';

type HudSnapshot = {
  mode: Mode;
  score: number;
  wave: number;
  shield: number;
};

type Player = {
  x: number;
  y: number;
  width: number;
  height: number;
  speed: number;
  shield: number;
  cooldown: number;
};

type Bolt = {
  id: number;
  x: number;
  y: number;
  radius: number;
  speed: number;
};

type Drone = {
  id: number;
  lane: number;
  x: number;
  y: number;
  width: number;
  height: number;
  hp: number;
  maxHp: number;
  speed: number;
  drift: number;
  driftRate: number;
  spawnPhase: number;
};

type GameState = {
  mode: Mode;
  score: number;
  wave: number;
  totalDestroyed: number;
  destroyedInWave: number;
  targetThisWave: number;
  spawnTimer: number;
  remainingSpawns: number;
  flashTimer: number;
  message: string;
  player: Player;
  bolts: Bolt[];
  drones: Drone[];
  nextBoltId: number;
  nextDroneId: number;
  elapsed: number;
};

type GameController = {
  start: () => void;
  restart: () => void;
  dispose: () => void;
};

declare global {
  interface Window {
    render_game_to_text?: () => string;
    advanceTime?: (ms: number) => Promise<void>;
  }
}

function createInitialState(): GameState {
  return {
    mode: 'menu',
    score: 0,
    wave: 1,
    totalDestroyed: 0,
    destroyedInWave: 0,
    targetThisWave: 6,
    spawnTimer: 0.8,
    remainingSpawns: 6,
    flashTimer: 0,
    message: 'Click launch or press Enter to begin.',
    player: {
      x: WORLD_WIDTH / 2 - PLAYER_WIDTH / 2,
      y: PLAYER_Y,
      width: PLAYER_WIDTH,
      height: PLAYER_HEIGHT,
      speed: PLAYER_SPEED,
      shield: MAX_SHIELD,
      cooldown: 0,
    },
    bolts: [],
    drones: [],
    nextBoltId: 1,
    nextDroneId: 1,
    elapsed: 0,
  };
}

function createPulseGame(
  canvas: HTMLCanvasElement,
  setHud: (hud: HudSnapshot) => void,
  stage: HTMLElement,
): GameController {
  const ctx = canvas.getContext('2d') as CanvasRenderingContext2D;

  if (!ctx) {
    throw new Error('2D canvas context is required for Pulse Game.');
  }

  canvas.width = WORLD_WIDTH;
  canvas.height = WORLD_HEIGHT;

  const pressed = new Set<string>();
  const state = createInitialState();
  let rafId = 0;
  let lastFrame = 0;
  let disposed = false;
  let pendingSpace = false;
  let lastHud = '';
  let controlledByStepper = false;

  function syncHud() {
    const snapshot = JSON.stringify({
      mode: state.mode,
      score: state.score,
      wave: state.wave,
      shield: state.player.shield,
    });

    if (snapshot === lastHud) {
      return;
    }

    lastHud = snapshot;
    setHud({
      mode: state.mode,
      score: state.score,
      wave: state.wave,
      shield: state.player.shield,
    });
  }

  function configureWave(wave: number) {
    state.wave = wave;
    state.destroyedInWave = 0;
    state.targetThisWave = 4 + wave * 2;
    state.remainingSpawns = state.targetThisWave;
    state.spawnTimer = Math.max(0.42, 0.92 - wave * 0.12);
    state.message = `Wave ${wave} deployed.`;
  }

  function resetForRun() {
    const next = createInitialState();
    Object.assign(state, next);
    state.mode = 'playing';
    state.message = 'Wave 1 deployed.';
    configureWave(1);
    syncHud();
  }

  function startGame() {
    if (state.mode === 'playing') {
      return;
    }
    resetForRun();
    render();
  }

  function restartGame() {
    resetForRun();
    render();
  }

  function spawnDrone() {
    const laneIndex = (state.nextDroneId + state.wave + state.totalDestroyed) % LANES.length;
    const lane = LANES[laneIndex];
    const hp = state.wave >= 3 && state.nextDroneId % 3 === 0 ? 2 : 1;

    state.drones.push({
      id: state.nextDroneId++,
      lane,
      x: lane,
      y: -42,
      width: 48,
      height: 34,
      hp,
      maxHp: hp,
      speed: 72 + state.wave * 18 + (state.totalDestroyed % 4) * 6,
      drift: 22 + ((state.nextDroneId * 9) % 24),
      driftRate: 1.25 + (state.wave % 3) * 0.2,
      spawnPhase: state.elapsed,
    });
  }

  function fireBolt() {
    if (state.mode !== 'playing' || state.player.cooldown > 0) {
      return;
    }

    state.player.cooldown = PLAYER_COOLDOWN;
    state.bolts.push({
      id: state.nextBoltId++,
      x: state.player.x + state.player.width / 2,
      y: state.player.y - 4,
      radius: 5,
      speed: 520,
    });
  }

  function applyDamage(reason: string) {
    state.player.shield = Math.max(0, state.player.shield - 1);
    state.flashTimer = 0.28;
    state.message = reason;

    if (state.player.shield <= 0) {
      state.mode = 'defeat';
      state.message = 'Signal collapsed. Press Enter to relaunch.';
    }

    syncHud();
  }

  function completeWave() {
    if (state.wave >= FINAL_WAVE) {
      state.mode = 'victory';
      state.message = 'All drone bands cleared. Press Enter to run again.';
      syncHud();
      return;
    }

    configureWave(state.wave + 1);
    syncHud();
  }

  function update(dt: number) {
    state.elapsed += dt;

    if (state.mode !== 'playing') {
      if (state.flashTimer > 0) {
        state.flashTimer = Math.max(0, state.flashTimer - dt);
      }
      return;
    }

    if (pressed.has('ArrowLeft') || pressed.has('KeyA')) {
      state.player.x -= state.player.speed * dt;
    }

    if (pressed.has('ArrowRight') || pressed.has('KeyD')) {
      state.player.x += state.player.speed * dt;
    }

    state.player.x = Math.max(26, Math.min(WORLD_WIDTH - state.player.width - 26, state.player.x));
    state.player.cooldown = Math.max(0, state.player.cooldown - dt);
    state.flashTimer = Math.max(0, state.flashTimer - dt);

    if (pendingSpace) {
      fireBolt();
      pendingSpace = false;
    }

    state.spawnTimer -= dt;
    if (state.remainingSpawns > 0 && state.spawnTimer <= 0) {
      spawnDrone();
      state.remainingSpawns -= 1;
      state.spawnTimer = Math.max(0.4, 1 - state.wave * 0.1);
    }

    for (const bolt of state.bolts) {
      bolt.y -= bolt.speed * dt;
    }
    state.bolts = state.bolts.filter((bolt) => bolt.y + bolt.radius > -12);

    for (const drone of state.drones) {
      const wobble = Math.sin((state.elapsed - drone.spawnPhase) * drone.driftRate) * drone.drift;
      drone.x = drone.lane + wobble;
      drone.y += drone.speed * dt;
    }

    const survivors: Drone[] = [];
    for (const drone of state.drones) {
      let destroyed = false;

      for (const bolt of state.bolts) {
        const dx = bolt.x - drone.x;
        const dy = bolt.y - drone.y;
        const hitX = Math.abs(dx) < drone.width / 2 + bolt.radius;
        const hitY = Math.abs(dy) < drone.height / 2 + bolt.radius;

        if (!hitX || !hitY) {
          continue;
        }

        bolt.y = -999;
        drone.hp -= 1;
        if (drone.hp <= 0) {
          destroyed = true;
          state.score += 100 * state.wave;
          state.destroyedInWave += 1;
          state.totalDestroyed += 1;
          state.message = `Drone cluster down. ${state.targetThisWave - state.destroyedInWave} left in wave.`;
          syncHud();
        }
        break;
      }

      if (destroyed) {
        continue;
      }

      const overlapsPlayer =
        Math.abs(drone.x - (state.player.x + state.player.width / 2)) < drone.width / 2 + state.player.width / 2 - 8 &&
        Math.abs(drone.y - (state.player.y + state.player.height / 2)) < drone.height / 2 + state.player.height / 2 - 8;

      if (overlapsPlayer) {
        applyDamage('Hull impact detected.');
        continue;
      }

      if (drone.y + drone.height / 2 >= WORLD_HEIGHT - 24) {
        applyDamage('A drone leaked through the perimeter.');
        continue;
      }

      survivors.push(drone);
    }

    state.drones = survivors;
    state.bolts = state.bolts.filter((bolt) => bolt.y > -20);

    if (
      state.mode === 'playing' &&
      state.destroyedInWave >= state.targetThisWave &&
      state.remainingSpawns === 0 &&
      state.drones.length === 0
    ) {
      completeWave();
    }
  }

  function drawBackdrop() {
    const gradient = ctx.createLinearGradient(0, 0, 0, WORLD_HEIGHT);
    gradient.addColorStop(0, '#03101d');
    gradient.addColorStop(0.58, '#0a1f35');
    gradient.addColorStop(1, '#102844');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, WORLD_WIDTH, WORLD_HEIGHT);

    const glow = ctx.createRadialGradient(WORLD_WIDTH * 0.65, 92, 40, WORLD_WIDTH * 0.65, 92, 250);
    glow.addColorStop(0, 'rgba(97, 237, 255, 0.26)');
    glow.addColorStop(1, 'rgba(97, 237, 255, 0)');
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, WORLD_WIDTH, WORLD_HEIGHT);

    for (const star of STARFIELD) {
      ctx.fillStyle = `rgba(255, 255, 255, ${star.alpha})`;
      ctx.beginPath();
      ctx.arc(star.x, star.y, star.r, 0, Math.PI * 2);
      ctx.fill();
    }

    ctx.strokeStyle = 'rgba(96, 180, 255, 0.14)';
    ctx.lineWidth = 1;
    for (let x = 0; x <= WORLD_WIDTH; x += 80) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, WORLD_HEIGHT);
      ctx.stroke();
    }
    for (let y = 0; y <= WORLD_HEIGHT; y += 60) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(WORLD_WIDTH, y);
      ctx.stroke();
    }

    const floor = ctx.createLinearGradient(0, WORLD_HEIGHT - 120, 0, WORLD_HEIGHT);
    floor.addColorStop(0, 'rgba(11, 49, 82, 0)');
    floor.addColorStop(1, 'rgba(10, 84, 126, 0.72)');
    ctx.fillStyle = floor;
    ctx.fillRect(0, WORLD_HEIGHT - 120, WORLD_WIDTH, 120);
  }

  function drawPlayer() {
    const centerX = state.player.x + state.player.width / 2;
    const centerY = state.player.y + state.player.height / 2;

    ctx.save();
    ctx.translate(centerX, centerY);
    ctx.shadowColor = 'rgba(67, 240, 255, 0.65)';
    ctx.shadowBlur = 18;
    ctx.fillStyle = state.flashTimer > 0 ? '#ffe3a1' : '#6ff3ff';
    ctx.beginPath();
    ctx.moveTo(-34, 12);
    ctx.lineTo(0, -18);
    ctx.lineTo(34, 12);
    ctx.lineTo(8, 8);
    ctx.lineTo(0, 18);
    ctx.lineTo(-8, 8);
    ctx.closePath();
    ctx.fill();

    ctx.fillStyle = '#0d3154';
    ctx.beginPath();
    ctx.moveTo(-10, 8);
    ctx.lineTo(0, -6);
    ctx.lineTo(10, 8);
    ctx.closePath();
    ctx.fill();
    ctx.restore();
  }

  function drawBolts() {
    for (const bolt of state.bolts) {
      ctx.fillStyle = '#fff7d6';
      ctx.shadowColor = 'rgba(255, 229, 148, 0.7)';
      ctx.shadowBlur = 12;
      ctx.beginPath();
      ctx.arc(bolt.x, bolt.y, bolt.radius, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.shadowBlur = 0;
  }

  function drawDrones() {
    for (const drone of state.drones) {
      ctx.save();
      ctx.translate(drone.x, drone.y);
      ctx.shadowColor = 'rgba(255, 161, 89, 0.45)';
      ctx.shadowBlur = 14;
      ctx.fillStyle = drone.hp > 1 ? '#ffb366' : '#ff7c53';
      ctx.beginPath();
      ctx.moveTo(0, -18);
      ctx.lineTo(24, -4);
      ctx.lineTo(18, 15);
      ctx.lineTo(0, 22);
      ctx.lineTo(-18, 15);
      ctx.lineTo(-24, -4);
      ctx.closePath();
      ctx.fill();

      ctx.fillStyle = '#2d1209';
      ctx.fillRect(-8, -4, 16, 8);
      ctx.restore();

      if (drone.maxHp > 1) {
        ctx.fillStyle = 'rgba(12, 21, 34, 0.75)';
        ctx.fillRect(drone.x - 24, drone.y - 33, 48, 5);
        ctx.fillStyle = '#ffe7a6';
        ctx.fillRect(drone.x - 24, drone.y - 33, 48 * (drone.hp / drone.maxHp), 5);
      }
    }
  }

  function drawHud() {
    ctx.save();
    ctx.fillStyle = 'rgba(4, 12, 23, 0.72)';
    ctx.fillRect(18, 18, 286, 74);
    ctx.strokeStyle = 'rgba(120, 212, 255, 0.3)';
    ctx.strokeRect(18, 18, 286, 74);

    ctx.fillStyle = '#9fe8ff';
    ctx.font = '700 22px JetBrains Mono, monospace';
    ctx.fillText(`Score ${state.score}`, 34, 47);
    ctx.font = '600 15px JetBrains Mono, monospace';
    ctx.fillStyle = '#dff8ff';
    ctx.fillText(`Wave ${state.wave}/${FINAL_WAVE}`, 34, 71);
    ctx.fillText(`Shield ${state.player.shield}`, 170, 71);
    ctx.fillText(`${state.destroyedInWave}/${state.targetThisWave} cleared`, 34, 89);

    if (state.mode !== 'playing') {
      ctx.fillStyle = 'rgba(4, 12, 23, 0.75)';
      ctx.fillRect(0, 0, WORLD_WIDTH, WORLD_HEIGHT);
      ctx.fillStyle = state.mode === 'victory' ? '#9ff8c8' : state.mode === 'defeat' ? '#ffc29d' : '#9fe8ff';
      ctx.font = '700 42px JetBrains Mono, monospace';
      const title =
        state.mode === 'menu'
          ? 'Pulse Siege'
          : state.mode === 'victory'
            ? 'Sector Secure'
            : 'Signal Lost';
      const titleWidth = ctx.measureText(title).width;
      ctx.fillText(title, WORLD_WIDTH / 2 - titleWidth / 2, 170);

      ctx.font = '600 18px JetBrains Mono, monospace';
      ctx.fillStyle = '#dff8ff';
      const lines =
        state.mode === 'menu'
          ? [
              'Arrow Left / Right: strafe',
              'Space: fire pulse',
              'F: fullscreen',
              'Clear three waves before shield reaches zero.',
            ]
          : [state.message, 'Press Enter to relaunch the simulation.'];

      lines.forEach((line, index) => {
        const width = ctx.measureText(line).width;
        ctx.fillText(line, WORLD_WIDTH / 2 - width / 2, 232 + index * 34);
      });
    } else {
      ctx.fillStyle = '#b8dfff';
      ctx.font = '500 15px JetBrains Mono, monospace';
      ctx.fillText(state.message, 334, 46);
      ctx.fillText('Press F for fullscreen', 334, 70);
    }
    ctx.restore();
  }

  function render() {
    drawBackdrop();
    drawBolts();
    drawDrones();
    drawPlayer();
    drawHud();
  }

  function toTextState() {
    return JSON.stringify({
      mode: state.mode,
      coordinate_system: 'origin top-left; +x right; +y down',
      canvas: { width: WORLD_WIDTH, height: WORLD_HEIGHT },
      player: {
        x: Number((state.player.x + state.player.width / 2).toFixed(1)),
        y: Number((state.player.y + state.player.height / 2).toFixed(1)),
        width: state.player.width,
        height: state.player.height,
        shield: state.player.shield,
        cooldown_ms: Math.round(state.player.cooldown * 1000),
      },
      wave: {
        current: state.wave,
        target: state.targetThisWave,
        destroyed: state.destroyedInWave,
        remaining_spawns: state.remainingSpawns,
        spawn_in_ms: Math.max(0, Math.round(state.spawnTimer * 1000)),
      },
      score: state.score,
      drones: state.drones.map((drone) => ({
        x: Number(drone.x.toFixed(1)),
        y: Number(drone.y.toFixed(1)),
        width: drone.width,
        height: drone.height,
        hp: drone.hp,
      })),
      bolts: state.bolts.map((bolt) => ({
        x: Number(bolt.x.toFixed(1)),
        y: Number(bolt.y.toFixed(1)),
      })),
      message: state.message,
    });
  }

  async function stepFor(ms: number) {
    controlledByStepper = true;
    const steps = Math.max(1, Math.round(ms / FRAME_MS));
    for (let index = 0; index < steps; index += 1) {
      update(FRAME_MS / 1000);
    }
    render();
  }

  function animate(ts: number) {
    if (disposed) {
      return;
    }

    if (!lastFrame) {
      lastFrame = ts;
    }

    if (controlledByStepper) {
      lastFrame = ts;
      render();
      rafId = window.requestAnimationFrame(animate);
      return;
    }

    const dt = Math.min((ts - lastFrame) / 1000, 0.05);
    lastFrame = ts;
    update(dt);
    render();
    rafId = window.requestAnimationFrame(animate);
  }

  async function toggleFullscreen() {
    if (document.fullscreenElement) {
      await document.exitFullscreen();
      return;
    }

    if (stage.requestFullscreen) {
      await stage.requestFullscreen();
    }
  }

  function handleKeyDown(event: KeyboardEvent) {
    if (event.code === 'Enter' && state.mode !== 'playing') {
      event.preventDefault();
      restartGame();
      return;
    }

    if (event.code === 'Space') {
      event.preventDefault();
      pressed.add(event.code);
      pendingSpace = true;
      return;
    }

    if (event.code === 'KeyF') {
      event.preventDefault();
      void toggleFullscreen();
      return;
    }

    if (event.code.startsWith('Arrow') || event.code === 'KeyA' || event.code === 'KeyD') {
      event.preventDefault();
      pressed.add(event.code);
    }
  }

  function handleKeyUp(event: KeyboardEvent) {
    pressed.delete(event.code);
    if (event.code === 'Space') {
      pendingSpace = false;
    }
  }

  window.addEventListener('keydown', handleKeyDown);
  window.addEventListener('keyup', handleKeyUp);
  window.render_game_to_text = toTextState;
  window.advanceTime = stepFor;

  syncHud();
  render();
  rafId = window.requestAnimationFrame(animate);

  return {
    start: startGame,
    restart: restartGame,
    dispose: () => {
      disposed = true;
      window.cancelAnimationFrame(rafId);
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
      delete window.render_game_to_text;
      delete window.advanceTime;
    },
  };
}

export default function PulseGame() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const stageRef = useRef<HTMLDivElement | null>(null);
  const controllerRef = useRef<GameController | null>(null);
  const [hud, setHud] = useState<HudSnapshot>({
    mode: 'menu',
    score: 0,
    wave: 1,
    shield: 3,
  });

  useEffect(() => {
    const canvas = canvasRef.current;
    const stage = stageRef.current;

    if (!canvas || !stage) {
      return undefined;
    }

    const controller = createPulseGame(canvas, setHud, stage);
    controllerRef.current = controller;

    return () => {
      controller.dispose();
      controllerRef.current = null;
    };
  }, []);

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,#173257_0%,#09111f_58%,#05070d_100%)] px-4 py-8 text-slate-100">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.4em] text-cyan-300/70">Arcade Route</p>
            <h1 className="mt-2 font-mono text-4xl font-semibold tracking-tight text-cyan-100">Pulse Siege</h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-cyan-50/80">
              Single-canvas survival testbed for the mission-control UI. Clear three waves, keep the shield online,
              and use the deterministic hooks for automation.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3 text-xs uppercase tracking-[0.25em]">
            <Link
              href="/"
              className="rounded-full border border-cyan-400/30 bg-cyan-400/10 px-4 py-2 text-cyan-100 transition hover:border-cyan-300/70 hover:bg-cyan-300/15"
            >
              Dashboard
            </Link>
            <button
              id="start-btn"
              type="button"
              onClick={() => controllerRef.current?.start()}
              className="rounded-full border border-amber-300/40 bg-amber-300/10 px-4 py-2 text-amber-100 transition hover:border-amber-200/70 hover:bg-amber-200/15"
            >
              Launch
            </button>
            <button
              id="restart-btn"
              type="button"
              onClick={() => controllerRef.current?.restart()}
              className="rounded-full border border-slate-200/20 bg-slate-200/10 px-4 py-2 text-slate-100 transition hover:border-slate-100/60 hover:bg-slate-100/15"
            >
              Restart
            </button>
          </div>
        </div>

        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_300px]">
          <div
            ref={stageRef}
            className="relative overflow-hidden rounded-[28px] border border-cyan-300/20 bg-slate-950/70 p-3 shadow-[0_30px_90px_rgba(4,12,24,0.55)]"
          >
            <canvas
              ref={canvasRef}
              className="mx-auto block aspect-video w-full rounded-[20px] border border-white/10 bg-[#07111f]"
            />
          </div>

          <aside className="rounded-[28px] border border-white/10 bg-slate-950/60 p-5 text-sm text-slate-200 shadow-[0_24px_60px_rgba(2,8,16,0.45)]">
            <div className="rounded-2xl border border-cyan-300/15 bg-cyan-300/5 p-4">
              <p className="text-[11px] uppercase tracking-[0.28em] text-cyan-200/70">Live Snapshot</p>
              <div className="mt-4 space-y-3 font-mono text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Mode</span>
                  <span className="text-cyan-100">{hud.mode}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Score</span>
                  <span className="text-cyan-100">{hud.score}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Wave</span>
                  <span className="text-cyan-100">{hud.wave}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Shield</span>
                  <span className="text-cyan-100">{hud.shield}</span>
                </div>
              </div>
            </div>

            <div className="mt-5 rounded-2xl border border-white/10 bg-white/5 p-4">
              <p className="text-[11px] uppercase tracking-[0.28em] text-slate-300/75">Controls</p>
              <ul className="mt-3 space-y-2 text-sm text-slate-200/85">
                <li>Arrow Left / Right or A / D to strafe.</li>
                <li>Space to fire one pulse per cooldown.</li>
                <li>Enter relaunches after victory or defeat.</li>
                <li>F toggles fullscreen.</li>
              </ul>
            </div>

            <div className="mt-5 rounded-2xl border border-amber-300/15 bg-amber-300/5 p-4">
              <p className="text-[11px] uppercase tracking-[0.28em] text-amber-100/70">Automation Hooks</p>
              <ul className="mt-3 space-y-2 font-mono text-xs leading-5 text-amber-50/80">
                <li>`window.render_game_to_text()` returns concise JSON game state.</li>
                <li>`window.advanceTime(ms)` steps the simulation deterministically.</li>
              </ul>
            </div>
          </aside>
        </div>
      </div>
    </main>
  );
}
