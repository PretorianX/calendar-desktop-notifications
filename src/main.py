#!/usr/bin/env python3
"""Main entry point for the Calendar Desktop Notifications application."""

import logging
import os
import sys
from typing import Callable, cast

# Add the parent directory to Python path to make 'src' package available
# This needs to be before importing from src
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from src.gui.tray_app import main as tray_main  # noqa: E402


def main() -> int:
    """Application main entry point."""
    try:
        cast(Callable[[], None], tray_main)()
    except KeyboardInterrupt:
        logging.info("Application terminated by user")
        return 0
    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
