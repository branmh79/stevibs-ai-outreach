from typing import Dict, Any

class BaseTool:
    """
    Base class for all agent tools.
    Enforces dict-in, dict-out interface and provides a place for validation and error handling.
    """

    def __call__(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entrypoint for the tool. Subclasses should override this method.
        """
        raise NotImplementedError("Tool must implement __call__ with dict-in, dict-out signature.")

    def validate_input(self, input_data: Dict[str, Any]) -> None:
        """
        Optional: Validate input data. Raise ValueError if invalid.
        """
        pass

    def handle_error(self, error: Exception) -> Dict[str, Any]:
        """
        Optional: Standardized error handling. Returns a dict with error info.
        """
        return {"success": False, "error": str(error)} 