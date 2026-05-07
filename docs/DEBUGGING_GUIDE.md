# Week 2 Debugging Guide - AZIZ-5

**Last Updated:** April 4, 2026  
**System:** Jarvis Mission Control Week 2  
**Audience:** Developers, DevOps, Operations

---

## Quick Reference

### Common Issues & Solutions

| Issue | Symptom | Solution |
|-------|---------|----------|
| Cache not working | All calls slow | Check cache initialization in setUp() |
| Metrics not recorded | No metrics file | Verify log_dir permissions |
| Tests failing | Import errors | Install circuit_breaker dependency |
| Voice input error | Cannot extract goal | Check TASK_PREFIXES in voice_layer.py |
| Memory leak | Growing memory | Check cache eviction, TTL settings |

---

## 1. Test Execution Debugging

### Running Tests with Verbose Output

```bash
# Run single test
python -m unittest tests.test_week2_e2e.Week2E2ETests.test_10_call_sequence -v

# Run all Week 2 tests
python -m unittest tests.test_week2_e2e -v

# Run with more detailed output
python -m unittest tests.test_week2_e2e -v 2>&1 | tee test_run.log
```

### Common Test Failures

#### 1.1 Import Errors

**Error:** `ModuleNotFoundError: No module named 'circuit_breaker'`

**Root Cause:** Missing dependency for voice layer

**Solution:**
```bash
# Check if circuit_breaker.py exists
ls server/voice/circuit_breaker.py

# If missing, create minimal version
python -c "
import sys
sys.path.insert(0, 'server/voice')
"
```

#### 1.2 Assertion Failures

**Error:** `AssertionError: Success rate too low`

**Root Cause:** Execution failures in test tools

**Debugging:**
```python
# Add debug prints to test
import logging
logging.basicConfig(level=logging.DEBUG)

# Check individual tool execution
def tracked_tool(action: str):
    def _tool(payload: dict) -> dict:
        print(f"Executing {action} with {payload}")  # ADD THIS
        # ... rest of implementation
```

#### 1.3 Metric Collection Issues

**Error:** `AssertionError: No metrics recorded`

**Root Cause:** Metrics file not created or permissions issue

**Debugging:**
```python
# Check log directory exists
from pathlib import Path
log_dir = Path("server/logs/test_week2")
print(f"Log dir exists: {log_dir.exists()}")
print(f"Log dir writable: {log_dir.stat().st_mode}")

# Check metrics file
metrics_file = log_dir / "execution_metrics.jsonl"
print(f"Metrics file exists: {metrics_file.exists()}")
```

---

## 2. Execution Flow Debugging

### Tracing Voice → Plan → Execute Flow

#### 2.1 Voice Input Processing

**File:** Tests simulate voice with task prefix

**Debug Points:**
```python
# Verify voice input extraction
voice_input = "task: Build a test workflow"
goal = voice_input.replace("task:", "").strip()
print(f"Extracted goal: {goal}")

# Expected output: "Build a test workflow"
```

#### 2.2 Planning Phase

**File:** `server/agents/task_planner_agent.py`

**Debug Points:**
```python
# Check plan generation
plan_result = planner.plan(goal, requested_actions=["analyze", "test"])
print(f"Plan OK: {plan_result.ok}")
print(f"Steps: {len(plan_result.steps)}")
for i, step in enumerate(plan_result.steps):
    print(f"  Step {i+1}: {step.action} - {step.description}")
```

#### 2.3 Execution Phase

**File:** `server/agents/executor_agent.py`

**Debug Points:**
```python
# Monitor execution
for step in steps:
    print(f"\nExecuting: {step.action}")
    start = time.time()
    
    outcome = executor.execute_step(step, run_id="debug")
    
    duration = time.time() - start
    print(f"  Status: {outcome['ok']}")
    print(f"  Duration: {duration:.3f}s")
    print(f"  Result: {outcome.get('result', 'N/A')}")
```

---

## 3. Metrics & Monitoring Debugging

### 3.1 Metrics Collection Issues

**File:** `server/monitoring/execution_metrics.py`

**Check if metrics are being recorded:**
```python
from server.monitoring.execution_metrics import ExecutionMetricsCollector
from pathlib import Path

collector = ExecutionMetricsCollector(log_dir="server/logs/test_week2")
metrics = collector.get_recent_metrics(limit=100)

print(f"Total metrics: {len(metrics)}")
for metric in metrics[-5:]:
    print(f"  {metric.timestamp} | {metric.action} | {metric.status} | {metric.duration_seconds}s")
```

**File Location:** `server/logs/test_week2/execution_metrics.jsonl`

**Expected Format:**
```json
{
  "timestamp": "2026-04-04T12:00:00.123456+00:00",
  "run_id": "test",
  "action": "analyze",
  "status": "success",
  "duration_seconds": 0.042,
  "result_size_bytes": 128,
  "error_message": null,
  "cache_hit": false,
  "retry_count": 0
}
```

### 3.2 Cache Performance Debugging

**File:** `server/agents/execution_cache.py`

**Monitor cache hits/misses:**
```python
from server.agents.execution_cache import ExecutionCache

cache = ExecutionCache(ttl_seconds=300, max_entries=50)

# First call - miss
result, hit = cache.get("analyze", {"description": "test"})
print(f"First call hit: {hit}")  # Should be False

# Set value
cache.set("analyze", {"description": "test"}, {"result": "data"})

# Second call - hit
result, hit = cache.get("analyze", {"description": "test"})
print(f"Second call hit: {hit}")  # Should be True

# Get statistics
stats = cache.get_stats()
print(f"Cache stats: {stats}")
```

**Expected Stats:**
```python
{
    "hits": 1,
    "misses": 1,
    "total_entries": 1,
    "hit_rate_pct": 50.0
}
```

---

## 4. Performance Debugging

### 4.1 Latency Analysis

**Identify slow operations:**
```python
import time
from server.agents.week1_pipeline import Week1Pipeline

pipeline = Week1Pipeline()

# Measure end-to-end time
start = time.time()
result = pipeline.run("Test goal", requested_actions=["analyze", "test"])
total_duration = time.time() - start

print(f"Total duration: {total_duration:.3f}s")
print(f"Per-action average: {total_duration / 2:.3f}s")

# Check individual step durations
if total_duration > 1.0:
    print("WARNING: Slow execution detected")
    print("  Check: network latency, CPU load, memory pressure")
```

### 4.2 Memory Profiling

**Track memory usage:**
```python
import psutil
import os

process = psutil.Process(os.getpid())

# Get initial memory
mem_start = process.memory_info().rss / 1024 / 1024  # MB

# Run tests
for i in range(10):
    pipeline.run(f"Test {i}", requested_actions=["analyze"])

# Get final memory
mem_end = process.memory_info().rss / 1024 / 1024  # MB

print(f"Memory delta: {mem_end - mem_start:.2f} MB")
if mem_end - mem_start > 100:
    print("WARNING: Significant memory growth detected")
    print("  Check: cache size, metrics file growth, session leaks")
```

### 4.3 Throughput Analysis

**Measure calls per second:**
```python
import time

start = time.time()
call_count = 0

# Run for 10 seconds
while time.time() - start < 10:
    pipeline.run(f"Call {call_count}", requested_actions=["analyze"])
    call_count += 1

elapsed = time.time() - start
throughput = call_count / elapsed

print(f"Throughput: {throughput:.1f} calls/second")
print(f"Total calls: {call_count}")
print(f"Time: {elapsed:.1f}s")
```

---

## 5. Health Monitoring Debugging

### 5.1 Component Health Checks

**File:** `server/monitoring/health_check.py`

**Check component status:**
```python
from server.monitoring.health_check import HealthChecker
from pathlib import Path

checker = HealthChecker(log_dir="server/logs/test_week2")

# Get component status
components = checker.check_components()
for component, status in components.items():
    print(f"{component}: {status}")

# Get overall status
status = checker.get_status()
print(f"\nOverall status: {status.status}")
print(f"Response code: {200 if status.status == 'healthy' else 503}")

# Get health endpoint response
response, status_code = checker.get_health_endpoint_response()
print(f"\nEndpoint response:")
print(f"  Status: {response['status']}")
print(f"  HTTP Code: {status_code}")
```

---

## 6. Error Recovery Debugging

### 6.1 Tracking Recovery Attempts

**File:** `server/agents/error_handler_agent.py`

**Monitor error recovery:**
```python
# Check recoveries in results
result = pipeline.run("Test goal", requested_actions=["analyze", "implement", "test"])

print(f"Recoveries attempted: {len(result['recoveries'])}")
for recovery in result['recoveries']:
    print(f"\nRecovery {recovery['decision']}:")
    print(f"  Original step: {recovery['step']['action']}")
    print(f"  Retry attempts: {recovery['retry_attempts']}")
    print(f"  Replan attempts: {recovery['replan_attempts']}")
    print(f"  Success: {recovery['ok']}")
```

---

## 7. Data Inspection

### 7.1 Reading Log Files

**Metrics Log:**
```bash
# View recent metrics
tail -20 server/logs/test_week2/execution_metrics.jsonl

# Parse JSON
python -c "
import json
with open('server/logs/test_week2/execution_metrics.jsonl') as f:
    metrics = [json.loads(line) for line in f]
    print(f'Total: {len(metrics)}')
    actions = {}
    for m in metrics:
        actions[m['action']] = actions.get(m['action'], 0) + 1
    print('By action:', actions)
"
```

**Pipeline Log:**
```bash
# View pipeline execution log
tail -50 server/logs/week1_pipeline.log

# Count errors
grep ERROR server/logs/week1_pipeline.log | wc -l
```

### 7.2 Checking File Permissions

```bash
# Check log directory
ls -la server/logs/test_week2/

# Fix permissions if needed
chmod 755 server/logs/test_week2/
chmod 644 server/logs/test_week2/*.jsonl
```

---

## 8. Specific Test Debugging

### 8.1 Debug 10-Call Sequence Test

```python
from tests.test_week2_e2e import Week2E2ETests

test = Week2E2ETests()
test.setUp()

print("Running 10-call sequence...")
results = []

for call_num in range(1, 11):
    print(f"\nCall {call_num}:")
    goal = f"Execute task sequence call {call_num}"
    
    start = time.time()
    result = test.pipeline.run(
        goal,
        requested_actions=["analyze", "test"],
    )
    duration = time.time() - start
    
    print(f"  Duration: {duration:.3f}s")
    print(f"  Success: {result['ok']}")
    print(f"  Steps: {len(result['steps'])}")
    
    results.append(result)

# Summary
successful = sum(1 for r in results if r['ok'])
print(f"\nSummary: {successful}/10 successful")

# Statistics
stats = test.call_tracker.get_stats()
print(f"Statistics: {stats}")
```

### 8.2 Debug Cache Performance Test

```python
test = Week2E2ETests()
test.setUp()

print("Testing cache performance...")

# Warm up cache
for i in range(3):
    test.pipeline.run("Cache test", requested_actions=["analyze"])

# Measure cached vs non-cached
print("\nMeasuring cached performance:")
start = time.time()
for i in range(5):
    test.pipeline.run("Cached test", requested_actions=["analyze"])
cached_time = time.time() - start

print("\nMeasuring non-cached performance:")
cache_cleared = True
test.cache.clear()
start = time.time()
for i in range(5):
    test.pipeline.run("Non-cached test", requested_actions=["test"])  # Different action
non_cached_time = time.time() - start

print(f"\nCached: {cached_time:.3f}s")
print(f"Non-cached: {non_cached_time:.3f}s")
print(f"Speedup: {non_cached_time / cached_time:.1f}x")
```

---

## 9. Performance Profiling

### 9.1 Using Python cProfile

```bash
# Profile the 10-call test
python -m cProfile -s cumulative -m unittest tests.test_week2_e2e.Week2E2ETests.test_10_call_sequence 2>&1 | head -30
```

**Output Analysis:**
- `ncalls`: Number of calls
- `tottime`: Total time in function
- `cumtime`: Cumulative time (including called functions)

### 9.2 Line Profiling

```python
# For detailed line-by-line timing
# Install: pip install line_profiler

from line_profiler import LineProfiler
from server.agents.executor_agent import ExecutorAgent

profiler = LineProfiler()
profiler.add_function(ExecutorAgent.execute_step)

profiler.enable()
# ... run code ...
profiler.disable()

profiler.print_stats()
```

---

## 10. Troubleshooting Checklist

### Before Escalating Issues

- [ ] Verify Python 3.11+ is installed
- [ ] Confirm all dependencies are installed
- [ ] Check log directories exist and are writable
- [ ] Verify test suite runs without errors
- [ ] Check metrics files are being created
- [ ] Confirm cache is operational
- [ ] Validate health checks pass
- [ ] Review error recovery tracking

### Information to Gather

When reporting issues, include:

1. **Environment:**
   ```bash
   python --version
   python -m pip list | grep -E "(requests|psutil|PyYAML)"
   ```

2. **Test Output:**
   ```bash
   python -m unittest tests.test_week2_e2e -v 2>&1 | tail -50
   ```

3. **Relevant Logs:**
   ```bash
   tail -100 server/logs/week1_pipeline.log
   tail -20 server/logs/test_week2/execution_metrics.jsonl
   ```

4. **System Status:**
   ```bash
   # Check disk space
   df -h server/logs/
   
   # Check memory
   free -h
   
   # Check CPU load
   top -b -n 1 | head -10
   ```

---

## 11. Recovery Procedures

### 11.1 Clear Corrupted Metrics

```bash
# Backup current metrics
cp server/logs/test_week2/execution_metrics.jsonl \
   server/logs/test_week2/execution_metrics.jsonl.bak

# Clear metrics
rm server/logs/test_week2/execution_metrics.jsonl

# Re-run tests to regenerate
python -m unittest tests.test_week2_e2e -v
```

### 11.2 Reset Cache

```python
from server.agents.execution_cache import ExecutionCache

cache = ExecutionCache()
cache.clear()
print("Cache cleared")
```

### 11.3 Check System Health

```python
from server.monitoring.health_check import HealthChecker

checker = HealthChecker()
response, code = checker.get_health_endpoint_response()

print(f"Status: {response['status']}")
print(f"Components: {response.get('components', {})}")

if code != 200:
    print("WARNING: System not healthy")
    print("Recommendations:")
    print("  - Check disk space")
    print("  - Verify permissions")
    print("  - Restart service")
```

---

## 12. Performance Tuning

### 12.1 Cache Tuning

```python
# Increase cache size for better hit rate
cache = ExecutionCache(
    ttl_seconds=600,  # Increase TTL
    max_entries=100   # Increase size
)

# Monitoring cache impact
stats = cache.get_stats()
if stats["hit_rate_pct"] < 20:
    print("Cache hit rate low - increase TTL or size")
if stats["total_entries"] > 80:
    print("Cache approaching capacity - increase max_entries")
```

### 12.2 Metrics Tuning

```python
# Archive old metrics to reduce disk usage
from pathlib import Path
import gzip
import shutil

metrics_file = Path("server/logs/test_week2/execution_metrics.jsonl")
archive_path = Path("server/logs/test_week2/execution_metrics.jsonl.gz")

with open(metrics_file, 'rb') as f_in:
    with gzip.open(archive_path, 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)

metrics_file.unlink()  # Delete original
print(f"Archived to {archive_path}")
```

---

## Contact & Escalation

**For bugs:** Create issue with:
- Test name
- Error message
- Relevant logs
- System info

**For performance issues:** Include:
- Throughput measurement
- Latency graphs
- Memory profile
- Cache statistics

---

**Last Updated:** 2026-04-04  
**Maintainer:** Jarvis Team  
**Status:** Production Ready
