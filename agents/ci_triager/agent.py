from __future__ import annotations

from agents.base import AgentArtifact, AgentContext, BaseAgent
from agents.ci_triager.formatter import render_report
from agents.ci_triager.heuristics import classify_failure
from agents.ci_triager.log_parser import extract_signal_lines
from scripts.utils import slugify, utc_timestamp


class CITriagerAgent(BaseAgent):
    name = 'ci_triager'
    prompt_file = 'ci_failure.md'
    output_group = 'reports'

    def collect(self, context: AgentContext) -> dict:
        workflow_run = context.event_payload.get('workflow_run', {})
        run_id = int(context.extra.get('number') or workflow_run.get('id') or 0)
        jobs = context.github.list_workflow_run_jobs(run_id) if context.github and context.github.enabled and run_id else []
        logs_excerpt = context.github.download_workflow_run_logs(run_id) if context.github and context.github.enabled and run_id else ''
        signal_lines = extract_signal_lines(logs_excerpt)
        heuristic = classify_failure(logs_excerpt or '\n'.join(signal_lines))
        pull_requests = workflow_run.get('pull_requests') or []
        linked_pr = pull_requests[0].get('number') if pull_requests else 0
        return {
            'repository': context.repo_path.name,
            'run_id': run_id,
            'workflow_name': workflow_run.get('name', 'unknown-workflow'),
            'branch': workflow_run.get('head_branch', 'unknown'),
            'jobs': jobs,
            'logs_excerpt': logs_excerpt[:12000],
            'signal_lines': signal_lines,
            'heuristic': heuristic,
            'linked_pr': linked_pr,
        }

    def build_prompt_values(self, data: dict, context: AgentContext) -> dict:
        return data

    def fallback_response(self, data: dict, context: AgentContext) -> str:
        return render_report(data)

    def build_artifact(self, body: str, data: dict, context: AgentContext) -> AgentArtifact:
        slug = slugify(f"ci-triage-{data['run_id'] or utc_timestamp()}")
        return AgentArtifact(
            title=f"CI Failure Analysis #{data['run_id']}",
            slug=slug,
            body=body,
            output_group=self.output_group,
            metadata={'run_id': data['run_id']},
        )

    def publish(self, artifact: AgentArtifact, data: dict, context: AgentContext) -> list[str]:
        linked_pr = int(data.get('linked_pr') or 0)
        if not (context.github and context.github.enabled and linked_pr):
            return []
        context.github.comment_issue(linked_pr, artifact.body)
        return [f"commented on linked PR #{linked_pr}"]
