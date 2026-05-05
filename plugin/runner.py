"""Single responsibility: wire config, client, criteria, and executor into a single run() call."""

from pathlib import Path


def run(payload: dict) -> dict:
    """
    Execute the plugin for the given StashApp payload.

    Returns a dict with 'candidates' (list) and 'summary' (str).
    Stub implementation: returns empty candidates for all modes.
    """
    return {
        "candidates": [],
        "summary": "Dry run: 0 candidates (stub)",
    }
