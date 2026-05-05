"""Single responsibility: wire config, client, criteria, and executor into a single run() call."""

from plugin.config_loader import ConfigLoader
from plugin.deletion_executor import DeletionExecutor
from plugin.graphql_client import GraphQLClient


def run(payload: dict) -> dict:
    """
    Execute the plugin for the given StashApp payload.

    Reads server_connection and args from payload, loads config, runs the
    appropriate mode (dry_run only — delete raises NotImplementedError).

    Returns a dict with 'rules' (list) and 'summary' (str).
    """
    conn = payload["server_connection"]
    mode = payload.get("args", {}).get("mode", "dry_run")

    client = _build_client(conn)
    config = ConfigLoader(client, plugin_id="stash_deleter").load()

    executor = DeletionExecutor(client, deletion_scope=config["deletion_scope"])
    return executor.run_rules(rules=config["rules"], mode=mode)


def _build_client(conn: dict) -> GraphQLClient:
    """Construct a GraphQLClient from the server_connection block."""
    session_cookie = conn.get("SessionCookie", {})
    if isinstance(session_cookie, dict) and "Name" in session_cookie:
        # StashApp sends {"Name": "...", "Value": "..."}
        cookie_dict = {session_cookie["Name"]: session_cookie["Value"]}
    else:
        cookie_dict = session_cookie or {}

    return GraphQLClient(
        scheme=conn.get("Scheme", "http"),
        port=conn.get("Port", 9999),
        session_cookie=cookie_dict,
    )
