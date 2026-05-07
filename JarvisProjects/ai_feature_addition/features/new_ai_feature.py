import logging
from typing import List, Dict, Any, Optional

from ai_interface import AIInterface
from utils.helpers import generate_timestamp

class ContentTaggingFeature:
    """
    Implements the specific logic and workflows for the new AI content tagging feature.
    This module orchestrates the use of the AIInterface and helper utilities
    to deliver the new functionality.
    """
    _logger: logging.Logger
    _ai_interface: AIInterface

    def __init__(self, ai_interface: AIInterface) -> None:
        """
        Initializes the ContentTaggingFeature with an AIInterface instance.

        Args:
            ai_interface: An initialized instance of AIInterface to interact with the AI model.
        """
        self._logger = logging.getLogger(__name__)
        self._ai_interface = ai_interface
        self._logger.info("ContentTaggingFeature initialized.")

        # The AIInterface class has an attribute named _is_model_loaded, not a method is_model_loaded()
        if not self._ai_interface._is_model_loaded:
            self._logger.warning(
                f"[{generate_timestamp()}] AI model in AIInterface is not loaded. "
                "Content tagging predictions may fail."
            )

    def tag_content(self, content_text: str, num_tags: int = 5) -> List[str]:
        """
        Generates content tags for a given piece of text using the AI model.

        Args:
            content_text: The input text content to be tagged.
            num_tags: The desired number of tags to generate (positive integer).
                      The AI model might not strictly adhere to this number.

        Returns:
            A list of strings representing the generated tags.
            Returns an empty list if tagging fails, input is invalid, or no tags are generated.
        """
        if not content_text or not isinstance(content_text, str):
            self._logger.error(f"[{generate_timestamp()}] Invalid input: content_text must be a non-empty string.")
            return []
        
        if not isinstance(num_tags, int) or num_tags <= 0:
            self._logger.warning(f"[{generate_timestamp()}] Invalid num_tags: {num_tags}. Defaulting to 5.")
            num_tags = 5

        self._logger.info(f"[{generate_timestamp()}] Attempting to tag content of length {len(content_text)} "
                          f"with a request for {num_tags} tags.")

        try:
            # The AIInterface.predict method, as indicated by the error log from ai_interface.py,
            # expects a string as its primary input, not a dictionary.
            # It also appears to accept 'num_tags' as a keyword argument.
            # If the input type is incorrect (e.g., a dict), AIInterface.predict returns an error string,
            # which then causes the AttributeError in the subsequent .get() call.
            # We explicitly pass the content_text and num_tags directly and check the return type.
            raw_prediction_output: Any = self._ai_interface.predict(content_text, num_tags=num_tags)

            # Check if the output is not the expected dictionary structure
            if not isinstance(raw_prediction_output, dict):
                self._logger.error(
                    f"[{generate_timestamp()}] AI prediction returned an unexpected type "
                    f"({type(raw_prediction_output)}) instead of a dictionary. "
                    f"Raw output: {raw_prediction_output}"
                )
                return []
            
            # Now we are confident raw_prediction_output is a dict, so we can cast it.
            prediction_result: Dict[str, Any] = raw_prediction_output

            if not prediction_result:
                self._logger.error(f"[{generate_timestamp()}] AI prediction returned an empty result for content tagging.")
                return []

            if prediction_result.get("error"):
                error_message = prediction_result["error"]
                self._logger.error(f"[{generate_timestamp()}] AI prediction error: {error_message}")
                return []

            # Assuming the AI returns tags under a key like "tags" in a list format
            tags: List[str] = prediction_result.get("tags", [])

            if not isinstance(tags, list):
                self._logger.warning(
                    f"[{generate_timestamp()}] AI prediction did not return expected list of tags. "
                    f"Raw result: {prediction_result}"
                )
                return []

            if tags:
                self._logger.info(f"[{generate_timestamp()}] Successfully generated {len(tags)} tags: {tags}")
            else:
                self._logger.info(f"[{generate_timestamp()}] No tags generated for the content.")

            return tags

        except Exception as e:
            self._logger.exception(f"[{generate_timestamp()}] An unexpected error occurred during content tagging.")
            return []