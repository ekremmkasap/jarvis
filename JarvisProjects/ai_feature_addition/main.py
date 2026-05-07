import logging
from typing import List

from utils.helpers import setup_logging
from ai_interface import AIInterface
from features.new_ai_feature import ContentTaggingFeature

# Configure logging for the main application
setup_logging(log_file_path="project.log", level=logging.INFO)
_logger = logging.getLogger(__name__)

def main() -> None:
    """
    The main entry point of the application.
    Initializes the AI interface, configures the content tagging feature,
    and demonstrates its usage.
    """
    _logger.info("Application started. Initializing AI components...")

    # 1. Initialize AIInterface
    try:
        ai_interface = AIInterface(model_identifier="text-tagger-v1.0")
        # The _is_model_loaded attribute is a boolean, not a method.
        # Access it directly to check if the model was loaded.
        if not ai_interface._is_model_loaded:
            _logger.warning("AI model was not successfully loaded. Content tagging may not function.")
    except Exception as e:
        _logger.critical(f"Failed to initialize AIInterface: {e}. Exiting application.", exc_info=True)
        return

    # 2. Initialize the New AI Feature (ContentTaggingFeature)
    try:
        content_tagging_feature = ContentTaggingFeature(ai_interface=ai_interface)
    except Exception as e:
        _logger.critical(f"Failed to initialize ContentTaggingFeature: {e}. Exiting application.", exc_info=True)
        return

    _logger.info("AI components initialized successfully. Demonstrating content tagging.")

    # 3. Demonstrate the new feature
    sample_texts = [
        "The quick brown fox jumps over the lazy dog.",
        "Quantum computing explores principles of quantum mechanics to solve complex problems.",
        "Recipe for a classic lasagna with béchamel sauce and fresh tomatoes.",
        "Latest news on the stock market performance and economic indicators.",
        "",  # Empty string for testing
        123  # Invalid input for testing
    ]

    for i, text in enumerate(sample_texts):
        _logger.info(f"\n--- Processing Sample Text {i+1} ---")
        _logger.info(f"Input text: '{text}'")
        try:
            tags: List[str] = content_tagging_feature.tag_content(content_text=str(text), num_tags=3) # Ensure text is string for tagging method
            if tags:
                _logger.info(f"Generated tags: {', '.join(tags)}")
            else:
                _logger.info("No tags generated or tagging failed for this content.")
        except Exception as e:
            _logger.error(f"An unexpected error occurred while tagging content '{text}': {e}", exc_info=True)

    _logger.info("Application finished demonstration.")

if __name__ == "__main__":
    main()