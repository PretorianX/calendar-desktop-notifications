"""Configuration manager for the application."""

import os
from typing import Any, Dict

import appdirs
import yaml


class ConfigManager:
    """Manages application configuration."""

    DEFAULT_CONFIG: Dict[str, Any] = {
        "caldav": {"url": "", "username": "", "password": "", "calendar_name": ""},
        "sync": {"interval_minutes": 5, "sync_hours": 24},
        "notifications": {"intervals_minutes": [1, 5, 10], "sound_enabled": True},
        "auto_open_urls": True,
    }

    def __init__(self) -> None:
        """Initialize config manager."""
        self.app_name: str = "calendar-desktop-notifications"
        self.config_dir: str = appdirs.user_config_dir(self.app_name)
        self.config_file: str = os.path.join(self.config_dir, "config.yaml")
        self.config: Dict[str, Any] = self.DEFAULT_CONFIG.copy()
        self._load_config()

    def _ensure_config_dir(self) -> None:
        """Ensure config directory exists."""
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)

    def _load_config(self) -> None:
        """Load configuration from file."""
        self._ensure_config_dir()

        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as file:
                    loaded_config = yaml.safe_load(file)
                    if loaded_config and isinstance(loaded_config, dict):
                        # Update config with loaded values, preserving structure
                        self._update_dict(self.config, loaded_config)
            except (yaml.YAMLError, IOError) as e:
                print(f"Error loading config: {e}")

    def _update_dict(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """Recursively update dictionary with values from another dictionary."""
        for key, value in source.items():
            if (
                key in target
                and isinstance(target[key], dict)
                and isinstance(value, dict)
            ):
                self._update_dict(target[key], value)
            elif key in target:
                target[key] = value

    def save_config(self) -> None:
        """Save current configuration to file."""
        self._ensure_config_dir()

        try:
            with open(self.config_file, "w") as file:
                yaml.dump(self.config, file, default_flow_style=False)
        except IOError as e:
            print(f"Error saving config: {e}")

    def get_config(self) -> Dict[str, Any]:
        """Get the current configuration."""
        return self.config

    def update_config(self, new_config: Dict[str, Any]) -> None:
        """Update configuration with new values."""
        self._update_dict(self.config, new_config)
        self.save_config()
