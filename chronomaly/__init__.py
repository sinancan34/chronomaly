"""
Chronomaly - A forecasting and anomaly detection library.
"""

from dotenv import load_dotenv

__version__ = "0.1.0"

# Load environment variables from .env file
# Searches for .env in current directory and parent directories
# Silently continues if .env file is not found
load_dotenv()
