"""Single responsibility: load and validate the YAML config from PluginDir."""

from pathlib import Path


class ConfigLoader:
    """Loads and validates stash_deleter_config.yml from the plugin directory."""

    def __init__(self, plugin_dir: Path) -> None:
        pass

    def load(self) -> dict:
        """Return the validated config as a plain dict."""
        pass
