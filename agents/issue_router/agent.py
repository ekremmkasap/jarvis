from __future__ import annotations

from agents.base import AgentArtifact, AgentContext, BaseAgent
from agents.issue_router.formatter import render_triage
from agents.issue_router.labels import infer_labels, infer_priority
from agents.issue_router.owners import resolve_mention, resolve_owner
from scripts.utils import slugify, utc_timestamp


class IssueRouterAgent(BaseAgent):
    name = 'issue_router'
    prompt_file = 'issue_triage.md'
    output_group = 'reports'

    def collect(self, context: AgentContext) -> dict:
        issue = context.event_payload.get('issue', {})
        number = int(context.extra.get('number') or issue.get('number') or 0)
        if context.github and context.github.enabled and number:
            issue_data = context.github.get_issue(number)
        else:
            issue_data = issue
        labels_config = context.config.get('labels', {})
        owners_config = context.config.get('owners', {})
        title = issue_data.get('title', 'Unknown issue')
        body = issue_data.get('body') or ''
        priority = infer_priority(title, body, labels_config, context.config.get('automation', {}).get('issue_routing', {}).get('default_priority', 'medium'))
        proposed_labels = infer_labels(title, body, labels_config)
        owner = resolve_owner(proposed_labels, owners_config)
        return {
            'repository': context.repo_path.name,
            'number': number,
            'title': title,
            'body': body,
            'author': (issue_data.get('user') or {}).get('login', 'unknown'),
            'labels_config': labels_config,
            'owners_config': owners_config,
            'proposed_labels': proposed_labels,
            'priority': priority,
            'owner': owner,
            'owner_mention': resolve_mention(owner, owners_config),
        }

    def build_prompt_values(self, data: dict, context: AgentContext) -> dict:
        return data

    def fallback_response(self, data: dict, context: AgentContext) -> str:
        return render_triage(data)

    def build_artifact(self, body: str, data: dict, context: AgentContext) -> AgentArtifact:
        slug = slugify(f"issue-triage-{data['number'] or utc_timestamp()}")
        return AgentArtifact(
            title=f"Issue Triage #{data['number']}",
            slug=slug,
            body=body,
            output_group=self.output_group,
            metadata={'number': data['number']},
        )

    def publish(self, artifact: AgentArtifact, data: dict, context: AgentContext) -> list[str]:
        if not (context.github and context.github.enabled and data.get('number')):
            return []
        actions: list[str] = []
        if data.get('proposed_labels'):
            context.github.add_labels(int(data['number']), list(data['proposed_labels']))
            actions.append(f"labels applied to issue #{data['number']}")
        context.github.comment_issue(int(data['number']), artifact.body)
        actions.append(f"commented on issue #{data['number']}")
        return actions
