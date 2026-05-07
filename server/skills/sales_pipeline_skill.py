from __future__ import annotations

"""
Sales pipeline skill.

Implements a deterministic Agency OS style pipeline that flows from customer
understanding to product packaging to sales execution.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PipelineStage:
    name: str
    goal: str
    tasks: tuple[str, ...]
    outputs: tuple[str, ...]
    metrics: tuple[str, ...]


@dataclass(frozen=True)
class SalesPipeline:
    name: str
    thesis: str
    stages: tuple[PipelineStage, ...]


def _build_pipeline(target: str) -> SalesPipeline:
    offer = target.strip() or "AI hizmeti"
    return SalesPipeline(
        name="Customer -> Product -> Sales",
        thesis=(
            f"Build the pipeline around the customer problem first, package it as"
            f" a simple offer for {offer}, then scale the sales motion with proof"
            " and follow-up discipline."
        ),
        stages=(
            PipelineStage(
                name="Customer",
                goal="Find the right customer segment and define the buying trigger.",
                tasks=(
                    "Map ICP, niche, and buying authority.",
                    "List pain points, urgency, and current workaround.",
                    "Define qualification rules for budget, timing, and fit.",
                    "Capture proof signals from calls, comments, and inbound messages.",
                ),
                outputs=(
                    "ICP card",
                    "pain map",
                    "qualification checklist",
                    "channel priority list",
                ),
                metrics=(
                    "qualified lead rate",
                    "response rate by channel",
                    "lead source quality",
                ),
            ),
            PipelineStage(
                name="Product",
                goal="Turn repeated customer pain into a clear and sellable package.",
                tasks=(
                    f"Define the core transformation for {offer}.",
                    "Set scope, deliverables, timeline, and success criteria.",
                    "Create pricing ladder: entry, core, and premium.",
                    "Attach proof, case studies, objections, and onboarding notes.",
                ),
                outputs=(
                    "offer sheet",
                    "pricing ladder",
                    "proof library",
                    "onboarding checklist",
                ),
                metrics=(
                    "proposal acceptance rate",
                    "gross margin",
                    "time to onboard",
                ),
            ),
            PipelineStage(
                name="Sales",
                goal="Move qualified leads through outreach, qualification, proposal, and close.",
                tasks=(
                    "Write outbound opener, discovery questions, and objection handling.",
                    "Run CRM stages: contacted, qualified, proposed, won, lost.",
                    "Set follow-up cadence for 24h, 72h, 7d, and 14d.",
                    "Record win/loss reasons and feed them back into product packaging.",
                ),
                outputs=(
                    "outreach sequence",
                    "call script",
                    "CRM stage model",
                    "follow-up playbook",
                ),
                metrics=(
                    "meeting booked rate",
                    "proposal-to-close rate",
                    "sales cycle length",
                    "win/loss reasons",
                ),
            ),
        ),
    )


def _format_stage(stage: PipelineStage) -> list[str]:
    lines = [f"- {stage.name}: {stage.goal}"]
    lines.append(f"  Tasks: {', '.join(stage.tasks)}")
    lines.append(f"  Outputs: {', '.join(stage.outputs)}")
    lines.append(f"  Metrics: {', '.join(stage.metrics)}")
    return lines


def pipeline_command(target: str = "") -> str:
    pipeline = _build_pipeline(target)
    lines = [
        f"Pipeline: {pipeline.name}",
        "",
        pipeline.thesis,
        "",
        "Stages:",
    ]
    for stage in pipeline.stages:
        lines.extend(_format_stage(stage))
    lines.append("")
    lines.append("Operating Rule: do not scale sales before customer pain, offer scope, and proof are explicit.")
    return "\n".join(lines)
