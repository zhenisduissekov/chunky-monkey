"""
utils.py

This module provides utility functions for the chunky-monkey project, including:

- Environment variable loading and validation
- Centralized logging setup (console and file)
- Hashing utilities for delta detection

All functions are designed to be imported and used by other modules in the project.
"""

from pathlib import Path

import logging
from logging.handlers import RotatingFileHandler

# Error logger for utils
def setup_utils_error_logger():
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("chunky-monkey.utils")
    logger.setLevel(logging.ERROR)
    if logger.hasHandlers():
        logger.handlers.clear()
    file_handler = RotatingFileHandler("logs/utils_errors.log", maxBytes=1_000_000, backupCount=3)
    file_formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    return logger

utils_error_logger = setup_utils_error_logger()

import os
import sys
import hashlib

from typing import Dict, Any, Optional

from dotenv import load_dotenv

import logging


# Optional: Use rich for pretty logs if available
try:
    from rich.logging import RichHandler
    RICH_AVAILABLE = True
except ImportError:
    class RichHandler:
        pass
    RICH_AVAILABLE = False

# --- Environment Variable Loader ---

REQUIRED_ENV_VARS = [
    "OPENAI_API_KEY",
    "ASSISTANT_ID",
    "KNOWLEDGE_BASE_API_URL",
]

OPTIONAL_ENV_VARS = {
    "LOG_LEVEL": "INFO",
    "KNOWLEDGE_BASE_PAGE_SIZE": "10",
}

def load_env(dotenv_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Loads environment variables from a .env file and validates required variables.
    Returns a dictionary of config values.
    """
    try:
        if dotenv_path is None:
            dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        load_dotenv(dotenv_path)

        config = {}
        missing = []
        for var in REQUIRED_ENV_VARS:
            value = os.getenv(var)
            if value is None or value.strip() == "":
                missing.append(var)
            else:
                config[var] = value

        for var, default in OPTIONAL_ENV_VARS.items():
            config[var] = os.getenv(var, default)

        if missing:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing)}. "
                f"Please set them in your .env file."
            )
        return config
    except Exception as e:
        utils_error_logger.error(f"Error loading environment variables: {e}", exc_info=True)
        raise

# --- Logging Setup ---

def setup_logging(log_level: str = "INFO", log_file: str = "logs/app.log") -> logging.Logger:
    """
    Sets up logging to both console and a rotating file.
    Returns a logger instance.
    """
    try:
        log_dir = Path(log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        logger = logging.getLogger("chunky-monkey")
        logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        logger.propagate = False  # Prevent double logging

        # Remove any existing handlers
        if logger.hasHandlers():
            logger.handlers.clear()

        # Console handler (Rich if available)
        if RICH_AVAILABLE:
            try:
                console_handler = RichHandler(rich_tracebacks=True, show_time=True, show_level=True, show_path=False)
            except Exception as e:
                utils_error_logger.error(f"Error setting up RichHandler: {e}", exc_info=True)
                console_handler = logging.StreamHandler(sys.stdout)
                console_formatter = logging.Formatter(
                    "[%(asctime)s] %(levelname)s %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S"
                )
                console_handler.setFormatter(console_formatter)
        else:
            console_handler = logging.StreamHandler(sys.stdout)
            console_formatter = logging.Formatter(
                "[%(asctime)s] %(levelname)s %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S"
            )
            console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # Rotating file handler
        file_handler = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=3)
        file_formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        return logger
    except Exception as e:
        utils_error_logger.error(f"Error setting up logger: {e}", exc_info=True)
        raise

# --- Hashing Utilities ---

def hash_content(content: str) -> str:
    """
    Returns a SHA-256 hash of the given string content.
    Used for delta detection (new/updated articles).
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def hash_file(file_path: str) -> str:
    """
    Returns a SHA-256 hash of the file's contents.
    """
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest()

# --- Example Usage (for testing) ---

if __name__ == "__main__":
    # Load environment variables and print config
    try:
        config = load_env()
        print("Loaded config:", config)
    except Exception as e:
        utils_error_logger.error(f"Error loading environment in __main__: {e}", exc_info=True)
        print("Error loading environment:", e)
        sys.exit(1)

    # Setup logger and log a test message
    try:
        logger = setup_logging(config.get("LOG_LEVEL", "INFO"))
        logger.info("Logger initialized successfully.")
    except Exception as e:
        utils_error_logger.error(f"Error setting up logger in __main__: {e}", exc_info=True)
        print("Error setting up logger:", e)
        sys.exit(1)

    # Test hashing
    sample = "Hello, chunky-monkey!"
    logger.info(f"Hash of sample content: {hash_content(sample)}")
