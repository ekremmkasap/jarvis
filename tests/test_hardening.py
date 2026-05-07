#!/usr/bin/env python3
"""
Test suite for Week 2 Hardening - Production Stability.

Tests circuit breaker, fallback responses, retry strategy, and error recovery.
"""

import sys
import time
import logging
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add server to path
sys.path.insert(0, str(Path(__file__).parent.parent / "server"))
sys.path.insert(0, str(Path(__file__).parent.parent / "server" / "voice"))

from voice.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerOpenError
from voice.retry_strategy import RetryStrategy, RetryConfig
from voice.fallback_responses import FallbackResponseManager
from voice.gemini_simple_chat import GeminiConversationSession, GeminiVoiceError
from agents.error_handler_agent import ErrorHandlerAgent, RecoveryDecision


class TestCircuitBreaker:
    """Test circuit breaker functionality."""

    def test_circuit_breaker_opens_after_threshold(self):
        """Circuit breaker should OPEN after N failures."""
        config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=1)
        cb = CircuitBreaker(config)

        def failing_func():
            raise ValueError("API Error")

        # First 3 calls fail
        for i in range(3):
            try:
                cb.call(failing_func)
            except ValueError:
                pass

        # 4th call should trigger OPEN state
        assert cb.state.value == "OPEN"
        try:
            cb.call(failing_func)
            assert False, "Should have raised CircuitBreakerOpenError"
        except CircuitBreakerOpenError as e:
            assert "Circuit breaker is OPEN" in str(e)

    def test_circuit_breaker_half_open_recovery(self):
        """Circuit breaker should recover to CLOSED after timeout."""
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=1)
        cb = CircuitBreaker(config)

        def failing_func():
            raise ValueError("API Error")

        # Trigger OPEN state
        for i in range(2):
            try:
                cb.call(failing_func)
            except ValueError:
                pass

        assert cb.state.value == "OPEN"

        # Wait for recovery window
        time.sleep(1.1)

        # Next call should attempt HALF_OPEN
        def success_func():
            return "OK"

        result = cb.call(success_func)
        assert result == "OK"
        assert cb.state.value == "CLOSED"

    def test_circuit_breaker_success_resets_count(self):
        """Successful calls should reset failure count."""
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker(config)

        def success_func():
            return "OK"

        # Successful call
        result = cb.call(success_func)
        assert result == "OK"
        assert cb.failure_count == 0
        assert cb.state.value == "CLOSED"

    def test_circuit_breaker_manual_reset(self):
        """Circuit breaker should support manual reset."""
        config = CircuitBreakerConfig(failure_threshold=1)
        cb = CircuitBreaker(config)

        def failing_func():
            raise ValueError("API Error")

        # Trigger OPEN
        try:
            cb.call(failing_func)
        except ValueError:
            pass

        assert cb.state.value == "OPEN"

        # Manual reset
        cb.reset()
        assert cb.state.value == "CLOSED"
        assert cb.failure_count == 0


class TestRetryStrategy:
    """Test retry strategy with exponential backoff."""

    def test_retry_succeeds_on_third_attempt(self):
        """Retry should succeed if function succeeds eventually."""
        config = RetryConfig(max_attempts=3, initial_delay=0.01)
        retry = RetryStrategy(config)

        call_count = 0

        def sometimes_failing():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "Success"

        result = retry.execute(sometimes_failing)
        assert result == "Success"
        assert call_count == 3
        assert retry.attempt_count == 3

    def test_retry_exhausts_attempts(self):
        """Retry should raise exception after max attempts."""
        config = RetryConfig(max_attempts=2, initial_delay=0.01)
        retry = RetryStrategy(config)

        def always_failing():
            raise ValueError("Permanent error")

        try:
            retry.execute(always_failing)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Permanent error" in str(e)
            assert retry.attempt_count == 2

    def test_retry_with_exponential_backoff(self):
        """Retry should apply exponential backoff."""
        config = RetryConfig(
            max_attempts=3, initial_delay=0.01, backoff_multiplier=2.0, jitter=False
        )
        retry = RetryStrategy(config)

        def always_failing():
            raise ValueError("Error")

        start = time.time()
        try:
            retry.execute(always_failing)
        except ValueError:
            pass
        elapsed = time.time() - start

        # 2 retries: 0.01s + 0.02s = 0.03s minimum
        assert elapsed >= 0.02

    def test_retry_single_attempt_success(self):
        """Retry should succeed immediately if function succeeds."""
        config = RetryConfig(max_attempts=3)
        retry = RetryStrategy(config)

        def success_func():
            return "Immediate success"

        result = retry.execute(success_func)
        assert result == "Immediate success"
        assert retry.attempt_count == 1


class TestFallbackResponses:
    """Test fallback response generation."""

    def test_fallback_greeting_detection(self):
        """Should detect greeting keywords."""
        response = FallbackResponseManager.get_response("merhaba", language="tr")
        assert "API" in response or "api" in response
        assert len(response) > 0

    def test_fallback_help_detection(self):
        """Should detect help keywords."""
        response = FallbackResponseManager.get_response("yardım", language="tr")
        assert "sağlana" in response or "sağlanemiyor" in response

    def test_fallback_language_detection(self):
        """Should detect language from input."""
        lang_tr = FallbackResponseManager.detect_language("merhaba dünya")
        assert lang_tr == "tr"

        lang_en = FallbackResponseManager.detect_language("hello world")
        assert lang_en == "en"

    def test_fallback_error_message(self):
        """Should generate error message from exception."""
        error = RuntimeError("circuit breaker open")
        msg = FallbackResponseManager.get_error_message(error, language="tr")
        assert len(msg) > 0

    def test_fallback_generic_response(self):
        """Should provide generic response for unknown input."""
        response = FallbackResponseManager.get_response("xyz123unknown", language="en")
        assert "API" in response or "temporarily" in response


class TestGeminiHardening:
    """Test Gemini chat hardening with circuit breaker and retry."""

    def test_gemini_session_with_circuit_breaker(self):
        """Gemini session should have circuit breaker."""
        mock_client = Mock()
        session = GeminiConversationSession(client=mock_client)

        assert session.circuit_breaker is not None
        assert session.circuit_breaker.config.failure_threshold == 3

    def test_gemini_session_with_retry_strategy(self):
        """Gemini session should have retry strategy."""
        mock_client = Mock()
        session = GeminiConversationSession(client=mock_client)

        assert session.retry_strategy is not None
        assert session.retry_strategy.config.max_attempts == 3

    def test_gemini_fallback_on_circuit_breaker_open(self):
        """Should return fallback when circuit breaker opens."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.text = "API Response"

        session = GeminiConversationSession(client=mock_client)

        # Manually open circuit breaker
        from voice.circuit_breaker import CircuitState
        session.circuit_breaker.state = CircuitState.OPEN

        response = session.send_user_message("test", use_fallback=True)
        assert "API" in response or "temporar" in response.lower()

    def test_gemini_fallback_multilingual(self):
        """Fallback should respect user language."""
        from voice.circuit_breaker import CircuitState
        mock_client = Mock()
        session = GeminiConversationSession(client=mock_client)

        # Open circuit breaker
        session.circuit_breaker.state = CircuitState.OPEN

        response_tr = session.send_user_message("merhaba", use_fallback=True)
        assert len(response_tr) > 0

        response_en = session.send_user_message("hello", use_fallback=True)
        assert len(response_en) > 0


class TestErrorHandlerIntegration:
    """Test error handler with circuit breaker awareness."""

    def test_error_handler_recognizes_circuit_breaker_error(self):
        """Error handler should recognize circuit breaker as transient."""
        handler = ErrorHandlerAgent(max_retries=2)

        error = CircuitBreakerOpenError("Circuit breaker is OPEN")
        decision = handler.decide_action(error, retry_attempts=0, replan_attempts=0)

        assert decision == RecoveryDecision.RETRY

    def test_error_handler_recovery_path(self):
        """Error handler should track recovery path."""
        handler = ErrorHandlerAgent(max_retries=1)

        def execute_step(step):
            if handler.stats.total_failures == 0:
                raise RuntimeError("network timeout")
            return {"result": "recovered"}

        step = {"name": "api_call"}
        error = RuntimeError("network timeout")

        result = handler.execute_with_recovery(
            step=step,
            error=error,
            execute_step=execute_step,
        )

        assert result.ok is True
        assert "RETRY" in result.recovery_path

    def test_error_handler_stats_tracking(self):
        """Error handler should track recovery statistics."""
        handler = ErrorHandlerAgent()

        assert handler.stats.total_failures == 0
        assert handler.stats.recovered == 0
        assert handler.stats.skipped == 0

        def failing_step(step):
            raise RuntimeError("permanent error")

        step = {"name": "test"}
        handler.execute_with_recovery(
            step=step,
            error=RuntimeError("error"),
            execute_step=failing_step,
        )

        assert handler.stats.total_failures > 0


class TestProductionScenarios:
    """Test real-world production failure scenarios."""

    def test_scenario_api_timeout_then_recovery(self):
        """Scenario: API times out, retry succeeds."""
        config = RetryConfig(max_attempts=3, initial_delay=0.01)
        retry = RetryStrategy(config)

        call_count = 0

        def timeout_then_success():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TimeoutError("API timeout")
            return "Response"

        result = retry.execute(timeout_then_success)
        assert result == "Response"

    def test_scenario_circuit_breaker_prevents_cascading_failure(self):
        """Scenario: Circuit breaker stops cascading API calls."""
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=10)
        cb = CircuitBreaker(config)

        api_calls = 0

        def api_call():
            nonlocal api_calls
            api_calls += 1
            raise ConnectionError("API unreachable")

        # First 2 calls fail, triggering OPEN
        for i in range(2):
            try:
                cb.call(api_call)
            except ConnectionError:
                pass

        # Next calls blocked immediately
        for i in range(5):
            try:
                cb.call(api_call)
            except CircuitBreakerOpenError:
                pass

        # Should have made only 2 API calls, not 7
        assert api_calls == 2

    def test_scenario_graceful_degradation(self):
        """Scenario: User gets helpful message when API fails."""
        manager = FallbackResponseManager

        user_inputs = [
            ("merhaba", "tr"),
            ("hello", "en"),
            ("yardım", "tr"),
            ("help", "en"),
        ]

        for user_input, lang in user_inputs:
            response = manager.get_response(user_input, language=lang)
            assert len(response) > 10  # Non-trivial response
            assert "API" in response or "servis" in response or "service" in response


def run_tests():
    """Run all tests."""
    test_classes = [
        TestCircuitBreaker,
        TestRetryStrategy,
        TestFallbackResponses,
        TestGeminiHardening,
        TestErrorHandlerIntegration,
        TestProductionScenarios,
    ]

    total_tests = 0
    passed_tests = 0
    failed_tests = []

    for test_class in test_classes:
        print(f"\n{'='*60}")
        print(f"Running {test_class.__name__}")
        print(f"{'='*60}")

        test_instance = test_class()
        test_methods = [method for method in dir(test_instance) if method.startswith("test_")]

        for method_name in test_methods:
            total_tests += 1
            try:
                method = getattr(test_instance, method_name)
                method()
                print(f"[PASS] {method_name}")
                passed_tests += 1
            except Exception as e:
                print(f"[FAIL] {method_name}: {e}")
                failed_tests.append((test_class.__name__, method_name, str(e)))

    print(f"\n{'='*60}")
    print(f"Test Results: {passed_tests}/{total_tests} passed")
    print(f"{'='*60}")

    if failed_tests:
        print("\nFailed Tests:")
        for class_name, method_name, error in failed_tests:
            print(f"  - {class_name}.{method_name}: {error}")
        return 1
    else:
        print("\nAll tests passed!")
        return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    sys.exit(run_tests())
