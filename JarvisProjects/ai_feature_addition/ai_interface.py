import logging
import time
from typing import Any, Dict, Optional

# Assuming utils is a package directly accessible from the project root.
# The `setup_logging` function will configure the root logger.
from utils.helpers import setup_logging

class AIInterface:
    """
    Provides an abstraction layer to interact with the core AI model(s).
    Handles model loading, basic inference, and input/output processing.
    It exposes a simple `predict` function for other modules to utilize
    the AI's capabilities without needing to know the underlying complexities.
    """
    _logger: logging.Logger
    _model_identifier: str
    _model: Optional[Any] = None  # Placeholder for a loaded AI model object
    _is_model_loaded: bool = False

    def __init__(self, model_identifier: str = "default_ai_model") -> None:
        """
        Initializes the AIInterface and attempts to load the specified AI model.

        Args:
            model_identifier: A string identifying the AI model to load.
                              This could be a model name, version, or a path.
        """
        self._logger = logging.getLogger(__name__)
        self._model_identifier = model_identifier
        self._logger.info(f"Initializing AIInterface for model: {self._model_identifier}")
        self._is_model_loaded = self._load_model()
        if not self._is_model_loaded:
            self._logger.error(f"Failed to load AI model '{self._model_identifier}' during initialization.")
            # Depending on project requirements, one might raise an exception here
            # if the AI model is absolutely critical for the application to run.
            # For robustness, we allow initialization to complete but mark the model as unloaded.

    def _load_model(self) -> bool:
        """
        Simulates the loading of an AI model.

        In a real application, this would involve loading model weights,
        setting up device configurations (CPU/GPU), initializing the model
        architecture, and performing initial checks.

        Returns:
            True if the model was successfully loaded, False otherwise.
        """
        self._logger.info(f"Attempting to load AI model: '{self._model_identifier}'...")
        try:
            # Simulate a time-consuming model loading process
            time.sleep(1) # E.g., loading model weights from disk or a remote server

            # In a real scenario, `self._model` would be an actual AI model object
            # (e.g., a TensorFlow model, PyTorch model, or an ONNX runtime session).
            # For this simulation, we use a string as a placeholder.
            self._model = f"SimulatedModelObject<{self._model_identifier}>"
            self._logger.info(f"Successfully loaded AI model: '{self._model_identifier}'")
            return True
        except Exception as e:
            self._logger.error(f"Error loading model '{self._model_identifier}': {e}", exc_info=True)
            self._model = None  # Ensure no partial or failed model is used
            return False

    def preprocess_input(self, raw_input: str) -> Dict[str, Any]:
        """
        Preprocesses raw input data into a format suitable for the AI model.

        This method typically handles tasks like tokenization, numericalization,
        resizing, normalization, or feature extraction, depending on the AI model type.

        Args:
            raw_input: The raw input string provided by the user or another system.

        Returns:
            A dictionary containing the processed input data ready for inference.
        """
        # Ensure raw_input is a string before attempting to slice it for logging
        if not isinstance(raw_input, str):
            self._logger.error(f"Expected raw_input to be a string during preprocessing, but got {type(raw_input)}")
            # Raise an error or handle as appropriate for invalid input type
            raise TypeError(f"Preprocessing received non-string input: {type(raw_input).__name__}")

        self._logger.debug(f"Preprocessing input (first 50 chars): '{raw_input[:50]}...'")
        # Simulate common text preprocessing steps
        cleaned_text = raw_input.strip().lower()
        processed_data = {
            "text_features": cleaned_text,
            "original_length": len(raw_input),
            "cleaned_length": len(cleaned_text)
        }
        self._logger.debug("Input preprocessing complete.")
        return processed_data

    def _run_inference(self, processed_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulates running inference on the loaded AI model with processed input.

        This is a private method as it directly interacts with the internal model
        and should be orchestrated by the public `predict` method.

        Args:
            processed_input: The input data already preprocessed and formatted
                             for the specific AI model.

        Returns:
            A dictionary containing the raw inference output from the model.
            This output is typically numerical (e.g., probabilities, embeddings, class IDs).

        Raises:
            RuntimeError: If the AI model is not loaded before inference is attempted.
        """
        if not self._is_model_loaded or self._model is None:
            self._logger.error("Attempted to run inference, but AI model is not loaded.")
            raise RuntimeError("AI model is not loaded. Cannot perform inference.")

        # Ensure 'text_features' exists and is a string before slicing for logging
        text_features = processed_input.get("text_features", "")
        if not isinstance(text_features, str):
            self._logger.error(f"Expected 'text_features' to be a string for inference, but got {type(text_features)}")
            raise TypeError(f"Inference received non-string 'text_features': {type(text_features).__name__}")

        self._logger.debug(f"Running inference with processed input (text features): '{text_features[:50]}...'")
        # Simulate AI model predicting
        time.sleep(0.3) # Simulate inference time, can vary based on model complexity

        # Example: Simple keyword-based classification simulation
        if "hello" in text_features or "hi" in text_features:
            raw_output = {"prediction_label": "greeting", "confidence_score": 0.98}
        elif "problem" in text_features or "issue" in text_features or "error" in text_features:
            raw_output = {"prediction_label": "customer_support_request", "confidence_score": 0.90}
        elif "thanks" in text_features or "thank you" in text_features:
            raw_output = {"prediction_label": "acknowledgement", "confidence_score": 0.85}
        else:
            raw_output = {"prediction_label": "general_inquiry", "confidence_score": 0.75}

        raw_output["model_version"] = self._model_identifier # Include model info in output
        self._logger.debug(f"Inference complete. Raw output: {raw_output}")
        return raw_output

    def postprocess_output(self, raw_output: Dict[str, Any]) -> str:
        """
        Postprocesses the raw output from the AI model into a user-friendly format.

        This method translates the model's raw output (e.g., class IDs, scores)
        into human-readable text, structured data, or a specific API response format.

        Args:
            raw_output: The raw output dictionary received directly from the AI model's inference.

        Returns:
            A human-readable string representing the AI's final response or action.
        """
        self._logger.debug(f"Postprocessing raw output: {raw_output}")
        prediction_label = raw_output.get("prediction_label", "unknown")
        confidence_score = raw_output.get("confidence_score", 0.0)
        model_version = raw_output.get("model_version", "N/A")

        # Simulate generating a natural language response based on the prediction
        if prediction_label == "greeting":
            response = f"Hello! I detected a greeting (confidence: {confidence_score:.2f}). How can I assist you today? (Model: {model_version})"
        elif prediction_label == "customer_support_request":
            response = (f"I understand you're reporting an issue (confidence: {confidence_score:.2f}). "
                        f"Please describe your problem in more detail, and I'll connect you to support if needed. (Model: {model_version})")
        elif prediction_label == "acknowledgement":
            response = f"You're welcome! I'm glad I could help. (Confidence: {confidence_score:.2f}, Model: {model_version})"
        else: # general_inquiry or unknown
            response = (f"I've processed your input. My current understanding points to a '{prediction_label}' "
                        f"(confidence: {confidence_score:.2f}). Could you elaborate? (Model: {model_version})")

        self._logger.debug("Output postprocessing complete.")
        return response

    def predict(self, raw_input: str) -> str:
        """
        Orchestrates the entire AI interaction process: preprocess, infer, postprocess.

        This is the primary public method for the new AI feature to utilize the AI's
        capabilities. It abstracts away all the internal complexities.

        Args:
            raw_input: The raw input string to be processed by the AI.

        Returns:
            A user-friendly string response from the AI.

        Raises:
            RuntimeError: If the AI model is not loaded or if any critical
                          error occurs during the inference pipeline.
        """
        # FIX: Ensure raw_input is a string before attempting to slice it.
        # The TypeError: unhashable type: 'slice' indicates that `raw_input`
        # was not a string, and its `__getitem__` method returned a slice object
        # which then caused an error when implicitly converted to string for logging.
        if not isinstance(raw_input, str):
            self._logger.error(f"Prediction received non-string input: {type(raw_input)}. Expected 'str'.")
            return f"Error: Invalid input type for AI prediction. Expected string, but received {type(raw_input).__name__}."

        # Safely slice and log the input preview
        log_input_preview = raw_input[:100]
        if len(raw_input) > 100:
            log_input_preview += '...'
        self._logger.info(f"Received prediction request for input: '{log_input_preview}'")


        if not self._is_model_loaded:
            self._logger.error("Prediction requested, but AI model is not loaded. Returning error message.")
            return "Error: AI system not ready. Model failed to load during initialization."

        try:
            # Step 1: Preprocess the raw input
            processed_input = self.preprocess_input(raw_input)

            # Step 2: Run inference on the processed input
            raw_inference_output = self._run_inference(processed_input)

            # Step 3: Postprocess the raw inference output into a final response
            final_response = self.postprocess_output(raw_inference_output)

            self._logger.info("Prediction successful.")
            return final_response
        except RuntimeError as e:
            self._logger.error(f"Prediction failed due to an AI interface runtime error: {e}", exc_info=True)
            return f"Error during AI prediction: {e}. Please check the logs."
        except TypeError as e: # Catch TypeErrors explicitly, especially for input validation issues
            self._logger.error(f"Prediction failed due to invalid input type: {e}", exc_info=True)
            return f"Error during AI prediction: Invalid input type. {e}. Please check the logs."
        except Exception as e:
            self._logger.error(f"An unexpected error occurred during AI prediction: {e}", exc_info=True)
            return f"An unexpected error occurred during AI prediction: {e}. Please contact support."

# Entry point for testing the module's functionality in isolation.
if __name__ == "__main__":
    # Configure logging specifically for this module's standalone execution.
    # In a full project, main.py would typically call setup_logging once.
    setup_logging(log_file_path="ai_interface_test.log", level=logging.DEBUG)
    module_logger = logging.getLogger(__name__)
    module_logger.info("Starting AIInterface standalone test execution.")

    # Initialize AIInterface with a specific model identifier
    # This simulates loading a "sentiment_analyzer_v1" model
    ai_connector = AIInterface(model_identifier="sentiment_analyzer_v1")

    # Test cases for demonstration
    test_inputs = [
        "Hello there, AI system! How are you doing today?",
        "I have a big problem with my computer. It keeps crashing.",
        "This is just a general statement about something, not really a question.",
        "There's an error in the system report, and I can't figure it out.",
        "Good morning!",
        "Thank you for your help, I really appreciate it."
    ]

    print("\n--- AI Interface Test Results ---")
    for i, user_input in enumerate(test_inputs):
        module_logger.info(f"\n--- Test Case {i+1} ---")
        module_logger.info(f"User Input: '{user_input}'")

        ai_response = ai_connector.predict(user_input)

        module_logger.info(f"AI Response: '{ai_response}'")
        print(f"User Input ({i+1}): '{user_input}'")
        print(f"AI Response ({i+1}): '{ai_response}'\n")

    # Add a test case for invalid input type
    module_logger.info("\n--- Test Case for Invalid Input Type ---")
    invalid_input = ["This is a list, not a string", "and should cause an error"] # A list, not a string
    module_logger.info(f"User Input (Invalid): '{invalid_input}' (type: {type(invalid_input)})")
    ai_response_invalid = ai_connector.predict(invalid_input)
    module_logger.info(f"AI Response (Invalid): '{ai_response_invalid}'")
    print(f"User Input (Invalid): '{invalid_input}'")
    print(f"AI Response (Invalid): '{ai_response_invalid}'\n")

    # Demonstrate a scenario where model loading might fail (if it were implemented to fail)
    # For this simulation, _load_model always succeeds.
    # To truly test failure, one would modify _load_model to sometimes return False.
    # For example:
    # class AIInterfaceFail(AIInterface):
    #     def _load_model(self) -> bool:
    #         self._logger.error("Simulating model loading failure!")
    #         return False
    # failed_ai_connector = AIInterfaceFail("broken_model")
    # print("\n--- Testing Model Failure Scenario ---")
    # print(f"User Input: 'Test input for broken model'")
    # print(f"AI Response: '{failed_ai_connector.predict('Test input for broken model')}'\n")


    module_logger.info("AIInterface standalone test finished.")