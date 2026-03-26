from __future__ import annotations

from agents.base import AgentArtifact, AgentContext, BaseAgent
from agents.pr_reviewer.formatter import render_review
from agents.pr_reviewer.parser import summarize_files
from scripts.utils import slugify, utc_timestamp


class PRReviewerAgent(BaseAgent):
    name = 'pr_reviewer'
    prompt_file = 'pr_review.md'
    output_group = 'reports'

    def collect(self, context: AgentContext) -> dict:
        payload = context.event_payload
        pull_request = payload.get('pull_request', {})
        number = int(context.extra.get('number') or pull_request.get('number') or 0)
        if context.github and context.github.enabled and number:
            pr_data = context.github.get_pull_request(number)
            files = context.github.list_pull_request_files(number)
        else:
            pr_data = pull_request
            files = pull_request.get('files', [])
        file_summary = summarize_files(files)
        return {
            'repository': context.repo_path.name,
            'number': number,
            'title': pr_data.get('title', 'Unknown PR'),
            'author': (pr_data.get('user') or {}).get('login', 'unknown'),
            'body': pr_data.get('body') or '',
            'files': file_summary.get('files', []),
            'file_summary': file_summary,
        }

    def build_prompt_values(self, data: dict, context: AgentContext) -> dict:
        return data

    def fallback_response(self, data: dict, context: AgentContext) -> str:
        return render_review(data)

    def build_artifact(self, body: str, data: dict, context: AgentContext) -> AgentArtifact:
        slug = slugify(f"pr-review-{data['number'] or 'draft'}-{utc_timestamp()}")
        return AgentArtifact(
            title=f"PR Review Draft #{data['number']}",
            slug=slug,
            body=body,
            output_group=self.output_group,
            metadata={'number': data['number']},
        )

    def publish(self, artifact: AgentArtifact, data: dict, context: AgentContext) -> list[str]:
        if not (context.github and context.github.enabled and data.get('number')):
            return []
        context.github.comment_issue(int(data['number']), artifact.body)
        return [f"commented on PR #{data['number']}"]
