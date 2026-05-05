"""
Unit tests for plugin/config_loader.py.

Verifies that GraphQL config is loaded, defaults applied, and invalid config rejected.
"""
from unittest.mock import MagicMock

import pytest

from plugin.config_loader import ConfigLoader

PLUGIN_ID = "stash_deleter"

FULL_RULES = [
    {
        "name": "stale",
        "label": "Stale and unrated",
        "enabled": True,
        "min_play_count": 3,
        "max_play_count": None,
        "require_no_rating": True,
        "require_no_o_counter": None,
        "days_on_disk_without_play": 90,
        "max_rating100": None,
    },
    {
        "name": "never_watched",
        "label": "Never watched",
        "enabled": False,
        "min_play_count": None,
        "max_play_count": 0,
        "require_no_rating": None,
        "require_no_o_counter": None,
        "days_on_disk_without_play": 180,
        "max_rating100": None,
    },
]


def _mock_client(plugin_config: dict) -> MagicMock:
    """Return a mock GraphQL client that returns plugin_config under configuration.plugins."""
    client = MagicMock()
    client.query.return_value = {
        "configuration": {"plugins": {PLUGIN_ID: plugin_config}}
    }
    return client


class TestConfigLoader:
    """Tests for ConfigLoader — GraphQL loading and validation."""

    def test_load_returns_deletion_scope_and_rules(self):
        """Happy path: full config is loaded, validated, and returned as-is."""
        plugin_cfg = {"deletion_scope": "with_file", "rules": FULL_RULES}
        client = _mock_client(plugin_cfg)
        loader = ConfigLoader(client, PLUGIN_ID)
        result = loader.load()
        assert result["deletion_scope"] == "with_file"
        assert result["rules"] == FULL_RULES

    def test_load_defaults_deletion_scope_to_db_only(self):
        """Missing deletion_scope key → default 'db_only'."""
        client = _mock_client({"rules": FULL_RULES})
        result = ConfigLoader(client, PLUGIN_ID).load()
        assert result["deletion_scope"] == "db_only"

    def test_load_defaults_rules_to_empty_list(self):
        """Missing rules key → default []."""
        client = _mock_client({"deletion_scope": "db_only"})
        result = ConfigLoader(client, PLUGIN_ID).load()
        assert result["rules"] == []

    def test_load_raises_on_invalid_deletion_scope(self):
        """deletion_scope with unsupported value must raise ValueError."""
        client = _mock_client({"deletion_scope": "nuke_everything", "rules": []})
        with pytest.raises(ValueError, match="deletion_scope"):
            ConfigLoader(client, PLUGIN_ID).load()

    def test_load_returns_all_rules_including_disabled(self):
        """load() returns ALL rules (enabled + disabled); caller filters enabled."""
        client = _mock_client({"deletion_scope": "db_only", "rules": FULL_RULES})
        result = ConfigLoader(client, PLUGIN_ID).load()
        assert len(result["rules"]) == 2
        disabled = [r for r in result["rules"] if not r["enabled"]]
        assert len(disabled) == 1

    def test_load_with_empty_plugin_config(self):
        """Plugin not yet configured (key absent) → returns defaults."""
        client = MagicMock()
        client.query.return_value = {
            "configuration": {"plugins": {}}
        }
        result = ConfigLoader(client, PLUGIN_ID).load()
        assert result["deletion_scope"] == "db_only"
        assert result["rules"] == []
