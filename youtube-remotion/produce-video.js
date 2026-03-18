#!/usr/bin/env node
// produce-video.js - Kie.ai + ElevenLabs + Remotion Pipeline
// Kullanim: node produce-video.js --prompt "Konu"

const dotenv = require('dotenv');
dotenv.config({ path: require('path').join(__dirname, '.env'), override: true });
const axios = require('axios');
const fs    = require('fs-extra');
const path  = require('path');

const STORYBOARD = path.join(__dirname, 'my-video', 'src', 'data', 'storyboard.json');
const VIDEOS_DIR = path.join(__dirname, 'my-video', 'public', 'assets', 'videos');
const AUDIOS_DIR = path.join(__dirname, 'my-video', 'public', 'assets', 'audios');

function slugify(t) {
  return t.toLowerCase()
    .replace(/[ğ]/g,'g').replace(/[ü]/g,'u').replace(/[ş]/g,'s')
    .replace(/[ı]/g,'i').replace(/[ö]/g,'o').replace(/[ç]/g,'c')
    .replace(/[^a-z0-9]+/g,'_').replace(/^_+|_+$/g,'').slice(0,40);
}

function generatePlan(prompt) {
  return {
    title: prompt.trim(),
    scenes: [
      { id:'1', title:'Giris',   narration: prompt + ' - merak uyandirici giris.', videoPrompt: 'Cinematic wide establishing shot, dramatic lighting, epic atmosphere, 8K film grain, ' + prompt, duration: 6 },
      { id:'2', title:'ArkaPlani', narration: prompt + ' - tarihi ve kulturel arka plan.', videoPrompt: 'Slow aerial drone shot, historical context, atmospheric fog, cinematic 8K', duration: 6 },
      { id:'3', title:'AnaOlay',  narration: prompt + ' - kritik ve etkileyici doruk noktasi.', videoPrompt: 'Dynamic action shot, dramatic close-up, intense lighting, cinematic 8K', duration: 6 },
      { id:'4', title:'Sonuc',   narration: prompt + ' - sonucu ve tarihe etkisi.', videoPrompt: 'Wide panoramic shot, golden hour lighting, peaceful aftermath, depth of field 8K', duration: 6 },
      { id:'5', title:'Kapalis',  narration: prompt + ' - ilham verici kapalis mesaji.', videoPrompt: 'Slow zoom out epic wide shot, inspirational atmosphere, cinematic color grade 8K', duration: 6 },
    ]
  };
}

async function generateTTS(text, filename) {
  const out = path.join(AUDIOS_DIR, filename);
  if (await fs.pathExists(out)) { console.log('  [TTS] Mevcut:', filename); return; }
  const r = await axios.post(
    'https://api.elevenlabs.io/v1/text-to-speech/' + process.env.ELEVENLABS_VOICE_ID,
    { text, model_id: 'eleven_multilingual_v2', voice_settings: { stability: 0.5, similarity_boost: 0.75 } },
    { headers: { 'xi-api-key': process.env.ELEVENLABS_API_KEY, 'Content-Type': 'application/json', Accept: 'audio/mpeg' }, responseType: 'arraybuffer' }
  );
  await fs.writeFile(out, r.data);
  console.log('  [TTS] OK:', filename);
}

async function generateVideo(prompt, filename) {
  const out = path.join(VIDEOS_DIR, filename);
  if (await fs.pathExists(out)) { console.log('  [VIDEO] Mevcut:', filename); return; }
  const hdrs = { Authorization: 'Bearer ' + process.env.KIE_AI_API_KEY, 'Content-Type': 'application/json' };
  const cr = await axios.post('https://api.kie.ai/api/v1/jobs/createTask',
    { model: 'grok-imagine/text-to-video', callBackUrl: '', input: { prompt, aspect_ratio: '16:9', mode: 'normal', duration: '6', resolution: '720p' } },
    { headers: hdrs });
  const taskId = cr.data.taskId;
  console.log('  [VIDEO] Task:', taskId);
  for (let i = 0; i < 60; i++) {
    await new Promise(r => setTimeout(r, 5000));
    const sr = await axios.get('https://api.kie.ai/api/v1/jobs/recordInfo?taskId=' + taskId, { headers: hdrs });
    const d  = sr.data.data || sr.data;
    const st = d.state || d.status;
    if (st === 'success' || st === 'completed') {
      let url;
      try { const rj = typeof d.resultJson === 'string' ? JSON.parse(d.resultJson) : d.resultJson; url = rj.video_url || (rj.resultUrls && rj.resultUrls[0]); } catch(_){}
      url = url || d.video_url;
      if (!url) throw new Error('video_url yok');
      const dl = await axios.get(url, { responseType: 'arraybuffer' });
      await fs.writeFile(out, dl.data);
      console.log('  [VIDEO] OK:', filename);
      return;
    } else if (st === 'failed' || st === 'error') throw new Error('Kie.ai: ' + (d.failMsg || 'basarisiz'));
    console.log('  [VIDEO] Bekleniyor... (' + (i+1) + '/60) state=' + st);
  }
  throw new Error('Timeout: video uretilemedi');
}

function check() {
  const keys = ['KIE_AI_API_KEY','ELEVENLABS_API_KEY','ELEVENLABS_VOICE_ID'];
  let ok = true;
  console.log('--- ENV KONTROLU ---');
  for (const k of keys) {
    const v = process.env[k];
    if (!v || v.startsWith('your_')) { console.log('  EKSIK: ' + k); ok = false; }
    else console.log('  OK: ' + k + ' = ' + v.slice(0,8) + '...');
  }
  if (ok) console.log('[CHECK] Hazir!');
  else    console.log('[CHECK] .env dosyasini doldurun!');
  return ok;
}

async function main() {
  const args = process.argv.slice(2);
  if (args.includes('--check')) { check(); return; }
  const pi = args.indexOf('--prompt');
  if (pi === -1 || !args[pi+1]) { console.log('Kullanim: node produce-video.js --prompt "Konu"'); process.exit(1); }
  const prompt = args.slice(pi+1).join(' ');
  console.log('=== JARVIS VIDEO PIPELINE ===');
  console.log('Konu:', prompt);
  if (!check()) process.exit(1);
  await fs.ensureDir(VIDEOS_DIR);
  await fs.ensureDir(AUDIOS_DIR);
  const plan = generatePlan(prompt);
  console.log('[PLAN]', plan.scenes.length, 'sahne');
  const sceneFiles = [];
  for (const s of plan.scenes) {
    console.log('--- Sahne ' + s.id + ': ' + s.title + ' ---');
    const sl = slugify(s.title);
    const af = 'scene_' + s.id + '_' + sl + '.mp3';
    const vf = 'scene_' + s.id + '_' + sl + '.mp4';
    await Promise.all([ generateTTS(s.narration, af), generateVideo(s.videoPrompt, vf) ]);
    sceneFiles.push({ audio: af, video: vf });
  }
  const FPS = 30;
  const sb = { title: plan.title, fps: FPS, scenes: plan.scenes.map((s,i) => ({
    id: s.id, title: s.title,
    videoFile: sceneFiles[i].video, audioFile: sceneFiles[i].audio,
    durationFrames: s.duration * FPS, subtitle: s.narration.slice(0,80)
  }))};
  await fs.writeJson(STORYBOARD, sb, { spaces: 2 });
  console.log('[STORYBOARD] Guncellendi');
  const { execSync } = require('child_process');
  execSync('npm run build', { cwd: path.join(__dirname, 'my-video'), stdio: 'inherit' });
  console.log('=== VIDEO HAZIR: my-video/out/video.mp4 ===');
}

main().catch(e => { console.error('HATA:', e.message); process.exit(1); });
