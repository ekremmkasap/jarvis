#\!/usr/bin/env python3
import json, sqlite3, uuid
from datetime import datetime

DB_PATH = "/home/userk/.jarvis/tasks.db"

def _init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY, title TEXT, goal TEXT,
        status TEXT DEFAULT 'queued', plan TEXT DEFAULT '[]',
        result TEXT, events TEXT DEFAULT '[]',
        created_at TEXT, updated_at TEXT)""")
    conn.commit(); conn.close()

def _save(tid, title, goal, status, plan, result, events):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""INSERT OR REPLACE INTO tasks
            (id,title,goal,status,plan,result,events,created_at,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (tid,title,goal,status,
             json.dumps(plan,ensure_ascii=False), result,
             json.dumps(events,ensure_ascii=False),
             datetime.now().isoformat(), datetime.now().isoformat()))
        conn.commit(); conn.close()
    except: pass

class OrchestratorSkill:
    def __init__(self, ollama_fn):
        self.call = ollama_fn
        _init_db()

    def run(self, goal):
        tid = str(uuid.uuid4())[:8]
        events = []
        def log(m): events.append({"t": datetime.now().strftime("%H:%M"), "m": m})
        log("Gorev basladi: " + goal[:50])
        _save(tid, goal[:60], goal, "planning", [], None, events)
        try:
            plan = self._plan(goal)
            log(str(len(plan)) + " adim")
            _save(tid, goal[:60], goal, "running", plan, None, events)
            step_results = []
            for i, step in enumerate(plan[:3]):
                log("Adim " + str(i+1) + ": " + step[:40])
                res = self._implement(goal, step, step_results)
                step_results.append({"step": step, "result": res})
            _save(tid, goal[:60], goal, "reviewing", plan, None, events)
            log("Sentez")
            final = self._synthesize(goal, step_results)
            log("Tamam")
            _save(tid, goal[:60], goal, "done", plan, final, events)
            ev = " | ".join([e["m"] for e in events[-3:]])
            return "*Gorev #" + tid + " tamamlandi*" + "\n\n" + final + "\n\n_[" + ev + "]_"
        except Exception as e:
            log("HATA: " + str(e))
            _save(tid, goal[:60], goal, "failed", [], str(e), events)
            return "Gorev #" + tid + " basarisiz: " + str(e)

    def _plan(self, goal):
        prompt = "Su gorevi 2-3 net adima bol. Sadece madde listesi yaz, aciklama yok.\nGOREV: " + goal + "\nADIMLAR:"
        resp = self.call("llama3.2:latest",
            [{"role": "user", "content": prompt}],
            "Gorev planlayicisisin. Kisa Turkce adimlar.")
        lines = [l.strip().lstrip("0123456789.-*) ").strip() for l in resp.strip().split("\n") if len(l.strip()) > 6]
        return lines[:3] or [goal]

    def _implement(self, goal, step, prev):
        ctx = ""
        if prev:
            ctx = "\nOnceki: " + "; ".join(r["step"][:30] + ": " + r["result"][:80] for r in prev)
        is_code = any(k in step.lower() for k in ["kod", "python", "api", "yaz", "script"])
        model = "deepseek-coder:latest" if is_code else "llama3.2:latest"
        sys_p = "Yazilim gelistirici. Calisir kod uret." if is_code else "Uygulama ajani. Adimi eksiksiz uygula. Turkce."
        prompt = "Hedef: " + goal + ctx + "\nYAP: " + step + "\nNet Turkce cevap:"
        return self.call(model, [{"role": "user", "content": prompt}], sys_p)

    def _synthesize(self, goal, step_results):
        txt = "\n".join(r["step"] + ": " + r["result"][:200] for r in step_results)
        prompt = "Hedef: " + goal + "\nAdimlar:\n" + txt + "\nSentezle. Turkce, net final cevap:"
        return self.call("llama3.2:latest",
            [{"role": "user", "content": prompt}],
            "Sentez uzmanisi. Adim sonuclari net cevaba donustur. Turkce.")

def get_task_history(limit=5):
    try:
        _init_db()
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("SELECT id,title,status,updated_at FROM tasks ORDER BY updated_at DESC LIMIT ?", (limit,)).fetchall()
        conn.close()
        if not rows: return "Gorev yok."
        icons = {"done": "OK", "failed": "X", "running": ">", "planning": "o", "queued": "-", "blocked": "\!"}
        lines = ["Son Gorevler:\n"]
        for tid, title, status, ts in rows:
            lines.append("[" + icons.get(status, "?") + "] #" + tid + " - " + title[:45] + " (" + (ts or "")[:10] + ")")
        return "\n".join(lines)
    except Exception as e:
        return "Gecmis hatasi: " + str(e)
