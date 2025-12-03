"""
Chronomaly - A forecasting and anomaly detection library.
"""

from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

__version__ = "1.0.0"


def configure(
    env_file_path: Optional[str] = None,
    # Add more configuration parameters here in the future
    **kwargs
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
    
    Examples:
        >>> import chronomaly
        >>> # Load from specific path
        >>> chronomaly.configure(env_file_path='/path/to/your/.env')
        
        >>> # Load from current directory
        >>> chronomaly.configure()
        
        >>> # Future: More configuration options can be added
        >>> # chronomaly.configure(env_file_path='/path/.env', other_param=value)
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
    
    # Future configuration parameters can be handled here
    # Example:
    # if 'some_param' in kwargs:
    #     handle_some_param(kwargs['some_param'])
    
    return env_loaded
