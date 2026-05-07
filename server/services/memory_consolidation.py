"""
Session-Between Memory Consolidation — Otonom Öğrenme Sistemi

Claude Code'un autoDream pattern'ini Jarvis'e uyarla.
Her N session'dan veya T saat arayla eski oturumları analiz et,
pattern'leri çıkar ve uzun-süreli belleğe konsalide et.

Avantajlar:
  1. Bug pattern recognition — sık hataları öğren
  2. User preference learning — davranış pattern'leri
  3. Workflow optimization — bottleneck'leri detect et
  4. Zero manual intervention — fully autonomous
"""

import json
import sqlite3
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import Counter
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConsolidationPattern:
    """Konsalide edilen pattern"""
    name: str
    description: str
    frequency: int
    examples: List[str]
    recommendation: Optional[str] = None


def load_recent_sessions(
    db_path: str,
    limit: int = 10,
    hours_back: int = 24
) -> List[Dict[str, Any]]:
    """
    SQL'deki son N session'ı veya son T saat'ı yükle.
    
    Beklediğimiz table structure (state/Jarvis.db):
      CREATE TABLE conversations (
        id INTEGER PRIMARY KEY,
        session_id TEXT,
        timestamp DATETIME,
        user_message TEXT,
        assistant_message TEXT,
        error_log TEXT
      )
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        
        query = '''
            SELECT * FROM conversations
            WHERE timestamp > ?
            ORDER BY timestamp DESC
            LIMIT ?
        '''
        
        cursor.execute(query, (cutoff_time.isoformat(), limit))
        rows = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        logger.info(f"Loaded {len(rows)} conversation records from {hours_back}h")
        return rows
    
    except Exception as e:
        logger.error(f"Failed to load sessions: {e}")
        return []


def extract_error_patterns(sessions: List[Dict[str, Any]]) -> ConsolidationPattern:
    """
    Error pattern'lerini analiz et.
    
    Returns:
      ConsolidationPattern with error types and frequencies
    """
    error_types = Counter()
    error_examples = []
    
    for session in sessions:
        if session.get('error_log'):
            try:
                errors = json.loads(session['error_log']) if isinstance(session['error_log'], str) else session['error_log']
                if isinstance(errors, list):
                    for err in errors:
                        error_type = err.get('type', 'unknown_error')
                        error_types[error_type] += 1
                        error_examples.append(f"{error_type}: {err.get('message', '')[:100]}")
            except:
                pass
    
    if not error_types:
        return None
    
    top_errors = error_types.most_common(5)
    recommendation = None
    
    if top_errors[0][1] > 3:  # 3+ kez tekrarlanan aynı error
        top_error_type = top_errors[0][0]
        recommendation = f"Implement error handler for frequent '{top_error_type}' errors. Seen {top_errors[0][1]} times."
    
    return ConsolidationPattern(
        name="error_patterns",
        description="Sık tekrarlanan hata tipleri",
        frequency=sum(count for _, count in top_errors),
        examples=error_examples[:10],
        recommendation=recommendation
    )


def extract_user_preferences(sessions: List[Dict[str, Any]]) -> ConsolidationPattern:
    """
    User davranış pattern'lerini analiz et.
    
    Örneğin:
      - Sabah 9-11: intense coding sessions
      - Akşam 18:00: report generation
      - Thursday: weekly meeting prep
    """
    user_queries = []
    
    for session in sessions:
        if session.get('user_message'):
            msg = session['user_message'].lower()
            # Extract query intent
            if any(x in msg for x in ['write', 'create', 'generate']):
                user_queries.append('content_creation')
            elif any(x in msg for x in ['debug', 'error', 'fix', 'test']):
                user_queries.append('debugging')
            elif any(x in msg for x in ['analyze', 'report', 'summary']):
                user_queries.append('analysis')
            elif any(x in msg for x in ['search', 'find', 'research']):
                user_queries.append('research')
    
    if not user_queries:
        return None
    
    query_freq = Counter(user_queries)
    top_query = query_freq.most_common(1)[0][0]
    
    return ConsolidationPattern(
        name="user_preferences",
        description="Genel kullanım pattern'leri",
        frequency=len(user_queries),
        examples=sorted(set(user_queries)),
        recommendation=f"User primarily uses Jarvis for {top_query}. Optimize for this workflow."
    )


def extract_workflow_bottlenecks(sessions: List[Dict[str, Any]]) -> ConsolidationPattern:
    """
    İş akışı darboğazları ve yavaş adımları detect et.
    
    Örneğin:
      - Dosya okuma çok yavaş
      - Bash komutları timeout oluyor
      - API rate limiting'e takılıyoruz
    """
    bottlenecks = Counter()
    
    for session in sessions:
        msg = session.get('assistant_message', '').lower()
        
        if any(x in msg for x in ['timeout', 'timed out']):
            bottlenecks['timeout_issues'] += 1
        elif any(x in msg for x in ['rate limit', 'too many requests']):
            bottlenecks['rate_limiting'] += 1
        elif any(x in msg for x in ['permission denied', 'access denied']):
            bottlenecks['permission_issues'] += 1
        elif any(x in msg for x in ['retry', 'retrying']):
            bottlenecks['retry_loop'] += 1
    
    if not bottlenecks:
        return None
    
    top_bottleneck = bottlenecks.most_common(1)[0]
    
    recommendation = None
    if top_bottleneck[0] == 'timeout_issues':
        recommendation = "Implement async processing or parallel execution to avoid timeouts"
    elif top_bottleneck[0] == 'rate_limiting':
        recommendation = "Add exponential backoff and request batching"
    elif top_bottleneck[0] == 'permission_issues':
        recommendation = "Review file/folder permissions and credential refresh cycles"
    
    return ConsolidationPattern(
        name="workflow_bottlenecks",
        description="İş akışında sık karşılaşılan sorunlar",
        frequency=sum(bottlenecks.values()),
        examples=list(bottlenecks.keys()),
        recommendation=recommendation
    )


def consolidate_learnings(
    db_path: str,
    memory_dir: str,
    session_limit: int = 10,
    hours_back: int = 24
) -> Dict[str, Any]:
    """
    Session'lar arasından learnings'i konsalide et.
    
    Args:
      db_path: SQLite database path
      memory_dir: Konsolide edilmiş learnings'in kaydedileceği dizin
      session_limit: Kaç session analiz edilecek
      hours_back: Ne kadar geriye bakılacak
    
    Returns:
      Consolidation summary
    """
    logger.info(f"Starting memory consolidation... (limit={session_limit}, hours={hours_back})")
    
    # Load sessions
    sessions = load_recent_sessions(db_path, limit=session_limit, hours_back=hours_back)
    
    if not sessions:
        logger.warning("No sessions found for consolidation")
        return {'status': 'no_data'}
    
    # Extract patterns
    patterns = {}
    
    error_patterns = extract_error_patterns(sessions)
    if error_patterns:
        patterns['error_patterns'] = asdict(error_patterns)
    
    user_prefs = extract_user_preferences(sessions)
    if user_prefs:
        patterns['user_preferences'] = asdict(user_prefs)
    
    bottlenecks = extract_workflow_bottlenecks(sessions)
    if bottlenecks:
        patterns['workflow_bottlenecks'] = asdict(bottlenecks)
    
    # Save to memory directory
    os.makedirs(memory_dir, exist_ok=True)
    
    output_file = os.path.join(memory_dir, 'consolidated_learnings.json')
    
    consolidated = {
        'timestamp': datetime.now().isoformat(),
        'sessions_analyzed': len(sessions),
        'hours_back': hours_back,
        'patterns': patterns,
        'summary': {
            'total_errors': sum(p.get('frequency', 0) for p in patterns.values() if 'error' in p.get('name', '')),
            'total_observations': len(sessions),
            'recommendations': [p.get('recommendation') for p in patterns.values() if p.get('recommendation')]
        }
    }
    
    with open(output_file, 'w') as f:
        json.dump(consolidated, f, indent=2)
    
    logger.info(f"✓ Consolidation complete: {output_file}")
    logger.info(f"  - Patterns extracted: {len(patterns)}")
    logger.info(f"  - Recommendations: {len(consolidated['summary']['recommendations'])}")
    
    return consolidated


# ===== Integration: Background Scheduler =====

class ConsolidationScheduler:
    """
    Background thread'de memory consolidation'u schedule et.
    
    Kullanım (master_launcher.py'da):
      from server.services.memory_consolidation import ConsolidationScheduler
      
      scheduler = ConsolidationScheduler(
          db_path='state/Jarvis.db',
          memory_dir='state/agent_memory/consolidated',
          check_interval_seconds=3600  # Her saat
      )
      scheduler.start()
    """
    
    SESSION_THRESHOLD = 10  # Her 10 session'da
    TIME_THRESHOLD = timedelta(hours=6)  # Veya 6 saat arayla
    
    def __init__(
        self,
        db_path: str,
        memory_dir: str,
        check_interval_seconds: int = 3600
    ):
        self.db_path = db_path
        self.memory_dir = memory_dir
        self.check_interval = check_interval_seconds
        self.last_consolidation = datetime.now()
        self.session_count_since_last = 0
        self.running = False
    
    def should_consolidate(self) -> bool:
        """Consolidation yapılmalı mı?"""
        time_elapsed = datetime.now() - self.last_consolidation
        
        if time_elapsed > self.TIME_THRESHOLD:
            return True
        
        if self.session_count_since_last >= self.SESSION_THRESHOLD:
            return True
        
        return False
    
    def record_session(self) -> None:
        """Yeni session kaydedildi"""
        self.session_count_since_last += 1
    
    def run_consolidation(self) -> None:
        """Consolidation'u çalıştır (background'dan çağrılır)"""
        try:
            result = consolidate_learnings(
                self.db_path,
                self.memory_dir,
                session_limit=10,
                hours_back=24
            )
            
            self.last_consolidation = datetime.now()
            self.session_count_since_last = 0
            
            logger.info(f"Consolidation job completed: {result.get('summary')}")
        
        except Exception as e:
            logger.error(f"Consolidation job failed: {e}")
    
    def start_background_scheduler(self) -> None:
        """APScheduler ile background consolidation'u başlat"""
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            
            scheduler = BackgroundScheduler()
            scheduler.add_job(
                self.check_and_consolidate,
                'interval',
                seconds=self.check_interval,
                id='memory_consolidation'
            )
            scheduler.start()
            self.running = True
            logger.info("✓ Memory consolidation scheduler started")
        
        except ImportError:
            logger.warning("APScheduler not installed, skipping background consolidation")
    
    def check_and_consolidate(self) -> None:
        """Threshold check → consolidation"""
        if self.should_consolidate():
            self.run_consolidation()


# Export
__all__ = [
    'load_recent_sessions',
    'extract_error_patterns',
    'extract_user_preferences',
    'extract_workflow_bottlenecks',
    'consolidate_learnings',
    'ConsolidationScheduler'
]
