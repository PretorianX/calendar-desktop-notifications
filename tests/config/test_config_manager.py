"""Tests for the configuration manager."""

import os
import tempfile
from unittest import TestCase
from unittest.mock import mock_open, patch

import yaml

from src.config.config_manager import ConfigManager


class TestConfigManager(TestCase):
    """Tests for the ConfigManager class."""

    def setUp(self):
        """Set up test environment."""
        # Use patch to avoid modifying real config files during testing
        self.patcher = patch("src.config.config_manager.appdirs")
        self.mock_appdirs = self.patcher.start()

        # Create a temporary directory for config
        self.temp_dir = tempfile.mkdtemp()
        self.mock_appdirs.user_config_dir.return_value = self.temp_dir

        self.config_manager = ConfigManager()
        self.default_config = self.config_manager.DEFAULT_CONFIG.copy()

    def tearDown(self):
        """Clean up after tests."""
        self.patcher.stop()

        # Clean up the temporary directory if it exists
        if os.path.exists(self.temp_dir):
            for file in os.listdir(self.temp_dir):
                os.remove(os.path.join(self.temp_dir, file))
            os.rmdir(self.temp_dir)

    def test_default_config_includes_sync_hours(self):
        """Test that default config includes the sync_hours setting."""
        self.assertIn("sync", self.default_config)
        self.assertIn("sync_hours", self.default_config["sync"])
        self.assertEqual(24, self.default_config["sync"]["sync_hours"])

    def test_update_sync_hours(self):
        """Test updating the sync_hours setting."""
        new_config = {"sync": {"sync_hours": 48}}
        self.config_manager.update_config(new_config)

        config = self.config_manager.get_config()
        self.assertEqual(48, config["sync"]["sync_hours"])

    def test_default_config_is_not_mutated_when_updating(self):
        """Regression: DEFAULT_CONFIG must not be mutated by instance updates."""
        self.config_manager.update_config({"sync": {"sync_hours": 48}})

        # DEFAULT_CONFIG must remain pristine
        self.assertEqual(24, ConfigManager.DEFAULT_CONFIG["sync"]["sync_hours"])

        # Also ensure nested dicts aren't shared
        self.assertIsNot(
            self.config_manager.config["sync"], ConfigManager.DEFAULT_CONFIG["sync"]
        )

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists")
    def test_load_config_with_sync_hours(self, mock_exists, mock_file):
        """Test loading config with sync_hours from file."""
        # Setup mock to return True for config file existence
        mock_exists.return_value = True

        # Setup mock file content with updated sync_hours
        mock_yaml_data = {"sync": {"interval_minutes": 10, "sync_hours": 72}}
        mock_file.return_value.read.return_value = yaml.dump(mock_yaml_data)

        # Create a new instance to trigger loading from file
        with patch("yaml.safe_load", return_value=mock_yaml_data):
            config_manager = ConfigManager()
            config = config_manager.get_config()

            # Verify sync_hours was loaded correctly
            self.assertEqual(72, config["sync"]["sync_hours"])
