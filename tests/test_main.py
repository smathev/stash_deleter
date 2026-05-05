"""
Outside-in boundary tests for the stash_deleter plugin.

These tests verify the plugin contract: StashApp pipes JSON to stdin,
plugin responds with JSON on stdout. No internal logic is tested here.
"""
import json
import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).parent.parent


def _stash_payload(mode: str = "dry_run", plugin_dir: str | None = None) -> dict:
    """Build a realistic StashApp-style stdin payload."""
    return {
        "server_connection": {
            "Scheme": "http",
            "Port": 9999,
            "SessionCookie": {
                "Name": "session",
                "Value": "test-session-cookie",
                "Path": "",
                "Domain": "",
                "MaxAge": 0,
                "Secure": False,
                "HttpOnly": False,
                "SameSite": 0,
                "Expires": "0001-01-01T00:00:00Z",
                "Raw": "",
                "Unparsed": None,
            },
            "Dir": "/fake/stash",
            "PluginDir": str(plugin_dir or PLUGIN_ROOT),
        },
        "args": {"mode": mode},
    }


class TestPluginContract:
    """Tests the stdin/stdout JSON contract between StashApp and main.py."""

    def test_dry_run_returns_valid_json_with_output_key(self):
        """
        GIVEN a valid server_connection payload with mode=dry_run
        WHEN  main.py is invoked
        THEN  stdout is valid JSON, 'output' key is present, 'error' is null
        """
        result = subprocess.run(
            [sys.executable, "main.py"],
            input=json.dumps(_stash_payload("dry_run")),
            capture_output=True,
            text=True,
            cwd=PLUGIN_ROOT,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        response = json.loads(result.stdout)
        assert "output" in response
        assert response.get("error") is None

    def test_dry_run_output_has_candidates_and_summary(self):
        """
        GIVEN a valid dry_run payload
        THEN  output contains 'candidates' list and 'summary' string
        """
        result = subprocess.run(
            [sys.executable, "main.py"],
            input=json.dumps(_stash_payload("dry_run")),
            capture_output=True,
            text=True,
            cwd=PLUGIN_ROOT,
        )
        response = json.loads(result.stdout)
        output = response["output"]
        assert isinstance(output, dict), "output must be a dict"
        assert "candidates" in output, "output must have 'candidates' key"
        assert "summary" in output, "output must have 'summary' key"
        assert isinstance(output["candidates"], list)
        assert isinstance(output["summary"], str)

    def test_delete_run_returns_valid_json(self):
        """
        GIVEN a valid payload with mode=delete
        THEN  stdout is valid JSON with 'output' key
        """
        result = subprocess.run(
            [sys.executable, "main.py"],
            input=json.dumps(_stash_payload("delete")),
            capture_output=True,
            text=True,
            cwd=PLUGIN_ROOT,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        response = json.loads(result.stdout)
        assert "output" in response
        assert response.get("error") is None

    def test_malformed_stdin_returns_error_key(self):
        """
        GIVEN stdin contains invalid JSON
        THEN  stdout is still valid JSON with 'error' key set (never crash silently)
        """
        result = subprocess.run(
            [sys.executable, "main.py"],
            input="this-is-not-json",
            capture_output=True,
            text=True,
            cwd=PLUGIN_ROOT,
        )
        response = json.loads(result.stdout)
        assert response.get("error") is not None
        assert isinstance(response["error"], str)

    def test_missing_server_connection_returns_error(self):
        """
        GIVEN valid JSON but missing server_connection key
        THEN  returns error response, not a crash
        """
        result = subprocess.run(
            [sys.executable, "main.py"],
            input=json.dumps({"args": {"mode": "dry_run"}}),
            capture_output=True,
            text=True,
            cwd=PLUGIN_ROOT,
        )
        response = json.loads(result.stdout)
        assert response.get("error") is not None
