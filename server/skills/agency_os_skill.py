from __future__ import annotations

"""
Agency OS skill.

This module packages an Agency OS style operating model into deterministic,
production-ready Python structures so bridge commands can expose the
architecture without depending on external APIs.

Source notes used for the model:
- Public Digital Academy product pages describing AI agency, customer
  acquisition, content automation, and 24/7 operating systems.
- Internal repo notes in server/knowledge/agentclaw_mimari.md and
  server/knowledge/agentclaw_ajans.md describing CLOSE, memory, MCP, and
  multi-agent workflow patterns.
"""

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class AgencyLayer:
    name: str
    purpose: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    components: tuple[str, ...]


@dataclass(frozen=True)
class AgencyWorkflow:
    name: str
    trigger: str
    steps: tuple[str, ...]
    outcomes: tuple[str, ...]


@dataclass(frozen=True)
class AgencyBlueprint:
    name: str
    thesis: str
    close_framework: tuple[str, ...]
    layers: tuple[AgencyLayer, ...]
    workflows: tuple[AgencyWorkflow, ...]
    guardrails: tuple[str, ...]


def _build_blueprint() -> AgencyBlueprint:
    return AgencyBlueprint(
        name="Agency OS",
        thesis=(
            "Agency OS turns a small team into a 24/7 operating system by"
            " separating intake, memory, orchestration, specialist execution,"
            " and governance."
        ),
        close_framework=(
            "Connect: connect channels, CRM, files, and auth.",
            "Listen: capture requests, signals, and customer intent.",
            "Archive: persist memory, assets, decisions, and history.",
            "Wire: connect internal cells with external tools and delivery flows.",
            "Sense: monitor health, trigger follow-ups, and act proactively.",
        ),
        layers=(
            AgencyLayer(
                name="Intake Hub",
                purpose="Collect every inbound demand in one place.",
                inputs=(
                    "telegram messages",
                    "forms and landing pages",
                    "email and DMs",
                    "manual operator tasks",
                ),
                outputs=(
                    "normalized request",
                    "customer record",
                    "priority score",
                ),
                components=(
                    "channel adapters",
                    "lead capture forms",
                    "conversation parser",
                    "request normalizer",
                ),
            ),
            AgencyLayer(
                name="Memory Layer",
                purpose="Remember customers, offers, assets, and decisions.",
                inputs=(
                    "customer profile updates",
                    "meeting notes",
                    "offer revisions",
                    "campaign outputs",
                ),
                outputs=(
                    "customer context",
                    "project state",
                    "proof library",
                    "playbook memory",
                ),
                components=(
                    "sqlite or postgres memory",
                    "offer registry",
                    "asset library",
                    "decision log",
                ),
            ),
            AgencyLayer(
                name="Orchestration Layer",
                purpose="Route the right work to the right specialist cell.",
                inputs=(
                    "normalized request",
                    "memory context",
                    "business priority",
                ),
                outputs=(
                    "assigned workflow",
                    "task bundle",
                    "approval checkpoint",
                ),
                components=(
                    "supervisor agent",
                    "task planner",
                    "approval gate",
                    "scheduler and heartbeat",
                ),
            ),
            AgencyLayer(
                name="Specialist Cells",
                purpose="Break the agency into reusable operating units.",
                inputs=(
                    "task bundle",
                    "customer context",
                    "offer context",
                ),
                outputs=(
                    "research findings",
                    "product package",
                    "sales assets",
                    "delivery assets",
                ),
                components=(
                    "research cell",
                    "customer cell",
                    "product cell",
                    "sales cell",
                    "content and delivery cell",
                ),
            ),
            AgencyLayer(
                name="Execution Layer",
                purpose="Ship assets, follow-ups, and customer actions.",
                inputs=(
                    "approved workflow",
                    "campaign assets",
                    "proposal drafts",
                    "delivery tasks",
                ),
                outputs=(
                    "sent outreach",
                    "published assets",
                    "active projects",
                    "status updates",
                ),
                components=(
                    "CRM updater",
                    "proposal sender",
                    "content publisher",
                    "client delivery board",
                ),
            ),
            AgencyLayer(
                name="Governance Layer",
                purpose="Protect quality, security, cost, and accountability.",
                inputs=(
                    "task events",
                    "cost usage",
                    "approval history",
                    "quality checks",
                ),
                outputs=(
                    "audit trail",
                    "exception alerts",
                    "health score",
                    "recovery actions",
                ),
                components=(
                    "policy checks",
                    "approval logs",
                    "security review",
                    "recovery and watchdog",
                ),
            ),
        ),
        workflows=(
            AgencyWorkflow(
                name="Lead To Proposal",
                trigger="New lead arrives from channel or campaign.",
                steps=(
                    "capture lead and enrich customer context",
                    "qualify pain, urgency, and budget",
                    "shape the offer around the customer problem",
                    "generate proposal, proof, and call-to-action",
                    "schedule follow-up and next action",
                ),
                outcomes=("qualified lead", "proposal package", "next meeting"),
            ),
            AgencyWorkflow(
                name="Customer To Product",
                trigger="Repeated customer pain or a new niche opportunity appears.",
                steps=(
                    "group customers by pain and buying trigger",
                    "convert the pain into an offer hypothesis",
                    "define deliverables, promise, proof, and onboarding",
                    "test with a simple MVP offer",
                    "feed results back into memory and pricing rules",
                ),
                outcomes=("offer hypothesis", "MVP package", "feedback loop"),
            ),
            AgencyWorkflow(
                name="Proposal To Delivery",
                trigger="Deal is accepted.",
                steps=(
                    "create project and kickoff checklist",
                    "attach customer goals, assets, and deadlines",
                    "dispatch specialist tasks",
                    "monitor status through heartbeat summaries",
                    "archive learnings for the next similar account",
                ),
                outcomes=("live delivery board", "tracked milestones", "reusable playbook"),
            ),
        ),
        guardrails=(
            "Keep customer data local-first or under explicit control.",
            "Do not skip human approval on pricing, scope, or irreversible actions.",
            "Treat memory as a product asset; update it after every major decision.",
            "Use proactive heartbeat checks for stale leads, blocked projects, and missed follow-ups.",
            "Measure each stage by conversion, cycle time, and cost-to-serve.",
        ),
    )


BLUEPRINT = _build_blueprint()


def _iter_lines(items: Iterable[str], prefix: str = "- ") -> list[str]:
    return [f"{prefix}{item}" for item in items]


def format_blueprint(blueprint: AgencyBlueprint = BLUEPRINT) -> str:
    lines: list[str] = [
        f"Agency OS Blueprint: {blueprint.name}",
        "",
        blueprint.thesis,
        "",
        "CLOSE Framework:",
    ]
    lines.extend(_iter_lines(blueprint.close_framework))
    lines.append("")
    lines.append("Layers:")
    for layer in blueprint.layers:
        lines.append(f"- {layer.name}: {layer.purpose}")
        lines.append(f"  Inputs: {', '.join(layer.inputs)}")
        lines.append(f"  Outputs: {', '.join(layer.outputs)}")
        lines.append(f"  Components: {', '.join(layer.components)}")
    lines.append("")
    lines.append("Core Workflows:")
    for workflow in blueprint.workflows:
        lines.append(f"- {workflow.name}: {workflow.trigger}")
        lines.extend(_iter_lines(workflow.steps, prefix="  * "))
        lines.append(f"  Outcomes: {', '.join(workflow.outcomes)}")
    lines.append("")
    lines.append("Guardrails:")
    lines.extend(_iter_lines(blueprint.guardrails))
    return "\n".join(lines)


def _goal_profile(goal: str) -> tuple[str, tuple[str, ...]]:
    lower = goal.lower()
    if any(keyword in lower for keyword in ("lead", "musteri", "customer", "discovery", "qualification")):
        return (
            "Customer Intake Focus",
            (
                "Use Intake Hub + Memory Layer first.",
                "Collect ICP, pain, urgency, budget, and source channel.",
                "Do not produce a proposal before qualification is stored.",
            ),
        )
    if any(keyword in lower for keyword in ("offer", "urun", "product", "paket", "pricing")):
        return (
            "Productization Focus",
            (
                "Use Memory Layer + Product Cell first.",
                "Translate repeated customer pain into one clear transformation.",
                "Lock scope, proof, onboarding, and pricing before sales scaling.",
            ),
        )
    if any(keyword in lower for keyword in ("sales", "proposal", "outreach", "crm", "close")):
        return (
            "Sales Motion Focus",
            (
                "Use Orchestration Layer + Sales Cell first.",
                "Attach proof, objections, follow-up rhythm, and next action.",
                "Track every deal stage in a shared CRM state.",
            ),
        )
    return (
        "General Agency Build",
        (
            "Start with Intake Hub, Memory Layer, and Orchestration Layer.",
            "Deploy specialist cells only after the request is normalized.",
            "Protect every long-running workflow with heartbeat and approval gates.",
        ),
    )


def agency_os_command(goal: str = "") -> str:
    clean_goal = goal.strip()
    if not clean_goal:
        return format_blueprint()

    profile_name, profile_steps = _goal_profile(clean_goal)
    lines = [
        f"Agency OS Goal: {clean_goal}",
        f"Recommended Profile: {profile_name}",
        "",
        "Execution Order:",
    ]
    lines.extend(_iter_lines(profile_steps))
    lines.append("")
    lines.append("Reference Architecture:")
    lines.append(format_blueprint())
    return "\n".join(lines)
