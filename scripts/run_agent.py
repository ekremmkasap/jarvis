from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.base import AgentContext
from agents.registry import get_agent
from scripts.github_client import GitHubClient
from scripts.llm_client import build_llm_client
from scripts.utils import load_json, load_yaml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run a development automation agent')
    parser.add_argument('--agent', required=True, help='Agent name registered in agents/registry.py')
    parser.add_argument('--event-path', default='', help='Path to GitHub event payload JSON')
    parser.add_argument('--publish', action='store_true', help='Publish results back to GitHub')
    parser.add_argument('--output-root', default='outputs', help='Relative output directory')
    parser.add_argument('--window', default='', help='Time window override for summary agents')
    parser.add_argument('--number', type=int, default=0, help='PR or issue number override')
    parser.add_argument('--set', action='append', default=[], metavar='KEY=VALUE', help='Extra context values')
    return parser.parse_args()


def parse_extra(values: list[str]) -> dict[str, Any]:
    extra: dict[str, Any] = {}
    for item in values:
        if '=' not in item:
            continue
        key, value = item.split('=', 1)
        extra[key.strip()] = value.strip()
    return extra


def load_payload(event_path: str) -> dict[str, Any]:
    if event_path:
        return load_json(event_path)
    default_path = Path.cwd() / '.github-event.json'
    if default_path.exists():
        return load_json(default_path)
    return {}


def load_config() -> dict[str, Any]:
    return {
        'automation': load_yaml(ROOT / 'config' / 'automation-config.yml'),
        'labels': load_yaml(ROOT / 'config' / 'labels.yml'),
        'owners': load_yaml(ROOT / 'config' / 'owners.yml'),
        'repositories': load_yaml(ROOT / 'config' / 'repositories.yml'),
    }


def main() -> int:
    args = parse_args()
    config = load_config()
    payload = load_payload(args.event_path)
    github = GitHubClient.from_env()
    llm = build_llm_client(config.get('automation', {}).get('defaults', {}).get('llm', {}))
    extra = parse_extra(args.set)
    if args.window:
        extra['window'] = args.window
    if args.number:
        extra['number'] = args.number

    context = AgentContext(
        agent_name=args.agent,
        repo_path=ROOT,
        event_name=payload.get('action') or 'manual',
        event_payload=payload,
        config=config,
        github=github,
        llm=llm,
        dry_run=not args.publish,
        publish=args.publish,
        output_root=Path(args.output_root),
        extra=extra,
    )

    agent = get_agent(args.agent)
    result = agent.execute(context)
    print(f'agent={args.agent}')
    print(f'output={result.output_path}')
    for item in result.published:
        print(f'published={item}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
