from __future__ import annotations

import pytest

from server.orchestrator.swarm_coordinator import (
    DEFAULT_SWARM_SLOTS,
    SwarmCoordinator,
    SwarmCoordinatorError,
    SwarmState,
    TaskStatus,
)


def test_swarm_coordinator_is_instantiable_with_five_slots() -> None:
    coordinator = SwarmCoordinator("Build Jarvis Instagram account in 48 hours")

    assert coordinator.state == SwarmState.NEW
    assert len(coordinator.slots) == 5
    assert [slot.slot_id for slot in DEFAULT_SWARM_SLOTS] == [
        "forge",
        "nexus",
        "spark_buse",
        "spark_eren",
        "atlas",
    ]


def test_assign_task_moves_to_running_and_selects_expected_roles() -> None:
    coordinator = SwarmCoordinator("Instagram buildout")

    forge_task = coordinator.assign_task("Run batch scraper smoke", role="code")
    buse_task = coordinator.assign_task("Analyze Reel 021-030", role="content")
    eren_task = coordinator.assign_task("Score engagement metrics", role="data")
    atlas_task = coordinator.assign_task("Synthesize CEO strategy", role="strategy")

    assert coordinator.state == SwarmState.RUNNING
    assert forge_task.slot_id == "forge"
    assert buse_task.slot_id == "spark_buse"
    assert eren_task.slot_id == "spark_eren"
    assert atlas_task.slot_id == "atlas"
    assert buse_task.execution_slot == "spark"
    assert eren_task.execution_slot == "spark"


def test_assign_task_rejects_more_than_five_occupied_slots() -> None:
    coordinator = SwarmCoordinator("Capacity test")

    for index in range(5):
        coordinator.assign_task(f"Task {index + 1}")

    with pytest.raises(SwarmCoordinatorError):
        coordinator.assign_task("Task 6")


def test_collect_results_and_aggregate_reports_counts_outputs_and_errors() -> None:
    coordinator = SwarmCoordinator("Aggregate test", goal_id="swarm_test")
    task_a = coordinator.assign_task("Scrape handles", slot_id="forge")
    task_b = coordinator.assign_task("Collect ops state", slot_id="nexus")
    task_c = coordinator.assign_task("Analyze reels", slot_id="spark_buse")

    status = coordinator.collect_results(
        {
            task_a.task_id: {
                "success": True,
                "output": {"profiles": 5},
                "metrics": {"profiles": 5},
            },
            task_b.task_id: {
                "status": "error",
                "error": "rate limited",
            },
            task_c.task_id: "top reel pattern found",
        }
    )
    report = coordinator.aggregate_reports()

    assert status["state"] == "COLLECTING"
    assert coordinator.state == SwarmState.DONE
    assert report["goal_id"] == "swarm_test"
    assert report["summary"] == {
        "total_tasks": 3,
        "successful": 2,
        "failed": 1,
        "pending": 0,
        "slots": 5,
    }
    assert report["outputs"][task_a.task_id] == {"profiles": 5}
    assert report["outputs"][task_c.task_id] == "top reel pattern found"
    assert report["errors"][task_b.task_id] == "rate limited"
    assert "2 basarili, 1 hatali" in report["narrative"]


def test_state_machine_records_collecting_reporting_done_order() -> None:
    coordinator = SwarmCoordinator("State test")
    task = coordinator.assign_task("One task", persona="seda")

    coordinator.collect_results({task.task_id: {"success": True, "output": "ok"}})
    report = coordinator.aggregate_reports()

    states = [item["state"] for item in report["state_history"]]
    assert states == ["NEW", "RUNNING", "COLLECTING", "REPORTING", "DONE"]
    assert coordinator.tasks[task.task_id].status == TaskStatus.COMPLETED


def test_submit_result_collects_one_offline_result() -> None:
    coordinator = SwarmCoordinator("Submit result test")
    task = coordinator.assign_task("Scrape handles", slot_id="forge")

    status = coordinator.submit_result(
        task.task_id,
        success=True,
        output={"profiles": 5},
        metrics={"profiles": 5},
    )

    assert status["state"] == "COLLECTING"
    assert status["collected_results"] == 1
    assert coordinator.tasks[task.task_id].status == TaskStatus.COMPLETED
    assert coordinator.results[task.task_id].output == {"profiles": 5}
    assert coordinator.results[task.task_id].metrics == {"profiles": 5}
