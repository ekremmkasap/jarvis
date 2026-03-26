from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from scripts.markdown_publish import append_job_summary, persist_output
from scripts.prompt_loader import load_prompt_template, render_prompt
from scripts.utils import get_logger


@dataclass
class AgentContext:
    agent_name: str
    repo_path: Path
    event_name: str
    event_payload: dict[str, Any]
    config: dict[str, Any]
    github: Any = None
    llm: Any = None
    dry_run: bool = True
    publish: bool = False
    output_root: Path = Path('outputs')
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentArtifact:
    title: str
    slug: str
    body: str
    output_group: str = 'reports'
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentExecution:
    prompt: str
    artifact: AgentArtifact
    output_path: Path
    published: list[str] = field(default_factory=list)


class BaseAgent(ABC):
    name = 'base'
    prompt_file = ''
    output_group = 'reports'

    def __init__(self) -> None:
        self.log = get_logger(self.name)

    @abstractmethod
    def collect(self, context: AgentContext) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def build_prompt_values(self, data: dict[str, Any], context: AgentContext) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def fallback_response(self, data: dict[str, Any], context: AgentContext) -> str:
        raise NotImplementedError

    @abstractmethod
    def build_artifact(self, body: str, data: dict[str, Any], context: AgentContext) -> AgentArtifact:
        raise NotImplementedError

    def system_prompt(self, data: dict[str, Any], context: AgentContext) -> str | None:
        return None

    def build_prompt(self, data: dict[str, Any], context: AgentContext) -> str:
        template_path = context.repo_path / 'prompts' / self.prompt_file
        template = load_prompt_template(template_path)
        return render_prompt(template, self.build_prompt_values(data, context))

    def run(self, prompt: str, data: dict[str, Any], context: AgentContext) -> str:
        if context.llm and context.llm.available():
            response = context.llm.generate(prompt=prompt, system=self.system_prompt(data, context))
            if response:
                return response.strip()
        return self.fallback_response(data, context)

    def validate(self, body: str, data: dict[str, Any], context: AgentContext) -> None:
        if not body or not body.strip():
            raise ValueError(f'{self.name} produced an empty response')
        if len(body.strip()) < 40:
            raise ValueError(f'{self.name} response is too short to publish safely')

    def publish(self, artifact: AgentArtifact, data: dict[str, Any], context: AgentContext) -> list[str]:
        return []

    def execute(self, context: AgentContext) -> AgentExecution:
        data = self.collect(context)
        prompt = self.build_prompt(data, context)
        body = self.run(prompt, data, context)
        self.validate(body, data, context)
        artifact = self.build_artifact(body, data, context)
        output_path = persist_output(context.repo_path / context.output_root, artifact.output_group, artifact.slug, artifact.body)
        append_job_summary(f'## {artifact.title}\n\n{artifact.body}')
        published = self.publish(artifact, data, context) if context.publish else []
        return AgentExecution(prompt=prompt, artifact=artifact, output_path=output_path, published=published)
