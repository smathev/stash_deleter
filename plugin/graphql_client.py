"""Single responsibility: execute HTTP GraphQL requests against the StashApp API."""

import json

import requests


class GraphQLError(Exception):
    """Raised when the GraphQL response contains an 'errors' field."""

    def __init__(self, errors: list) -> None:
        super().__init__(f"GraphQL errors: {errors}")
        self.errors = errors


class GraphQLClient:
    """Sends GraphQL queries and mutations to a StashApp instance."""

    def __init__(self, scheme: str, port: int, session_cookie: dict) -> None:
        self._base_url = f"{scheme}://localhost:{port}/graphql"
        self._session_cookie = session_cookie

    def query(self, gql: str, variables: dict | None = None) -> dict:
        """Execute a read query; return the parsed JSON response data."""
        return self._post(gql, variables)

    def mutate(self, gql: str, variables: dict | None = None) -> dict:
        """Execute a write mutation; return the parsed JSON response data."""
        return self._post(gql, variables)

    def _post(self, gql: str, variables: dict | None = None) -> dict:
        cookie_header = "; ".join(f"{k}={v}" for k, v in self._session_cookie.items())
        headers = {
            "Content-Type": "application/json",
            "Cookie": cookie_header,
        }
        body = json.dumps({"query": gql, "variables": variables or {}})
        response = requests.post(self._base_url, headers=headers, data=body)
        response.raise_for_status()
        payload = response.json()
        if "errors" in payload:
            raise GraphQLError(payload["errors"])
        return payload["data"]
