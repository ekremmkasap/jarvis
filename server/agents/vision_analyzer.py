"""
Vision Analyzer - Gemini Vision API Integration
Analyzes screenshots and UI states using Gemini's multimodal capabilities
"""
from __future__ import annotations

import base64
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False


LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "vision_analyzer.log"


def _build_logger() -> logging.Logger:
    logger = logging.getLogger("agent.vision_analyzer")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not any(isinstance(handler, logging.FileHandler) and Path(handler.baseFilename) == LOG_FILE for handler in logger.handlers):
        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(file_handler)
    return logger


class VisionAnalyzer:
    """Analyzes images and screenshots using Gemini Vision API."""

    def __init__(self, api_key: Optional[str] = None, logger: logging.Logger | None = None) -> None:
        if not HAS_GEMINI:
            raise ImportError("google-generativeai is required. Install: pip install google-generativeai")

        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment or constructor")

        genai.configure(api_key=self.api_key)
        self.model_name = "gemini-2.0-flash-exp"
        self.model = genai.GenerativeModel(self.model_name)
        self.logger = logger or _build_logger()

        # Cache directory for analyzed results
        self.cache_dir = Path("server/logs/vision_analysis")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info("vision_analyzer_initialized model=%s", self.model_name)

    def analyze_screenshot(
        self,
        image_path: str | None = None,
        image_base64: str | None = None,
        image_bytes: bytes | None = None,
    ) -> dict[str, Any]:
        """
        Analyze a screenshot and extract comprehensive information.

        Args:
            image_path: Path to image file
            image_base64: Base64 encoded image data
            image_bytes: Raw image bytes

        Returns:
            Dictionary with analysis results including description, elements, and text
        """
        started_at = datetime.now(timezone.utc)

        try:
            # Load image data
            image_data = self._load_image_data(image_path, image_base64, image_bytes)
            if not image_data:
                raise ValueError("No valid image data provided")

            # Prepare analysis prompt
            analysis_prompt = """Analyze this screenshot comprehensively and provide:

1. **Overall Description**: Brief description of what you see in the screenshot
2. **UI Elements**: List all visible UI elements (buttons, text fields, menus, etc.) with their approximate positions
3. **Text Content**: Extract all readable text from the image
4. **Visual State**: Current state of the UI (e.g., loading, ready, error)
5. **Color Scheme**: Dominant colors and visual theme
6. **Potential Issues**: Any visual issues, errors, or warnings visible

Format your response as a structured JSON object."""

            # Call Gemini Vision API
            content = [analysis_prompt, image_data]
            response = self.model.generate_content(content)
            response_text = response.text if response else ""

            # Parse response
            analysis_result = self._parse_analysis_response(response_text)

            # Cache result
            cache_file = self.cache_dir / f"analysis_{datetime.now(timezone.utc).isoformat().replace(':', '-')}.json"
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(analysis_result, f, indent=2, ensure_ascii=False)

            output = {
                "ok": True,
                "started_at": started_at.isoformat(),
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "analysis": analysis_result,
                "cache_file": str(cache_file),
                "error": None,
            }

            self.logger.info("screenshot_analyzed successfully")
            return output

        except Exception as exc:
            self.logger.error("screenshot_analysis_failed error=%s", str(exc))
            return {
                "ok": False,
                "started_at": started_at.isoformat(),
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "analysis": None,
                "cache_file": None,
                "error": {
                    "type": exc.__class__.__name__,
                    "message": str(exc),
                },
            }

    def extract_text(
        self,
        image_path: str | None = None,
        image_base64: str | None = None,
        image_bytes: bytes | None = None,
    ) -> dict[str, Any]:
        """
        Extract text from image using OCR-style vision analysis.

        Args:
            image_path: Path to image file
            image_base64: Base64 encoded image data
            image_bytes: Raw image bytes

        Returns:
            Dictionary with extracted text and confidence
        """
        started_at = datetime.now(timezone.utc)

        try:
            image_data = self._load_image_data(image_path, image_base64, image_bytes)
            if not image_data:
                raise ValueError("No valid image data provided")

            extraction_prompt = """Extract ALL text visible in this image. Format as:

{
    "extracted_text": "raw text content",
    "text_blocks": [
        {"text": "block content", "confidence": 0.95, "location": "top-left/center/etc"},
        ...
    ],
    "languages_detected": ["en", "tr", ...],
    "total_words": 0
}"""

            content = [extraction_prompt, image_data]
            response = self.model.generate_content(content)
            response_text = response.text if response else ""

            # Parse JSON response
            try:
                # Try to extract JSON from response
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    text_result = json.loads(json_str)
                else:
                    text_result = {"extracted_text": response_text}
            except json.JSONDecodeError:
                text_result = {"extracted_text": response_text}

            output = {
                "ok": True,
                "started_at": started_at.isoformat(),
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "text_extraction": text_result,
                "error": None,
            }

            self.logger.info("text_extraction_completed")
            return output

        except Exception as exc:
            self.logger.error("text_extraction_failed error=%s", str(exc))
            return {
                "ok": False,
                "started_at": started_at.isoformat(),
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "text_extraction": None,
                "error": {
                    "type": exc.__class__.__name__,
                    "message": str(exc),
                },
            }

    def identify_ui_elements(
        self,
        image_path: str | None = None,
        image_base64: str | None = None,
        image_bytes: bytes | None = None,
    ) -> dict[str, Any]:
        """
        Identify and classify UI elements in screenshot.

        Args:
            image_path: Path to image file
            image_base64: Base64 encoded image data
            image_bytes: Raw image bytes

        Returns:
            Dictionary with identified UI elements and their properties
        """
        started_at = datetime.now(timezone.utc)

        try:
            image_data = self._load_image_data(image_path, image_base64, image_bytes)
            if not image_data:
                raise ValueError("No valid image data provided")

            elements_prompt = """Identify all UI elements in this screenshot. For each element, provide:

{
    "ui_elements": [
        {
            "type": "button|text_field|menu|image|link|form|etc",
            "label": "element label or text",
            "position": "estimated location (top-left, center, etc)",
            "state": "enabled|disabled|active|inactive|etc",
            "purpose": "what this element does",
            "color": "primary color or theme"
        },
        ...
    ],
    "ui_framework": "web|mobile|desktop|etc",
    "interaction_ready": true/false,
    "accessibility_issues": ["issue1", "issue2"]
}"""

            content = [elements_prompt, image_data]
            response = self.model.generate_content(content)
            response_text = response.text if response else ""

            # Parse response
            try:
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    ui_result = json.loads(json_str)
                else:
                    ui_result = {"ui_elements": [], "raw_response": response_text}
            except json.JSONDecodeError:
                ui_result = {"ui_elements": [], "raw_response": response_text}

            output = {
                "ok": True,
                "started_at": started_at.isoformat(),
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "ui_elements": ui_result,
                "error": None,
            }

            self.logger.info("ui_elements_identified count=%s", len(ui_result.get("ui_elements", [])))
            return output

        except Exception as exc:
            self.logger.error("ui_identification_failed error=%s", str(exc))
            return {
                "ok": False,
                "started_at": started_at.isoformat(),
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "ui_elements": None,
                "error": {
                    "type": exc.__class__.__name__,
                    "message": str(exc),
                },
            }

    def track_visual_state(
        self,
        image_path: str | None = None,
        image_base64: str | None = None,
        image_bytes: bytes | None = None,
        previous_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Track visual state changes in screenshot.

        Args:
            image_path: Path to image file
            image_base64: Base64 encoded image data
            image_bytes: Raw image bytes
            previous_state: Previous visual state for comparison

        Returns:
            Dictionary with current state and detected changes
        """
        started_at = datetime.now(timezone.utc)

        try:
            image_data = self._load_image_data(image_path, image_base64, image_bytes)
            if not image_data:
                raise ValueError("No valid image data provided")

            state_prompt = """Analyze the visual state of this screenshot. Provide:

{
    "current_state": {
        "page_status": "loading|ready|error|processing|etc",
        "modals_open": boolean,
        "notifications": ["notification1", "notification2"],
        "loading_indicators": true/false,
        "error_messages": ["error1", "error2"],
        "form_states": {
            "valid_fields": [],
            "invalid_fields": ["field1: error reason"]
        }
    },
    "detected_changes": ["change1", "change2"],
    "user_actions_available": ["action1", "action2"],
    "visual_flow": "description of UI flow or navigation state"
}"""

            previous_context = ""
            if previous_state:
                previous_context = f"\nPrevious state for comparison: {json.dumps(previous_state)}"

            content = [state_prompt + previous_context, image_data]
            response = self.model.generate_content(content)
            response_text = response.text if response else ""

            # Parse response
            try:
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    state_result = json.loads(json_str)
                else:
                    state_result = {"current_state": {}, "raw_response": response_text}
            except json.JSONDecodeError:
                state_result = {"current_state": {}, "raw_response": response_text}

            output = {
                "ok": True,
                "started_at": started_at.isoformat(),
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "state_tracking": state_result,
                "error": None,
            }

            self.logger.info("visual_state_tracked status=%s", state_result.get("current_state", {}).get("page_status"))
            return output

        except Exception as exc:
            self.logger.error("visual_state_tracking_failed error=%s", str(exc))
            return {
                "ok": False,
                "started_at": started_at.isoformat(),
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "state_tracking": None,
                "error": {
                    "type": exc.__class__.__name__,
                    "message": str(exc),
                },
            }

    def _load_image_data(
        self,
        image_path: str | None = None,
        image_base64: str | None = None,
        image_bytes: bytes | None = None,
    ) -> Any:
        """Load image data from various sources for Gemini API."""
        if image_path:
            # Load from file path
            if not Path(image_path).exists():
                raise FileNotFoundError(f"Image file not found: {image_path}")
            with open(image_path, "rb") as f:
                image_bytes = f.read()

        if image_bytes:
            # Convert bytes to base64
            image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        if not image_base64:
            return None

        # Determine MIME type based on extension or content
        mime_type = "image/png"
        if image_path:
            ext = Path(image_path).suffix.lower()
            mime_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".gif": "image/gif", ".webp": "image/webp"}
            mime_type = mime_types.get(ext, "image/png")

        # Return image data for Gemini API
        return genai.upload_file(data=base64.b64decode(image_base64), mime_type=mime_type) if HAS_GEMINI else None

    def _parse_analysis_response(self, response_text: str) -> dict[str, Any]:
        """Parse Gemini response into structured analysis data."""
        try:
            # Try to extract JSON from response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        # Fallback: return raw response structured
        return {
            "description": response_text,
            "ui_elements": [],
            "text_content": "",
            "visual_state": "unknown",
            "parsing_method": "fallback",
        }


def analyze_screenshot(
    image_path: str | None = None,
    image_base64: str | None = None,
    image_bytes: bytes | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Standalone function to analyze screenshot."""
    analyzer = VisionAnalyzer(api_key=api_key)
    return analyzer.analyze_screenshot(image_path=image_path, image_base64=image_base64, image_bytes=image_bytes)


def extract_text(
    image_path: str | None = None,
    image_base64: str | None = None,
    image_bytes: bytes | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Standalone function to extract text from image."""
    analyzer = VisionAnalyzer(api_key=api_key)
    return analyzer.extract_text(image_path=image_path, image_base64=image_base64, image_bytes=image_bytes)


def identify_ui_elements(
    image_path: str | None = None,
    image_base64: str | None = None,
    image_bytes: bytes | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Standalone function to identify UI elements."""
    analyzer = VisionAnalyzer(api_key=api_key)
    return analyzer.identify_ui_elements(image_path=image_path, image_base64=image_base64, image_bytes=image_bytes)


def track_visual_state(
    image_path: str | None = None,
    image_base64: str | None = None,
    image_bytes: bytes | None = None,
    previous_state: dict[str, Any] | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Standalone function to track visual state."""
    analyzer = VisionAnalyzer(api_key=api_key)
    return analyzer.track_visual_state(image_path=image_path, image_base64=image_base64, image_bytes=image_bytes, previous_state=previous_state)
