"""
JARVIS Night Runner - Autonomous Development System
Sen uyurken Claude Code ile birlikte JARVIS'i geliştiriyor
"""
import json
import os
import sys
import time
import traceback
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import asyncio

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add parent to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(current_dir, '..', '..'))

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False
    print("[NightRunner] Warning: anthropic not installed")

try:
    from server.agents.self_learning_orchestrator import SelfLearningOrchestrator
    HAS_AGENTS = True
except ImportError:
    HAS_AGENTS = False

try:
    from ollama_agent import OllamaAgent
    HAS_OLLAMA = True
except ImportError:
    HAS_OLLAMA = False

try:
    from github_trending_scraper import GitHubTrendingScraper
    HAS_GITHUB_SCRAPER = True
except ImportError:
    HAS_GITHUB_SCRAPER = False

try:
    from github_repo_analyzer import GitHubRepoAnalyzer
    HAS_REPO_ANALYZER = True
except ImportError:
    HAS_REPO_ANALYZER = False

try:
    from server.skills.approval_skill import add_approval_request, process_pending_auto_approvals, schedule_claude_resume
    HAS_APPROVAL_SKILL = True
except ImportError:
    HAS_APPROVAL_SKILL = False

try:
    from collaboration_bridge import get_bridge, TaskContract, HandoffContract
    HAS_COLLABORATION_BRIDGE = True
except ImportError:
    HAS_COLLABORATION_BRIDGE = False


class NightRunner:
    """
    Gece çalışan otonom geliştirme sistemi

    Features:
    - Claude API ile kod analizi
    - Self-learning system
    - Staging workspace
    - Morning reports
    - Safe autonomy
    """

    def __init__(self, config_path: str = "server/config/night_config.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()

        # Paths
        self.root_dir = Path("c:/Users/sergen/Desktop/jarvis-mission-control")
        self.staging_dir = self.root_dir / "server/agent_workspace/staging"
        self.logs_dir = self.root_dir / "server/logs/night_runs"
        self.reports_dir = self.root_dir / "server/logs/night_reports"
        self.visual_state_path = self.root_dir / "server/logs/agent_os_status.json"
        self.visual_events_path = self.root_dir / "server/logs/agent_os_events.jsonl"

        # Create directories
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        # Claude API
        self.anthropic_client = None
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        if anthropic_key and HAS_ANTHROPIC:
            self.anthropic_client = anthropic.Anthropic(api_key=anthropic_key)
            print("[NightRunner] Claude API initialized")

        # Self-learning
        self.self_learning = None
        if HAS_AGENTS:
            try:
                self.self_learning = SelfLearningOrchestrator()
                print("[NightRunner] Self-learning initialized")
            except Exception as e:
                print(f"[NightRunner] Self-learning init failed: {e}")

        # Ollama (local LLM)
        self.ollama = None
        if HAS_OLLAMA:
            try:
                self.ollama = OllamaAgent()
                print("[NightRunner] Ollama initialized")
            except Exception as e:
                print(f"[NightRunner] Ollama init failed: {e}")

        # GitHub Trending
        self.github_scraper = None
        if HAS_GITHUB_SCRAPER:
            try:
                self.github_scraper = GitHubTrendingScraper()
                print("[NightRunner] GitHub scraper initialized")
            except Exception as e:
                print(f"[NightRunner] GitHub scraper init failed: {e}")

        self.repo_analyzer = None
        if HAS_REPO_ANALYZER:
            try:
                self.repo_analyzer = GitHubRepoAnalyzer(output_dir=str(self.staging_dir))
                print("[NightRunner] Repo analyzer initialized")
            except Exception as e:
                print(f"[NightRunner] Repo analyzer init failed: {e}")

        # Collaboration Bridge (Claude <-> JARVIS)
        self.bridge = None
        if HAS_COLLABORATION_BRIDGE:
            try:
                self.bridge = get_bridge()
                print("[NightRunner] Collaboration bridge initialized")
                print(f"[Bridge] Stats: {self.bridge.get_bridge_stats()}")
            except Exception as e:
                print(f"[NightRunner] Bridge init failed: {e}")

        # Stats
        self.run_stats = {
            "start_time": None,
            "end_time": None,
            "jobs_completed": 0,
            "jobs_failed": 0,
            "files_analyzed": 0,
            "files_modified": 0,
            "errors": []
        }

        self.visual_state = {
            "mode": "night_runner",
            "status": "idle",
            "current_job": None,
            "updated_at": datetime.now().isoformat(),
            "agents": {
                "jarvis": "idle",
                "claude": "idle",
                "ollama": "idle",
                "research": "idle",
                "guard": "idle"
            },
            "jobs": [],
            "stats": {}
        }
        self._write_visual_state()

        print("[NightRunner] Initialized!")

    def _load_config(self) -> Dict:
        """Load configuration"""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)

        # Default config
        return {
            "enabled": True,
            "schedule": {
                "run_at_hour": 2,
                "run_duration_max_hours": 4
            },
            "safety": {
                "staging_only": True,
                "max_files_per_run": 20,
                "safe_directories": [
                    "server/agents",
                    "server/agent_workspace/staging",
                    "server/skills",
                    "docs"
                ],
                "forbidden_files": [
                    ".env",
                    "credentials.json",
                    "*.key",
                    "*.pem"
                ],
                "forbidden_operations": [
                    "delete_files",
                    "system_shutdown",
                    "network_requests_external"
                ]
            },
            "tasks": {
                "enabled_tasks": [
                    "analyze_logs",
                    "scan_todos",
                    "research_topics",
                    "generate_docs",
                    "propose_improvements",
                    "self_learning"
                ]
            }
        }

    # ============================================
    # MAIN NIGHT LOOP
    # ============================================

    def run_night_cycle(self):
        """
        Ana gece döngüsü
        """
        print("\n" + "="*60)
        print("🌙 NIGHT RUNNER STARTED")
        print("="*60)

        self.run_stats["start_time"] = datetime.now().isoformat()
        self._set_agent_state("jarvis", "running")
        self._record_visual_event("night_runner_started", "Night automation cycle started")

        try:
            # Load job queue
            jobs = self._load_job_queue()
            print(f"\n[NightRunner] Loaded {len(jobs)} jobs")

            # Execute jobs
            for job in jobs:
                if not self._is_safe_to_continue():
                    print("[NightRunner] Safety limit reached, stopping")
                    break

                self._execute_job(job)

            # Self-learning tasks
            if self.config["tasks"]["enabled_tasks"].count("self_learning") > 0:
                self._run_self_learning_tasks()

            # Generate morning report
            self._generate_morning_report()

            # Process collaboration bridge handoffs
            if self.bridge:
                self._process_bridge_handoffs()

            # Approval skill integration
            if HAS_APPROVAL_SKILL:
                process_pending_auto_approvals()
                schedule_claude_resume(
                    "09:02",
                    "Claude limiti yenilenince collaboration protocol, architecture ve backlog islerinden devam et.",
                    "Claude collaboration protocol",
                )
                add_approval_request(
                    "Claude sabah devam paketi",
                    "09:02 sonrasinda Claude exchange alanini kontrol et ve uretilen resume paketinden devam et.",
                    source="night_runner",
                    risk="low",
                )

            # Create handoff package for Claude
            if self.bridge:
                self._create_claude_handoff_package()

        except KeyboardInterrupt:
            print("\n[NightRunner] Interrupted by user")
        except Exception as e:
            print(f"\n[NightRunner] Fatal error: {e}")
            traceback.print_exc()
            self.run_stats["errors"].append({
                "type": "fatal",
                "error": str(e),
                "traceback": traceback.format_exc()
            })
        finally:
            self.run_stats["end_time"] = datetime.now().isoformat()
            self._set_agent_state("jarvis", "done")
            self._save_run_log()

            print("\n" + "="*60)
            print("🌅 NIGHT RUNNER COMPLETED")
            print(f"Jobs completed: {self.run_stats['jobs_completed']}")
            print(f"Jobs failed: {self.run_stats['jobs_failed']}")
            print(f"Files analyzed: {self.run_stats['files_analyzed']}")
            print(f"Files modified: {self.run_stats['files_modified']}")
            print("="*60)

    # ============================================
    # JOB EXECUTION
    # ============================================

    def _load_job_queue(self) -> List[Dict]:
        """Job queue yükle"""
        queue_path = self.root_dir / "server/config/night_jobs.json"

        if queue_path.exists():
            with open(queue_path, 'r', encoding='utf-8') as f:
                jobs = json.load(f).get("jobs", [])
                return [job for job in jobs if job.get("enabled", True)]

        # Default jobs
        return [
            {
                "id": "analyze_recent_logs",
                "type": "analyze_logs",
                "priority": 1,
                "params": {"days_back": 1}
            },
            {
                "id": "scan_todos",
                "type": "scan_todos",
                "priority": 2,
                "params": {"auto_categorize": True}
            },
            {
                "id": "research_new_topics",
                "type": "research",
                "priority": 3,
                "params": {
                    "topics": ["Python async patterns", "Agent architecture best practices"]
                }
            }
        ]

    def _execute_job(self, job: Dict):
        """Tek bir job çalıştır"""
        job_id = job.get("id", "unknown")
        job_type = job.get("type", "unknown")

        print(f"\n[Job] Starting: {job_id} (type: {job_type})")
        self.visual_state["current_job"] = {"id": job_id, "type": job_type}
        self._record_visual_event("job_started", f"{job_id} started", {"type": job_type})
        self._set_agent_state("research", "running" if job_type in ("research", "github_trending", "github_repo_analysis") else self.visual_state["agents"]["research"])
        self._set_agent_state("ollama", "running" if job_type == "ollama_analysis" else self.visual_state["agents"]["ollama"])
        self._set_agent_state("claude", "running" if job_type == "claude_analysis" else self.visual_state["agents"]["claude"])

        try:
            if job_type == "analyze_logs":
                self._job_analyze_logs(job.get("params", {}))

            elif job_type == "scan_todos":
                self._job_scan_todos(job.get("params", {}))

            elif job_type == "research":
                self._job_research(job.get("params", {}))

            elif job_type == "generate_docs":
                self._job_generate_docs(job.get("params", {}))

            elif job_type == "claude_analysis":
                self._job_claude_analysis(job.get("params", {}))

            elif job_type == "ollama_analysis":
                self._job_ollama_analysis(job.get("params", {}))

            elif job_type == "github_trending":
                self._job_github_trending(job.get("params", {}))

            elif job_type == "github_repo_analysis":
                self._job_github_repo_analysis(job.get("params", {}))

            elif job_type == "health_check":
                self._job_health_check(job.get("params", {}))

            else:
                print(f"[Job] Unknown job type: {job_type}")
                self.run_stats["jobs_failed"] += 1
                return

            self.run_stats["jobs_completed"] += 1
            self.visual_state["jobs"].append({"id": job_id, "type": job_type, "status": "done"})
            self._record_visual_event("job_completed", f"{job_id} completed", {"type": job_type})
            print(f"[Job] ✓ Completed: {job_id}")

        except Exception as e:
            print(f"[Job] ✗ Failed: {job_id} - {e}")
            self.run_stats["jobs_failed"] += 1
            self.run_stats["errors"].append({
                "job_id": job_id,
                "error": str(e),
                "traceback": traceback.format_exc()
            })
            self.visual_state["jobs"].append({"id": job_id, "type": job_type, "status": "failed"})
            self._record_visual_event("job_failed", f"{job_id} failed", {"type": job_type, "error": str(e)})
        finally:
            for agent_name in ("research", "ollama", "claude"):
                if self.visual_state["agents"][agent_name] == "running":
                    self._set_agent_state(agent_name, "idle")
            self.visual_state["current_job"] = None
            self._write_visual_state()

    # ============================================
    # JOB IMPLEMENTATIONS
    # ============================================

    def _job_analyze_logs(self, params: Dict):
        """Log analizi"""
        days_back = params.get("days_back", 1)

        log_files = list(self.logs_dir.glob("*.log"))
        log_files += list((self.root_dir / "server/logs").glob("*.jsonl"))

        analysis = {
            "total_logs": len(log_files),
            "errors_found": [],
            "warnings_found": [],
            "insights": []
        }

        for log_file in log_files[:10]:  # Limit
            try:
                content = log_file.read_text(encoding='utf-8', errors='ignore')

                # Simple pattern matching
                if "ERROR" in content or "Exception" in content:
                    analysis["errors_found"].append(str(log_file))

                if "WARNING" in content or "WARN" in content:
                    analysis["warnings_found"].append(str(log_file))

                self.run_stats["files_analyzed"] += 1

            except Exception as e:
                print(f"[Job] Could not read log: {log_file} - {e}")

        # Save analysis
        output_path = self.staging_dir / f"log_analysis_{int(time.time())}.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)

        if HAS_APPROVAL_SKILL:
            add_approval_request(
                "Night log analysis artifact",
                f"Gece log analizi staging cikti olustu: {output_path.name}",
                source="night_runner",
                risk="low",
            )

        print(f"[Job] Log analysis saved: {output_path}")

    def _job_scan_todos(self, params: Dict):
        """TODO taraması"""
        todo_items = []

        # Scan Python files
        for py_file in self.root_dir.glob("**/*.py"):
            if ".venv" in str(py_file) or "node_modules" in str(py_file):
                continue

            try:
                content = py_file.read_text(encoding='utf-8', errors='ignore')
                lines = content.split('\n')

                for i, line in enumerate(lines):
                    if "TODO" in line or "FIXME" in line or "HACK" in line:
                        todo_items.append({
                            "file": str(py_file.relative_to(self.root_dir)),
                            "line": i + 1,
                            "text": line.strip()
                        })

                self.run_stats["files_analyzed"] += 1

            except Exception as e:
                continue

        # Save
        output_path = self.staging_dir / f"todos_{int(time.time())}.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({"total": len(todo_items), "items": todo_items}, f, indent=2, ensure_ascii=False)

        if HAS_APPROVAL_SKILL:
            add_approval_request(
                "Night TODO scan artifact",
                f"TODO/FIXME tarama cikti olustu: {output_path.name}",
                source="night_runner",
                risk="low",
            )

        print(f"[Job] Found {len(todo_items)} TODOs, saved to {output_path}")

    def _job_research(self, params: Dict):
        """Research topics using self-learning"""
        if not self.self_learning:
            print("[Job] Self-learning not available")
            return

        topics = params.get("topics", [])

        for topic in topics:
            print(f"[Job] Researching: {topic}")

            try:
                result = self.self_learning.learn_from_query(topic)

                if result.get("learned"):
                    print(f"[Job] ✓ Learned about: {topic}")
                else:
                    print(f"[Job] ✗ Could not learn: {topic}")

            except Exception as e:
                print(f"[Job] Research failed for {topic}: {e}")

    def _job_generate_docs(self, params: Dict):
        """Generate documentation"""
        # Use Claude API to generate docs
        if not self.anthropic_client:
            print("[Job] Claude API not available")
            return

        target_files = params.get("files", [])

        for file_path in target_files:
            full_path = self.root_dir / file_path

            if not full_path.exists():
                continue

            try:
                code = full_path.read_text(encoding='utf-8')

                # Call Claude API
                response = self.anthropic_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=2000,
                    messages=[{
                        "role": "user",
                        "content": f"Generate comprehensive documentation for this code:\n\n{code[:10000]}"
                    }]
                )

                doc_content = response.content[0].text

                # Save to staging
                doc_path = self.staging_dir / f"{full_path.stem}_docs.md"
                doc_path.write_text(doc_content, encoding='utf-8')

                if HAS_APPROVAL_SKILL:
                    add_approval_request(
                        "Generated documentation artifact",
                        f"Dokumantasyon staging cikti olustu: {doc_path.name}",
                        source="claude",
                        risk="medium",
                    )

                print(f"[Job] Generated docs: {doc_path}")
                self.run_stats["files_modified"] += 1

            except Exception as e:
                print(f"[Job] Doc generation failed for {file_path}: {e}")

    def _job_claude_analysis(self, params: Dict):
        """Claude ile kod analizi"""
        if not self.anthropic_client:
            print("[Job] Claude API not available")
            return

        target_dir = params.get("directory", "server/agents")
        analysis_type = params.get("type", "improvements")

        # Collect code
        code_files = list((self.root_dir / target_dir).glob("**/*.py"))[:5]  # Limit

        combined_code = ""
        for code_file in code_files:
            try:
                content = code_file.read_text(encoding='utf-8', errors='ignore')
                combined_code += f"\n\n# {code_file.name}\n{content[:5000]}\n"
            except:
                continue

        # Claude analysis
        prompt = f"""Analyze this code and provide:
1. Code quality assessment
2. Potential bugs or issues
3. Performance improvements
4. Architecture suggestions
5. Security concerns

Code:
{combined_code[:15000]}
"""

        try:
            response = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )

            analysis = response.content[0].text

            # Save
            output_path = self.staging_dir / f"claude_analysis_{int(time.time())}.md"
            output_path.write_text(analysis, encoding='utf-8')

            if HAS_APPROVAL_SKILL:
                add_approval_request(
                    "Claude analysis artifact",
                    f"Claude analiz staging cikti olustu: {output_path.name}",
                    source="claude",
                    risk="medium",
                )

            print(f"[Job] Claude analysis saved: {output_path}")

        except Exception as e:
            print(f"[Job] Claude analysis failed: {e}")

    def _job_ollama_analysis(self, params: Dict):
        """Ollama ile kod analizi"""
        if not self.ollama:
            print("[Job] Ollama not available")
            return

        target_dir = params.get("directory", "server/agents")
        analysis_type = params.get("analysis_type", "quality")

        # Collect code
        code_files = list((self.root_dir / target_dir).glob("**/*.py"))[:3]  # Limit

        for code_file in code_files:
            try:
                code = code_file.read_text(encoding='utf-8', errors='ignore')

                # Ollama analysis
                print(f"[Job] Analyzing {code_file.name} with Ollama...")
                analysis = self.ollama.analyze_code(code[:8000], analysis_type)

                # Save
                output_path = self.staging_dir / f"ollama_{code_file.stem}_{int(time.time())}.md"
                output_path.write_text(f"# {code_file.name} Analysis\n\n{analysis}", encoding='utf-8')

                if HAS_APPROVAL_SKILL:
                    add_approval_request(
                        f"Ollama analysis {code_file.name}",
                        f"Ollama analiz staging cikti olustu: {output_path.name}",
                        source="ollama",
                        risk="low",
                    )

                print(f"[Job] Saved: {output_path}")
                self.run_stats["files_analyzed"] += 1
                self.run_stats["files_modified"] += 1

                time.sleep(1)  # Rate limiting

            except Exception as e:
                print(f"[Job] Ollama analysis failed for {code_file}: {e}")

    def _job_github_trending(self, params: Dict):
        """GitHub trending scrape"""
        if not self.github_scraper:
            print("[Job] GitHub scraper not available")
            return

        try:
            # Get daily digest
            digest = self.github_scraper.get_daily_digest()

            # Ingest into knowledge base if available
            if self.self_learning:
                for repo in digest.get("python_repos", [])[:3]:
                    text = f"Trending Python Repo: {repo['name']}\n{repo['description']}\nStars: {repo['total_stars']}"
                    self.self_learning.knowledge_manager.ingest_text(
                        text=text,
                        source=repo['url'],
                        metadata={"type": "github_trending", "language": "python"}
                    )

            print(f"[Job] GitHub trending digest created")

        except Exception as e:
            print(f"[Job] GitHub trending failed: {e}")

    def _job_github_repo_analysis(self, params: Dict):
        """Analyze curated GitHub repositories and extract patterns"""
        if not self.repo_analyzer:
            print("[Job] Repo analyzer not available")
            return

        source_file = params.get("source_file", "server/config/repo_sources.json")
        max_repos = params.get("max_repos", 10)
        source_path = self.root_dir / source_file
        if not source_path.exists():
            print(f"[Job] Repo source file not found: {source_path}")
            return

        source_payload = json.loads(source_path.read_text(encoding="utf-8"))
        repo_urls = source_payload.get("repos", [])[:max_repos]
        if not repo_urls:
            print("[Job] No curated repos to analyze")
            return

        report = self.repo_analyzer.analyze_batch(repo_urls)
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_repos": report.get("session", {}).get("total_repos", 0),
            "successful": report.get("session", {}).get("successful", 0),
            "top_languages": report.get("top_languages", {}),
            "top_topics": report.get("top_topics", {}),
            "pattern_types": sorted(report.get("patterns_summary", {}).keys()),
        }
        output_path = self.staging_dir / f"repo_patterns_{int(time.time())}.json"
        with open(output_path, "w", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=2, ensure_ascii=False)
        self.run_stats["files_analyzed"] += report.get("session", {}).get("successful", 0)
        self.run_stats["files_modified"] += 1
        if HAS_APPROVAL_SKILL:
            add_approval_request(
                "Curated repo pattern digest",
                f"Repo pattern ozeti staging cikti olustu: {output_path.name}",
                source="night_runner",
                risk="medium",
            )
        print(f"[Job] Curated repo analysis saved: {output_path}")

    def _job_health_check(self, params: Dict):
        """System health check"""
        components = params.get("components", [])

        health_report = {
            "timestamp": datetime.now().isoformat(),
            "components": {}
        }

        # Ollama check
        if "ollama" in components and self.ollama:
            health_report["components"]["ollama"] = self.ollama.health_check()

        # Self-learning check
        if "vector_db" in components and self.self_learning:
            health_report["components"]["vector_db"] = self.self_learning.knowledge_manager.get_stats()

        # Web crawler check
        if "web_crawler" in components and self.self_learning:
            health_report["components"]["web_crawler"] = {"status": "available"}

        # Save health report
        output_path = self.staging_dir / f"health_check_{int(time.time())}.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(health_report, f, indent=2, ensure_ascii=False)

        if HAS_APPROVAL_SKILL:
            add_approval_request(
                "Night health check artifact",
                f"Saglik kontrol staging cikti olustu: {output_path.name}",
                source="night_runner",
                risk="low",
            )

        print(f"[Job] Health check saved: {output_path}")

    # ============================================
    # SELF-LEARNING TASKS
    # ============================================

    def _run_self_learning_tasks(self):
        """Gece self-learning görevleri"""
        if not self.self_learning:
            return

        print("\n[SelfLearning] Running night learning tasks...")

        # Get stats
        stats = self.self_learning.get_system_stats()

        # Learn about common errors from logs
        common_topics = [
            "Python async programming best practices",
            "Windows service development",
            "Voice assistant architecture"
        ]

        for topic in common_topics[:2]:  # Limit for night run
            try:
                self.self_learning.learn_from_query(topic)
                time.sleep(2)  # Rate limiting
            except:
                pass

    # ============================================
    # SAFETY & VALIDATION
    # ============================================

    def _is_safe_to_continue(self) -> bool:
        """Güvenlik kontrolü"""
        max_files = self.config["safety"]["max_files_per_run"]

        if self.run_stats["files_modified"] >= max_files:
            return False

        # Time limit
        if self.run_stats["start_time"]:
            start = datetime.fromisoformat(self.run_stats["start_time"])
            max_duration = timedelta(hours=self.config["schedule"]["run_duration_max_hours"])

            if datetime.now() - start > max_duration:
                return False

        return True

    # ============================================
    # REPORTING
    # ============================================

    def _generate_morning_report(self):
        """Sabah raporu oluştur"""
        report_path = self.reports_dir / f"report_{datetime.now().strftime('%Y%m%d')}.md"

        report = f"""# 🌅 JARVIS Night Run Report
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Summary
- **Jobs Completed:** {self.run_stats['jobs_completed']}
- **Jobs Failed:** {self.run_stats['jobs_failed']}
- **Files Analyzed:** {self.run_stats['files_analyzed']}
- **Files Modified:** {self.run_stats['files_modified']}

## Duration
- **Start:** {self.run_stats['start_time']}
- **End:** {self.run_stats['end_time']}

## Errors
"""

        if self.run_stats['errors']:
            for err in self.run_stats['errors']:
                report += f"\n### Error: {err.get('job_id', 'unknown')}\n"
                report += f"```\n{err.get('error', 'N/A')}\n```\n"
        else:
            report += "\n✓ No errors\n"

        report += f"""
## Staging Files
Check `{self.staging_dir}` for generated files.

## Agent States
- Jarvis: {self.visual_state['agents']['jarvis']}
- Claude: {self.visual_state['agents']['claude']}
- Ollama: {self.visual_state['agents']['ollama']}
- Research: {self.visual_state['agents']['research']}
- Guard: {self.visual_state['agents']['guard']}

## Next Steps
Review staging files and approve changes for production.

---
*Generated by JARVIS Night Runner*
"""

        report_path.write_text(report, encoding='utf-8')
        print(f"\n[Report] Morning report saved: {report_path}")
        self._record_visual_event("morning_report", "Morning report generated", {"report": str(report_path)})

    def _save_run_log(self):
        """Run log kaydet"""
        log_path = self.logs_dir / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(self.run_stats, f, indent=2, ensure_ascii=False)
        self.visual_state["status"] = "idle"
        self.visual_state["stats"] = self.run_stats
        self._write_visual_state()

    def _set_agent_state(self, agent: str, state: str):
        self.visual_state["agents"][agent] = state
        self.visual_state["updated_at"] = datetime.now().isoformat()
        self.visual_state["status"] = state if agent == "jarvis" else self.visual_state.get("status", "idle")
        self._write_visual_state()

    def _record_visual_event(self, event_type: str, message: str, data: Optional[Dict] = None):
        event = {
            "time": datetime.now().isoformat(),
            "type": event_type,
            "message": message,
            "data": data or {}
        }
        self.visual_events_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.visual_events_path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    def _write_visual_state(self):
        self.visual_state_path.parent.mkdir(parents=True, exist_ok=True)
        self.visual_state["updated_at"] = datetime.now().isoformat()
        with open(self.visual_state_path, "w", encoding="utf-8") as handle:
            json.dump(self.visual_state, handle, indent=2, ensure_ascii=False)

    # ============================================
    # COLLABORATION BRIDGE METHODS
    # ============================================

    def _process_bridge_handoffs(self):
        """Claude'dan gelen pending handoff'lari isle"""
        if not self.bridge:
            return

        print("\n[Bridge] Processing pending handoffs...")
        pending = self.bridge.get_pending_handoffs(for_agent="jarvis")
        print(f"[Bridge] Found {len(pending)} pending handoffs")

        for handoff in pending:
            try:
                print(f"[Bridge] Processing handoff {handoff.handoff_id} ({handoff.handoff_type})")

                # Handoff type'a gore isle
                if handoff.handoff_type == "analysis":
                    self._handle_analysis_handoff(handoff)
                elif handoff.handoff_type == "recommendation":
                    self._handle_recommendation_handoff(handoff)

                # Handoff'i kabul et
                self.bridge.accept_handoff(handoff.handoff_id, result={"status": "processed"})

            except Exception as e:
                print(f"[Bridge] Handoff processing failed: {e}")
                self.bridge.reject_handoff(handoff.handoff_id, reason=str(e))

    def _handle_analysis_handoff(self, handoff):
        """Claude'un analiz sonuclarini isle"""
        content = handoff.content
        patterns = content.get("patterns", [])

        # Staging'e kaydet
        output_path = self.staging_dir / f"claude_analysis_{handoff.handoff_id}.json"
        output_path.write_text(
            json.dumps(content, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        if HAS_APPROVAL_SKILL:
            add_approval_request(
                f"Claude analysis: {handoff.task_id}",
                f"Claude tarafindan analiz yapildi. Patterns: {', '.join(patterns[:3])}",
                source="collaboration_bridge",
                risk="low"
            )

    def _handle_recommendation_handoff(self, handoff):
        """Claude'un onerilerini isle"""
        content = handoff.content

        # Staging'e kaydet
        output_path = self.staging_dir / f"claude_recommendation_{handoff.handoff_id}.json"
        output_path.write_text(
            json.dumps(content, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        # High confidence oneriyi approval'a gonder
        if handoff.confidence >= 0.8 and not handoff.requires_human_review:
            if HAS_APPROVAL_SKILL:
                add_approval_request(
                    f"Claude recommendation",
                    f"Confidence: {handoff.confidence}. Staging'de hazir.",
                    source="collaboration_bridge",
                    risk="medium"
                )

    def _create_claude_handoff_package(self):
        """Gece artifact'lerini Claude icin paketle"""
        if not self.bridge:
            return

        print("\n[Bridge] Creating handoff package for Claude...")

        # Gece boyunca uretilen artifact'leri topla
        artifacts = list(self.staging_dir.glob("*.json"))
        print(f"[Bridge] Found {len(artifacts)} artifacts in staging")

        if not artifacts:
            print("[Bridge] No artifacts to hand off")
            return

        # Handoff package olustur
        package = {
            "handoff_id": str(uuid.uuid4())[:8],
            "from_agent": "jarvis",
            "to_agent": "claude",
            "created_at": datetime.now().isoformat(),
            "artifact_count": len(artifacts),
            "summary": {
                "total_artifacts": len(artifacts),
                "night_run_stats": self.run_stats
            }
        }

        # Package'i Claude'un incoming zone'una yaz
        output_path = self.bridge.claude_incoming / f"night_package_{package['handoff_id']}.json"
        output_path.write_text(
            json.dumps(package, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        print(f"[Bridge] Handoff package created: {output_path.name}")

        # Task olustur
        task = self.bridge.create_task(
            title="Review night run artifacts",
            goal="Gece boyunca uretilen artifact'leri incele ve backlog olustur",
            owner="claude",
            source="night_runner",
            priority=2,
            risk_level="low",
            tags=["night_run", "review", "artifacts"]
        )

        print(f"[Bridge] Task created for Claude: {task.task_id}")


# ============================================
# CLI
# ============================================
if __name__ == "__main__":
    import sys

    runner = NightRunner()

    if len(sys.argv) > 1 and sys.argv[1] == "run":
        runner.run_night_cycle()
    else:
        print("Usage: python night_runner.py run")
        print("\nNight Runner is ready. Use Windows Task Scheduler to run this at night.")
