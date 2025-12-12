"""
Chronomaly - A forecasting and anomaly detection library.
"""

import sys
from typing import Any, Optional
from pathlib import Path
from dotenv import load_dotenv

__version__ = "1.0.0"

# Global configuration state
_config = {
    "verbose": False,
}


def _exception_handler(
    exc_type: type, exc_value: BaseException, exc_traceback: Any
) -> None:
    """
    Custom exception handler that prints only the error message when verbose=False.

    When verbose mode is disabled, this handler suppresses the full traceback
    and displays only the exception type and message for cleaner output.

    Args:
        exc_type: The exception class.
        exc_value: The exception instance.
        exc_traceback: The traceback object.
    """
    if _config["verbose"]:
        # Use default behavior with full traceback
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
    else:
        # Print only the error message
        print(f"{exc_type.__name__}: {exc_value}")


def configure(
    env_file_path: Optional[str] = None,
    verbose: bool = False,
    **kwargs: Any,
) -> bool:
    """
    Configure the Chronomaly library.

    This function allows users to configure the library settings, including
    loading environment variables from a specified .env file path. The function
    is designed to be extensible for future configuration parameters.

    Args:
        env_file_path (str, optional): Path to the .env file. If None, searches for
            .env in the current directory and parent directories. If provided,
            loads environment variables from the specified path.
        verbose (bool): If True, show full exception tracebacks. If False (default),
            show only the error message for cleaner output.
        **kwargs: Reserved for future configuration parameters.

    Returns:
        bool: True if the .env file was found and loaded (if env_file_path was used),
              False otherwise.
    """
    env_loaded = False

    # Configure verbose mode
    _config["verbose"] = verbose
    sys.excepthook = _exception_handler

    # Configure environment variables
    if env_file_path:
        env_file = Path(env_file_path)
        if env_file.exists():
            env_loaded = load_dotenv(dotenv_path=env_file)
        else:
            env_loaded = False
    else:
        env_loaded = load_dotenv()

    return env_loaded
