"""
Project Nexus

Logger
"""

import logging

from utils.settings import settings


logger = logging.getLogger("ProjectNexus")

logger.setLevel(settings.log_level)

formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

if not logger.handlers:
    logger.addHandler(console_handler)
