from __future__ import annotations

from agents.base import AgentArtifact, AgentContext, BaseAgent
from agents.git_summarizer.formatter import render_summary
from agents.git_summarizer.summarize import build_stats, collect_recent_commits
from scripts.utils import slugify, utc_timestamp


class GitSummarizerAgent(BaseAgent):
    name = 'git_summarizer'
    prompt_file = 'daily_summary.md'
    output_group = 'summaries'

    def collect(self, context: AgentContext) -> dict:
        defaults = context.config.get('automation', {}).get('defaults', {})
        window = context.extra.get('window') or defaults.get('summary', {}).get('daily_window', '1 day ago')
        commits = collect_recent_commits(context.repo_path, window=window)
        return {
            'repository': context.repo_path.name,
            'window': window,
            'commits': commits,
            'stats': build_stats(commits),
        }

    def build_prompt_values(self, data: dict, context: AgentContext) -> dict:
        return data

    def fallback_response(self, data: dict, context: AgentContext) -> str:
        return render_summary(data)

    def build_artifact(self, body: str, data: dict, context: AgentContext) -> AgentArtifact:
        slug = slugify(f"git-summary-{utc_timestamp()}")
        return AgentArtifact(
            title='Daily Git Activity Summary',
            slug=slug,
            body=body,
            output_group=self.output_group,
            metadata={'window': data['window']},
        )
