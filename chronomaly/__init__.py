"""
Chronomaly - A forecasting and anomaly detection library.
"""

from typing import Any, Optional
from pathlib import Path
from dotenv import load_dotenv

__version__ = "1.0.0"


def configure(
    env_file_path: Optional[str] = None,
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
        **kwargs: Reserved for future configuration parameters.

    Returns:
        bool: True if the .env file was found and loaded (if env_file_path was used),
              False otherwise.
    """
    env_loaded = False

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
