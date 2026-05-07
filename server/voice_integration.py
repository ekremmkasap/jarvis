#!/usr/bin/env python3
"""
Voice Integration Layer
Connects Gemini voice to the planning and execution pipeline
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# Add server to path
sys.path.insert(0, str(Path(__file__).parent))

from voice.gemini_simple_chat import GeminiConversationSession
from agents.planner_agent import PlannerAgent
from agents.executor_agent import ExecutorAgent
from agents.error_handler_agent import ErrorHandlerAgent

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)


class VoiceIntegrationManager:
    """Manage voice input → planning → execution pipeline"""

    def __init__(self, log_dir: str = "server/logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.voice_session: Optional[GeminiConversationSession] = None
        self.executor = ExecutorAgent(log_dir=log_dir)
        self.error_handler = ErrorHandlerAgent(log_dir=log_dir)
        self.integration_log = self.log_dir / "voice_integration.jsonl"

    async def initialize_voice_session(self, session_seconds: int = 300) -> bool:
        """Initialize Gemini voice session"""
        try:
            self.voice_session = GeminiConversationSession(
                session_seconds=session_seconds
            )
            logger.info(f"Voice session initialized (duration: {session_seconds}s)")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize voice session: {e}")
            return False

    async def voice_test(self, test_duration_minutes: int = 2) -> Dict[str, Any]:
        """
        Run 2-minute voice test: capture audio, process, respond.

        Returns:
            Dict with test_status, turns_completed, errors
        """
        if not self.voice_session:
            await self.initialize_voice_session(session_seconds=test_duration_minutes * 60)

        test_record = {
            "timestamp": datetime.now().isoformat(),
            "test_duration_minutes": test_duration_minutes,
            "turns": [],
            "test_status": "running",
            "errors": [],
        }

        try:
            # Run voice test for specified duration
            turn_count = 0
            max_turns = 5  # Limit to 5 turns for 2-minute test

            print(f"\n🎤 Starting {test_duration_minutes}-minute voice test...")
            print("Speak naturally, or type English/Turkish text:")
            print("Commands: 'quit' to exit, 'status' for info\n")

            while self.voice_session.is_active() and turn_count < max_turns:
                try:
                    # Get user input (voice or text)
                    user_input = input("\nYou: ").strip()

                    if user_input.lower() in ["quit", "exit", "çıkış"]:
                        break

                    if not user_input:
                        continue

                    # Send to Gemini
                    response = self.voice_session.send_user_message(user_input)

                    # Log turn
                    turn_record = {
                        "turn_num": turn_count,
                        "user_input": user_input[:200],
                        "response_length": len(response),
                        "status": "success",
                    }
                    test_record["turns"].append(turn_record)

                    print(f"\nJarvis: {response}\n")
                    turn_count += 1

                except Exception as e:
                    error_msg = str(e)
                    test_record["errors"].append(error_msg)
                    logger.error(f"Turn {turn_count} error: {error_msg}")
                    print(f"Error: {error_msg}\n")
                    break

            test_record["test_status"] = "completed"
            test_record["turns_completed"] = turn_count

        except KeyboardInterrupt:
            test_record["test_status"] = "interrupted"
        except Exception as e:
            test_record["test_status"] = "failed"
            test_record["errors"].append(str(e))
            logger.error(f"Test failed: {e}")

        # Log test result
        self._log_integration_event(test_record)
        return test_record

    async def process_voice_command(self, user_input: str) -> Dict[str, Any]:
        """
        Process a voice command: parse → plan → execute.

        Steps:
        1. Capture/parse user intent
        2. Generate plan using PlannerAgent
        3. Execute plan using ExecutorAgent
        4. Handle errors if needed
        """
        if not self.voice_session:
            await self.initialize_voice_session()

        process_record = {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "stages": {},
        }

        try:
            # Stage 1: Voice capture
            logger.info(f"Processing voice command: {user_input[:100]}")
            process_record["stages"]["voice_capture"] = {
                "status": "success",
                "input_length": len(user_input),
            }

            # Stage 2: Get Gemini interpretation
            gemini_response = self.voice_session.send_user_message(user_input)
            process_record["stages"]["gemini_interpretation"] = {
                "status": "success",
                "response": gemini_response[:200],
            }

            # Stage 3: Plan generation
            # (In a real system, this would call PlannerAgent)
            plan = self._generate_simple_plan(user_input)
            process_record["stages"]["planning"] = {
                "status": "success",
                "plan_steps": len(plan),
            }

            # Stage 4: Execution
            execution_result = await self.executor.execute_plan(plan)
            process_record["stages"]["execution"] = {
                "status": execution_result["status"],
                "completed_steps": execution_result["completed_steps"],
                "total_steps": execution_result["total_steps"],
            }

            # Stage 5: Error handling if needed
            if execution_result["status"] != "success":
                failed_step = plan[execution_result["failed_at"]]
                error_result = await self.error_handler.handle_step_error(
                    step_definition=failed_step,
                    error=f"Step {execution_result['failed_at']} failed",
                    execution_history=execution_result["steps"],
                )
                process_record["stages"]["error_handling"] = {
                    "status": "handled",
                    "recovery_action": error_result["recovery_action"],
                }

            process_record["final_status"] = "completed"

        except Exception as e:
            process_record["final_status"] = "failed"
            process_record["error"] = str(e)
            logger.error(f"Voice command processing failed: {e}")

        # Log the full process
        self._log_integration_event(process_record)
        return process_record

    def _generate_simple_plan(self, user_input: str) -> list:
        """Generate a simple plan from user input (fallback)"""
        # This is a placeholder; real system would use PlannerAgent
        return [
            {
                "action": "analyze_input",
                "target": user_input,
                "params": {},
            },
            {
                "action": "generate_response",
                "target": "gemini",
                "params": {"input": user_input},
            },
        ]

    def _log_integration_event(self, record: Dict[str, Any]) -> None:
        """Log integration event to JSONL"""
        try:
            with open(self.integration_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Failed to log integration event: {e}")

    def get_voice_test_results(self) -> Dict[str, Any]:
        """Retrieve voice test results"""
        if not self.integration_log.exists():
            return {"status": "no_data"}

        test_results = []
        try:
            with open(self.integration_log, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        record = json.loads(line)
                        if "test_duration_minutes" in record:
                            test_results.append(record)
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            logger.error(f"Failed to read voice test results: {e}")

        return {
            "status": "completed",
            "total_tests": len(test_results),
            "latest_test": test_results[-1] if test_results else None,
        }


async def main():
    """Main entry point for voice integration"""
    manager = VoiceIntegrationManager()

    # Initialize voice session
    success = await manager.initialize_voice_session(session_seconds=600)  # 10 min
    if not success:
        print("Failed to initialize voice session")
        return

    print("Voice Integration Test")
    print("=" * 50)

    # Run 2-minute voice test
    test_result = await manager.voice_test(test_duration_minutes=2)

    print("\n" + "=" * 50)
    print("Test Results:")
    print(json.dumps(test_result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
