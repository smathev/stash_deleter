"""Single responsibility: orchestrate stdin → plugin → stdout for the StashApp exec interface."""

import json
import sys

import plugin


def main() -> None:
    """Read JSON from stdin, delegate to plugin.run(), write JSON to stdout."""
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        _write({"output": None, "error": f"Invalid JSON on stdin: {exc}"})
        return

    if "server_connection" not in payload:
        _write({"output": None, "error": "Missing required key: server_connection"})
        return

    try:
        result = plugin.run(payload)
        _write({"output": result, "error": None})
    except Exception as exc:  # noqa: BLE001
        _write({"output": None, "error": str(exc)})


def _write(response: dict) -> None:
    """Serialise response to stdout."""
    print(json.dumps(response))


if __name__ == "__main__":
    main()
