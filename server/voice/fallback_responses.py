#!/usr/bin/env python3
"""Fallback response generator when API is unavailable."""

from __future__ import annotations

from typing import Dict, Optional


class FallbackResponseManager:
    """Generates helpful fallback responses for API outages."""

    FALLBACK_RESPONSES: Dict[str, Dict[str, str]] = {
        "greeting": {
            "tr": "Merhaba! Şu anda Gemini API'ye erişilemiyor. Lütfen birkaç saniye sonra tekrar deneyin.",
            "en": "Hello! Gemini API is temporarily unavailable. Please try again in a few moments.",
        },
        "help": {
            "tr": "Yardım şu anda sağlanemiyor. API servisi zorluk yaşıyor. Lütfen birkaç saniye sonra deneyin.",
            "en": "Help is temporarily unavailable. The API service is experiencing issues. Please try again shortly.",
        },
        "generic": {
            "tr": "API servisi şu anda kullanılamıyor. Lütfen birkaç saniye sonra tekrar deneyin.",
            "en": "API service temporarily unavailable. Please try again shortly.",
        },
        "error": {
            "tr": "Bir hata oluştu. Lütfen bağlantınızı kontrol edin ve tekrar deneyin.",
            "en": "An error occurred. Please check your connection and try again.",
        },
        "timeout": {
            "tr": "İstek zaman aşımına uğradı. Lütfen tekrar deneyin.",
            "en": "Request timed out. Please try again.",
        },
        "circuit_breaker_open": {
            "tr": "Servis geçici olarak kapatılmıştır. Sistem kendisini kurtarmaya çalışıyor. Lütfen bekleyin.",
            "en": "Service is temporarily disabled. System is attempting recovery. Please wait.",
        },
    }

    KEYWORD_MAPPING = {
        # Turkish
        "merhaba": "greeting",
        "selam": "greeting",
        "alo": "greeting",
        "hi": "greeting",
        "hello": "greeting",
        "yardım": "help",
        "help": "help",
        "ne yapabilirim": "help",
        "what can i do": "help",
        "hata": "error",
        "error": "error",
        "zaman aşımı": "timeout",
        "timeout": "timeout",
        "circuit": "circuit_breaker_open",
    }

    @classmethod
    def get_response(cls, user_input: str, language: str = "en") -> str:
        """
        Generate appropriate fallback response based on user input.

        Args:
            user_input: Original user input
            language: Response language ('tr' for Turkish, 'en' for English)

        Returns:
            Helpful fallback response
        """
        text_lower = user_input.lower().strip()

        # Try to match keywords
        for keyword, response_type in cls.KEYWORD_MAPPING.items():
            if keyword in text_lower:
                responses = cls.FALLBACK_RESPONSES.get(response_type, {})
                return responses.get(language, cls.FALLBACK_RESPONSES["generic"][language])

        # Default response
        return cls.FALLBACK_RESPONSES["generic"][language]

    @classmethod
    def get_error_message(
        cls, error: Exception, language: str = "en", include_details: bool = False
    ) -> str:
        """
        Generate error message from exception.

        Args:
            error: Exception that occurred
            language: Response language
            include_details: Whether to include technical details

        Returns:
            User-friendly error message
        """
        error_str = str(error).lower()

        if "circuit" in error_str or "open" in error_str:
            base_msg = cls.FALLBACK_RESPONSES["circuit_breaker_open"][language]
        elif "timeout" in error_str:
            base_msg = cls.FALLBACK_RESPONSES["timeout"][language]
        else:
            base_msg = cls.FALLBACK_RESPONSES["error"][language]

        if include_details:
            technical_msg = f"\n[Technical: {type(error).__name__}: {str(error)[:100]}]"
            return base_msg + technical_msg

        return base_msg

    @classmethod
    def detect_language(cls, user_input: str) -> str:
        """
        Detect language from user input (simple heuristic).

        Args:
            user_input: User input text

        Returns:
            'tr' for Turkish, 'en' for English (default)
        """
        turkish_chars = set("çğıöşüÇĞİÖŞÜ")
        if any(char in user_input for char in turkish_chars):
            return "tr"
        return "en"
