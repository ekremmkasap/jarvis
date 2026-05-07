#!/usr/bin/env python3
"""
Run a single autoresearch experiment iteration.
Handles: edit target, run eval, compare metric, keep/discard, log results.
"""

import argparse
import subprocess
import configparser
import sys
import time
import os
from pathlib import Path
from datetime import datetime

def get_short_hash():
    """Get current git short hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=Path.cwd()
        )
        return result.stdout.strip()
    except:
        return "unknown"

def load_config(experiment_path):
    """Load config.cfg from experiment directory."""
    config_file = experiment_path / "config.cfg"
    if not config_file.exists():
        raise FileNotFoundError(f"Config not found: {config_file}")

    config = configparser.ConfigParser()
    config.read(config_file)
    return config

def load_last_result(experiment_path):
    """Load best metric from results.tsv."""
    results_file = experiment_path / "results.tsv"
    if not results_file.exists():
        return None

    best_metric = None
    with open(results_file) as f:
        lines = f.readlines()
        for line in lines[1:]:  # Skip header
            parts = line.strip().split("\t")
            if len(parts) >= 2:
                try:
                    metric = float(parts[1])
                    if best_metric is None:
                        best_metric = metric
                    else:
                        # Will compare with direction later
                        pass
                except ValueError:
                    pass

    return best_metric

def run_evaluation(eval_cmd, time_budget_minutes):
    """Run evaluation command, return parsed metric or None on failure."""
    try:
        start = time.time()
        result = subprocess.run(
            eval_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=time_budget_minutes * 60 * 2.5  # 2.5x timeout
        )
        elapsed = time.time() - start

        # Parse output for "metric_name: value"
        metric_value = None
        for line in result.stdout.split("\n"):
            if ":" in line:
                key, val = line.split(":", 1)
                key = key.strip()
                val = val.strip()
                try:
                    metric_value = float(val)
                    break
                except ValueError:
                    pass

        return metric_value, elapsed, result.returncode == 0

    except subprocess.TimeoutExpired:
        return None, time_budget_minutes * 60 * 2.5, False
    except Exception as e:
        print(f"Eval error: {e}", file=sys.stderr)
        return None, 0, False

def log_result(experiment_path, commit_hash, metric, status, description):
    """Append result to results.tsv."""
    results_file = experiment_path / "results.tsv"

    # Create header if file doesn't exist
    if not results_file.exists():
        with open(results_file, "w") as f:
            f.write("commit\tmetric\tstatus\tdescription\n")

    # Append result
    metric_str = f"{metric:.2f}" if metric is not None else "N/A"
    with open(results_file, "a") as f:
        f.write(f"{commit_hash}\t{metric_str}\t{status}\t{description}\n")

def main():
    parser = argparse.ArgumentParser(description="Run single experiment iteration")
    parser.add_argument("--experiment", required=True, help="experiment/name (e.g., engineering/api-speed)")
    parser.add_argument("--single", action="store_true", help="Run one iteration only")
    parser.add_argument("--dry-run", action="store_true", help="Test eval command without committing")
    args = parser.parse_args()

    # Paths
    domain, name = args.experiment.split("/")
    base_path = Path(".autoresearch") / domain / name
    if not base_path.exists():
        print(f"Experiment not found: {base_path}", file=sys.stderr)
        sys.exit(1)

    # Load config
    config = load_config(base_path)
    exp_config = config["experiment"]
    target_file = exp_config["target"]
    eval_cmd = exp_config["evaluate_cmd"]
    metric_name = exp_config["metric"]
    metric_direction = exp_config["metric_direction"]
    time_budget = int(exp_config.get("time_budget_minutes", "5"))

    print(f"[autoresearch] {domain}/{name}")
    print(f"  Target: {target_file}")
    print(f"  Eval: {eval_cmd}")
    print(f"  Metric: {metric_name} ({metric_direction})")

    if args.dry_run:
        print("\n[DRY RUN] Testing evaluation command...")
        metric, elapsed, success = run_evaluation(eval_cmd, time_budget)
        if success and metric is not None:
            print(f"  [OK] Eval works! Metric: {metric:.2f}")
        else:
            print(f"  [FAIL] Eval failed or returned no metric")
        return

    # Run evaluation (baseline or after edit)
    print(f"\n[eval] Running: {eval_cmd}")
    metric, elapsed, success = run_evaluation(eval_cmd, time_budget)

    if not success or metric is None:
        print(f"  [CRASH] metric: N/A")
        commit_hash = get_short_hash()
        log_result(base_path, commit_hash, None, "crash", "Evaluation failed")
        sys.exit(1)

    # Get previous best
    prev_best = load_last_result(base_path)

    # Compare
    if prev_best is None:
        print(f"  [BASELINE] {metric:.2f} {metric_name}")
        status = "baseline"
    elif metric_direction == "higher" and metric > prev_best:
        improvement = ((metric - prev_best) / prev_best) * 100
        print(f"  [KEEP] +{improvement:.1f}% ({prev_best:.2f} -> {metric:.2f})")
        status = "keep"
    elif metric_direction == "lower" and metric < prev_best:
        improvement = ((prev_best - metric) / prev_best) * 100
        print(f"  [KEEP] -{improvement:.1f}% ({prev_best:.2f} -> {metric:.2f})")
        status = "keep"
    else:
        print(f"  [DISCARD] no improvement: {metric:.2f}")
        status = "discard"

    commit_hash = get_short_hash()
    description = f"{elapsed:.2f}s eval time"
    log_result(base_path, commit_hash, metric, status, description)

if __name__ == "__main__":
    main()
