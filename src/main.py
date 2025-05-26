#!/usr/bin/env python3
"""Main entry point for the Calendar Desktop Notifications application."""

import logging
import os
import sys
from typing import NoReturn

# Add the parent directory to Python path to make 'src' package available
# This needs to be before importing from src
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from src.gui.tray_app import main as tray_main  # noqa: E402


def main() -> NoReturn:
    """Application main entry point."""
    try:
        tray_main()
    except KeyboardInterrupt:
        logging.info("Application terminated by user")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
