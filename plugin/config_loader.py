"""Single responsibility: load and validate plugin config from the StashApp GraphQL API."""

_VALID_SCOPES = {"db_only", "with_file"}

_CONFIG_QUERY = "{ configuration { plugins } }"


class ConfigLoader:
    """
    Fetches and validates the stash_deleter plugin configuration from the Stash API.

    Configuration is stored as a JSON object in configuration.plugins["stash_deleter"]
    via the configurePlugin mutation (managed by the JS frontend page). The flat
    settings: block is gone — all configuration lives in the rules array.

    Returned shape:
    {
        "deletion_scope": "db_only" | "with_file",
        "rules": [
            {
                "name": str,            # tag suffix: stash-deleter:candidate:{name}
                "label": str,           # human-readable display name
                "enabled": bool,
                "min_play_count": int | None,
                "max_play_count": int | None,
                "require_no_rating": bool | None,
                "require_no_o_counter": bool | None,
                "days_on_disk_without_play": int | None,
                "max_rating100": int | None,
            }
        ]
    }

    0/None for numeric criteria means the criterion is disabled.
    """

    def __init__(self, graphql_client, plugin_id: str) -> None:
        self._client = graphql_client
        self._plugin_id = plugin_id

    def load(self) -> dict:
        """
        Query configuration.plugins via the GraphQL client, extract plugin_id key,
        apply defaults, validate deletion_scope, and return the clean config dict.
        """
        data = self._client.query(_CONFIG_QUERY)
        raw = data["configuration"]["plugins"].get(self._plugin_id, {})

        deletion_scope = raw.get("deletion_scope") or "db_only"
        rules = raw.get("rules") or []

        if deletion_scope not in _VALID_SCOPES:
            raise ValueError(
                f"Invalid deletion_scope {deletion_scope!r}. "
                f"Must be one of: {sorted(_VALID_SCOPES)}"
            )

        return {"deletion_scope": deletion_scope, "rules": rules}
