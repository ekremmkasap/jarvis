"""
Tests for Vision Analyzer - Gemini Vision API Integration
Tests screenshot analysis, text extraction, UI element identification, and visual state tracking
"""
from __future__ import annotations

import base64
import json
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.agents.vision_analyzer import VisionAnalyzer, analyze_screenshot, extract_text, identify_ui_elements, track_visual_state


class VisionAnalyzerTests(unittest.TestCase):
    """Test suite for VisionAnalyzer class."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.test_image_path = Path(__file__).parent / "fixtures" / "test_screenshot.png"
        self.test_image_path.parent.mkdir(parents=True, exist_ok=True)

        # Create a minimal test image (1x1 PNG)
        png_data = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
            b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        self.test_image_path.write_bytes(png_data)

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        if self.test_image_path.exists():
            self.test_image_path.unlink()

    @patch("server.agents.vision_analyzer.genai")
    @patch("server.agents.vision_analyzer.HAS_GEMINI", True)
    def test_vision_analyzer_initialization(self, mock_genai: MagicMock) -> None:
        """Test VisionAnalyzer initialization."""
        mock_genai.GenerativeModel.return_value = MagicMock()

        analyzer = VisionAnalyzer(api_key="test-key")

        self.assertIsNotNone(analyzer)
        self.assertEqual(analyzer.api_key, "test-key")
        self.assertEqual(analyzer.model_name, "gemini-2.0-flash-exp")
        mock_genai.configure.assert_called_once_with(api_key="test-key")

    @patch("server.agents.vision_analyzer.genai")
    @patch("server.agents.vision_analyzer.HAS_GEMINI", True)
    def test_analyze_screenshot_success(self, mock_genai: MagicMock) -> None:
        """Test successful screenshot analysis."""
        # Setup mocks
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model

        mock_response = MagicMock()
        mock_response.text = json.dumps(
            {
                "description": "Login screen with username and password fields",
                "ui_elements": [
                    {"type": "text_field", "label": "Username", "state": "empty"},
                    {"type": "text_field", "label": "Password", "state": "empty"},
                    {"type": "button", "label": "Login", "state": "enabled"},
                ],
                "text_content": "Login Username Password Sign in",
                "visual_state": "ready",
            }
        )
        mock_model.generate_content.return_value = mock_response

        mock_genai.upload_file.return_value = MagicMock()

        # Create analyzer and test
        analyzer = VisionAnalyzer(api_key="test-key")
        result = analyzer.analyze_screenshot(image_path=str(self.test_image_path))

        # Assertions
        self.assertTrue(result["ok"])
        self.assertIsNotNone(result["analysis"])
        self.assertIn("description", result["analysis"])
        self.assertIn("ui_elements", result["analysis"])
        self.assertEqual(result["analysis"]["visual_state"], "ready")
        self.assertIsNone(result["error"])

    @patch("server.agents.vision_analyzer.genai")
    @patch("server.agents.vision_analyzer.HAS_GEMINI", True)
    def test_analyze_screenshot_with_invalid_path(self, mock_genai: MagicMock) -> None:
        """Test screenshot analysis with invalid file path."""
        mock_genai.GenerativeModel.return_value = MagicMock()

        analyzer = VisionAnalyzer(api_key="test-key")
        result = analyzer.analyze_screenshot(image_path="/nonexistent/path/image.png")

        self.assertFalse(result["ok"])
        self.assertIsNotNone(result["error"])
        self.assertIn("FileNotFoundError", result["error"]["type"])

    @patch("server.agents.vision_analyzer.genai")
    @patch("server.agents.vision_analyzer.HAS_GEMINI", True)
    def test_extract_text_success(self, mock_genai: MagicMock) -> None:
        """Test successful text extraction from image."""
        # Setup mocks
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model

        mock_response = MagicMock()
        mock_response.text = json.dumps(
            {
                "extracted_text": "Welcome to Jarvis Mission Control Dashboard",
                "text_blocks": [
                    {"text": "Welcome", "confidence": 0.98, "location": "top-left"},
                    {"text": "Jarvis Mission Control", "confidence": 0.99, "location": "center"},
                    {"text": "Dashboard", "confidence": 0.97, "location": "top-right"},
                ],
                "languages_detected": ["en"],
                "total_words": 5,
            }
        )
        mock_model.generate_content.return_value = mock_response

        mock_genai.upload_file.return_value = MagicMock()

        # Create analyzer and test
        analyzer = VisionAnalyzer(api_key="test-key")
        result = analyzer.extract_text(image_path=str(self.test_image_path))

        # Assertions
        self.assertTrue(result["ok"])
        self.assertIsNotNone(result["text_extraction"])
        self.assertIn("extracted_text", result["text_extraction"])
        self.assertEqual(result["text_extraction"]["total_words"], 5)
        self.assertIn("en", result["text_extraction"]["languages_detected"])

    @patch("server.agents.vision_analyzer.genai")
    @patch("server.agents.vision_analyzer.HAS_GEMINI", True)
    def test_extract_text_with_base64(self, mock_genai: MagicMock) -> None:
        """Test text extraction with base64 encoded image."""
        # Setup mocks
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model

        mock_response = MagicMock()
        mock_response.text = json.dumps(
            {
                "extracted_text": "Test text from base64",
                "text_blocks": [],
                "languages_detected": ["en"],
            }
        )
        mock_model.generate_content.return_value = mock_response

        mock_genai.upload_file.return_value = MagicMock()

        # Convert test image to base64
        image_bytes = self.test_image_path.read_bytes()
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        # Create analyzer and test
        analyzer = VisionAnalyzer(api_key="test-key")
        result = analyzer.extract_text(image_base64=image_base64)

        # Assertions
        self.assertTrue(result["ok"])
        self.assertIsNotNone(result["text_extraction"])

    @patch("server.agents.vision_analyzer.genai")
    @patch("server.agents.vision_analyzer.HAS_GEMINI", True)
    def test_identify_ui_elements_success(self, mock_genai: MagicMock) -> None:
        """Test successful UI element identification."""
        # Setup mocks
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model

        mock_response = MagicMock()
        mock_response.text = json.dumps(
            {
                "ui_elements": [
                    {
                        "type": "button",
                        "label": "Save",
                        "position": "bottom-right",
                        "state": "enabled",
                        "purpose": "Save form changes",
                        "color": "blue",
                    },
                    {
                        "type": "text_field",
                        "label": "Email",
                        "position": "center",
                        "state": "active",
                        "purpose": "Enter email address",
                        "color": "white",
                    },
                ],
                "ui_framework": "web",
                "interaction_ready": True,
                "accessibility_issues": [],
            }
        )
        mock_model.generate_content.return_value = mock_response

        mock_genai.upload_file.return_value = MagicMock()

        # Create analyzer and test
        analyzer = VisionAnalyzer(api_key="test-key")
        result = analyzer.identify_ui_elements(image_path=str(self.test_image_path))

        # Assertions
        self.assertTrue(result["ok"])
        self.assertIsNotNone(result["ui_elements"])
        self.assertGreater(len(result["ui_elements"].get("ui_elements", [])), 0)
        self.assertTrue(result["ui_elements"]["interaction_ready"])
        self.assertEqual(result["ui_elements"]["ui_framework"], "web")

    @patch("server.agents.vision_analyzer.genai")
    @patch("server.agents.vision_analyzer.HAS_GEMINI", True)
    def test_track_visual_state_success(self, mock_genai: MagicMock) -> None:
        """Test successful visual state tracking."""
        # Setup mocks
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model

        mock_response = MagicMock()
        mock_response.text = json.dumps(
            {
                "current_state": {
                    "page_status": "ready",
                    "modals_open": False,
                    "notifications": [],
                    "loading_indicators": False,
                    "error_messages": [],
                    "form_states": {"valid_fields": ["email", "password"], "invalid_fields": []},
                },
                "detected_changes": ["form_loaded"],
                "user_actions_available": ["submit", "reset"],
                "visual_flow": "Form is ready for user input",
            }
        )
        mock_model.generate_content.return_value = mock_response

        mock_genai.upload_file.return_value = MagicMock()

        # Create analyzer and test
        analyzer = VisionAnalyzer(api_key="test-key")
        result = analyzer.track_visual_state(image_path=str(self.test_image_path))

        # Assertions
        self.assertTrue(result["ok"])
        self.assertIsNotNone(result["state_tracking"])
        self.assertEqual(result["state_tracking"]["current_state"]["page_status"], "ready")
        self.assertFalse(result["state_tracking"]["current_state"]["loading_indicators"])

    @patch("server.agents.vision_analyzer.genai")
    @patch("server.agents.vision_analyzer.HAS_GEMINI", True)
    def test_track_visual_state_with_previous_state(self, mock_genai: MagicMock) -> None:
        """Test visual state tracking with comparison to previous state."""
        # Setup mocks
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model

        previous_state = {"page_status": "loading"}

        mock_response = MagicMock()
        mock_response.text = json.dumps(
            {
                "current_state": {"page_status": "ready"},
                "detected_changes": ["page_loaded"],
                "user_actions_available": ["click", "scroll"],
                "visual_flow": "Page transitioned from loading to ready",
            }
        )
        mock_model.generate_content.return_value = mock_response

        mock_genai.upload_file.return_value = MagicMock()

        # Create analyzer and test
        analyzer = VisionAnalyzer(api_key="test-key")
        result = analyzer.track_visual_state(
            image_path=str(self.test_image_path),
            previous_state=previous_state,
        )

        # Assertions
        self.assertTrue(result["ok"])
        self.assertIn("page_loaded", result["state_tracking"]["detected_changes"])

    @patch("server.agents.vision_analyzer.genai")
    @patch("server.agents.vision_analyzer.HAS_GEMINI", True)
    def test_gemini_import_failure(self, mock_genai: MagicMock) -> None:
        """Test handling of missing Gemini library."""
        with patch("server.agents.vision_analyzer.HAS_GEMINI", False):
            with self.assertRaises(ImportError):
                VisionAnalyzer(api_key="test-key")

    @patch("server.agents.vision_analyzer.genai")
    @patch("server.agents.vision_analyzer.HAS_GEMINI", True)
    def test_api_key_from_environment(self, mock_genai: MagicMock) -> None:
        """Test API key loading from environment."""
        with patch.dict("os.environ", {"GOOGLE_API_KEY": "env-test-key"}):
            mock_genai.GenerativeModel.return_value = MagicMock()

            analyzer = VisionAnalyzer()

            self.assertEqual(analyzer.api_key, "env-test-key")
            mock_genai.configure.assert_called_once_with(api_key="env-test-key")

    @patch("server.agents.vision_analyzer.genai")
    @patch("server.agents.vision_analyzer.HAS_GEMINI", True)
    def test_api_key_missing_error(self, mock_genai: MagicMock) -> None:
        """Test error handling when API key is missing."""
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ValueError):
                VisionAnalyzer()

    @patch("server.agents.vision_analyzer.genai")
    @patch("server.agents.vision_analyzer.HAS_GEMINI", True)
    def test_analyze_screenshot_with_malformed_response(self, mock_genai: MagicMock) -> None:
        """Test handling of malformed API response."""
        # Setup mocks
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model

        mock_response = MagicMock()
        mock_response.text = "This is not JSON - just plain text response from API"
        mock_model.generate_content.return_value = mock_response

        mock_genai.upload_file.return_value = MagicMock()

        # Create analyzer and test
        analyzer = VisionAnalyzer(api_key="test-key")
        result = analyzer.analyze_screenshot(image_path=str(self.test_image_path))

        # Should handle gracefully with fallback parsing
        self.assertTrue(result["ok"])
        self.assertIsNotNone(result["analysis"])
        self.assertEqual(result["analysis"]["parsing_method"], "fallback")

    @patch("server.agents.vision_analyzer.genai")
    @patch("server.agents.vision_analyzer.HAS_GEMINI", True)
    def test_standalone_analyze_screenshot_function(self, mock_genai: MagicMock) -> None:
        """Test standalone analyze_screenshot function."""
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model

        mock_response = MagicMock()
        mock_response.text = json.dumps(
            {
                "description": "Test screenshot",
                "ui_elements": [],
                "text_content": "Test",
                "visual_state": "ready",
            }
        )
        mock_model.generate_content.return_value = mock_response

        mock_genai.upload_file.return_value = MagicMock()

        result = analyze_screenshot(image_path=str(self.test_image_path), api_key="test-key")

        self.assertTrue(result["ok"])

    @patch("server.agents.vision_analyzer.genai")
    @patch("server.agents.vision_analyzer.HAS_GEMINI", True)
    def test_standalone_extract_text_function(self, mock_genai: MagicMock) -> None:
        """Test standalone extract_text function."""
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model

        mock_response = MagicMock()
        mock_response.text = json.dumps(
            {"extracted_text": "Sample text", "languages_detected": ["en"]}
        )
        mock_model.generate_content.return_value = mock_response

        mock_genai.upload_file.return_value = MagicMock()

        result = extract_text(image_path=str(self.test_image_path), api_key="test-key")

        self.assertTrue(result["ok"])

    @patch("server.agents.vision_analyzer.genai")
    @patch("server.agents.vision_analyzer.HAS_GEMINI", True)
    def test_standalone_identify_ui_elements_function(self, mock_genai: MagicMock) -> None:
        """Test standalone identify_ui_elements function."""
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model

        mock_response = MagicMock()
        mock_response.text = json.dumps(
            {
                "ui_elements": [{"type": "button", "label": "Click me"}],
                "ui_framework": "web",
            }
        )
        mock_model.generate_content.return_value = mock_response

        mock_genai.upload_file.return_value = MagicMock()

        result = identify_ui_elements(image_path=str(self.test_image_path), api_key="test-key")

        self.assertTrue(result["ok"])

    @patch("server.agents.vision_analyzer.genai")
    @patch("server.agents.vision_analyzer.HAS_GEMINI", True)
    def test_standalone_track_visual_state_function(self, mock_genai: MagicMock) -> None:
        """Test standalone track_visual_state function."""
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model

        mock_response = MagicMock()
        mock_response.text = json.dumps(
            {
                "current_state": {"page_status": "ready"},
                "detected_changes": [],
                "user_actions_available": [],
            }
        )
        mock_model.generate_content.return_value = mock_response

        mock_genai.upload_file.return_value = MagicMock()

        result = track_visual_state(image_path=str(self.test_image_path), api_key="test-key")

        self.assertTrue(result["ok"])

    @patch("server.agents.vision_analyzer.genai")
    @patch("server.agents.vision_analyzer.HAS_GEMINI", True)
    def test_vision_analyzer_logs_analysis(self, mock_genai: MagicMock) -> None:
        """Test that vision analyzer logs analysis results."""
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model

        mock_response = MagicMock()
        mock_response.text = json.dumps({"description": "Test", "ui_elements": []})
        mock_model.generate_content.return_value = mock_response

        mock_genai.upload_file.return_value = MagicMock()

        analyzer = VisionAnalyzer(api_key="test-key")

        with patch.object(analyzer.logger, "info") as mock_log:
            result = analyzer.analyze_screenshot(image_path=str(self.test_image_path))

            self.assertTrue(result["ok"])
            # Check that logging occurred
            calls = [str(call) for call in mock_log.call_args_list]
            self.assertTrue(any("analyzed" in str(call) for call in calls))


if __name__ == "__main__":
    unittest.main()
