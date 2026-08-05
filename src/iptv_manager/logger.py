"""
Logging module for IPTV tester.
"""

import logging
import os
from pathlib import Path
from datetime import datetime


class IPTVLogger:
    """Logger for IPTV tester."""

    def __init__(self, log_dir: str | Path = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "test.log"
        self._setup_logger()

    def _setup_logger(self) -> None:
        """Set up the logger."""
        self.logger = logging.getLogger("IPTVTester")
        self.logger.setLevel(logging.INFO)

        # Avoid adding multiple handlers if logger already has them
        if not self.logger.handlers:
            # File handler
            fh = logging.FileHandler(self.log_file, encoding='utf-8')
            fh.setLevel(logging.INFO)

            # Console handler (optional)
            ch = logging.StreamHandler()
            ch.setLevel(logging.INFO)

            # Formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            fh.setFormatter(formatter)
            ch.setFormatter(formatter)

            self.logger.addHandler(fh)
            self.logger.addHandler(ch)

    def log_test(self, channel_name: str, url: str, status: str, 
                 response_time: float, reason: str) -> None:
        """Log a single test result."""
        self.logger.info(
            f"CHANNEL: {channel_name} | URL: {url} | STATUS: {status} | "
            f"RESPONSE_TIME: {response_time:.2f}s | REASON: {reason}"
        )

    def info(self, message: str) -> None:
        """Log an info message."""
        self.logger.info(message)

    def warning(self, message: str) -> None:
        """Log a warning message."""
        self.logger.warning(message)

    def error(self, message: str) -> None:
        """Log an error message."""
        self.logger.error(message)