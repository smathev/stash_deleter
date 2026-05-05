"""Single responsibility: execute HTTP GraphQL requests against the StashApp API."""

import requests


class GraphQLClient:
    """Sends GraphQL queries and mutations to a StashApp instance."""

    def __init__(self, scheme: str, port: int, session_cookie: dict) -> None:
        pass

    def query(self, gql: str, variables: dict | None = None) -> dict:
        """Execute a read query; return the parsed JSON response data."""
        pass

    def mutate(self, gql: str, variables: dict | None = None) -> dict:
        """Execute a write mutation; return the parsed JSON response data."""
        pass
