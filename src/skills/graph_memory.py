import sqlite3
import json
import logging
from datetime import datetime

log = logging.getLogger("knowledge_graph")

class KnowledgeGraph:
    def __init__(self, db_path="/home/userk/.jarvis/knowledge_graph.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS entities
                     (id INTEGER PRIMARY KEY, name TEXT UNIQUE, type TEXT, created_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS relations
                     (id INTEGER PRIMARY KEY, source_id INTEGER, target_id INTEGER, 
                      relation_type TEXT, weight REAL, created_at TEXT,
                      FOREIGN KEY(source_id) REFERENCES entities(id),
                      FOREIGN KEY(target_id) REFERENCES entities(id))''')
        c.execute('''CREATE TABLE IF NOT EXISTS observations
                     (id INTEGER PRIMARY KEY, entity_id INTEGER, note TEXT, created_at TEXT,
                      FOREIGN KEY(entity_id) REFERENCES entities(id))''')
        conn.commit()
        conn.close()

    def add_entity(self, name, entity_type="concept"):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO entities (name, type, created_at) VALUES (?, ?, ?)",
                      (name.lower(), entity_type, datetime.now().isoformat()))
            conn.commit()
            return c.lastrowid
        except sqlite3.IntegrityError:
            c.execute("SELECT id FROM entities WHERE name = ?", (name.lower(),))
            return c.fetchone()[0]
        finally:
            conn.close()

    def add_relation(self, source_name, target_name, relation_type):
        source_id = self.add_entity(source_name)
        target_id = self.add_entity(target_name)
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT INTO relations (source_id, target_id, relation_type, weight, created_at) VALUES (?, ?, ?, ?, ?)",
                  (source_id, target_id, relation_type, 1.0, datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def add_observation(self, entity_name, note):
        entity_id = self.add_entity(entity_name)
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT INTO observations (entity_id, note, created_at) VALUES (?, ?, ?)",
                  (entity_id, note, datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def search_graph(self, query):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''SELECT e.name, o.note FROM entities e 
                     JOIN observations o ON e.id = o.entity_id 
                     WHERE e.name LIKE ? OR o.note LIKE ?''', (f"%{query.lower()}%", f"%{query}%"))
        results = set(c.fetchall())
        
        c.execute('''SELECT e1.name, r.relation_type, e2.name FROM relations r
                     JOIN entities e1 ON r.source_id = e1.id
                     JOIN entities e2 ON r.target_id = e2.id
                     WHERE e1.name LIKE ? OR e2.name LIKE ?''', (f"%{query.lower()}%", f"%{query.lower()}%"))
        relations = c.fetchall()
        conn.close()
        
        return {"observations": list(results), "relations": relations}

graph_db = KnowledgeGraph()
