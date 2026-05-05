"""
Unit tests for plugin/graphql_client.py.

Verifies HTTP GraphQL requests, response parsing, and error handling.
"""
import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from plugin.graphql_client import GraphQLClient, GraphQLError

GQL = "{ __typename }"
SCHEME = "http"
PORT = 9999
SESSION_COOKIE = {"session": "abc123"}


def _make_response(data=None, errors=None, status_code=200):
    """Build a mock requests.Response."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    body = {}
    if data is not None:
        body["data"] = data
    if errors is not None:
        body["errors"] = errors
    mock_resp.json.return_value = body
    if status_code >= 400:
        mock_resp.raise_for_status.side_effect = requests.HTTPError(
            response=mock_resp
        )
    else:
        mock_resp.raise_for_status.return_value = None
    return mock_resp


class TestGraphQLClient:
    """Tests for GraphQLClient — query, mutation, and connection behaviour."""

    def test_builds_correct_url(self):
        """_base_url should be scheme://localhost:port/graphql."""
        client = GraphQLClient("https", 4242, {})
        assert client._base_url == "https://localhost:4242/graphql"

    def test_query_sends_post_with_json_body(self):
        """query() must POST with Content-Type: application/json and correct body shape."""
        mock_resp = _make_response(data={"scenes": []})
        with patch("requests.post", return_value=mock_resp) as mock_post:
            client = GraphQLClient(SCHEME, PORT, SESSION_COOKIE)
            client.query(GQL, {"page": 1})

            mock_post.assert_called_once()
            _, kwargs = mock_post.call_args
            assert kwargs["headers"]["Content-Type"] == "application/json"
            body = json.loads(kwargs["data"])
            assert body["query"] == GQL
            assert body["variables"] == {"page": 1}

    def test_query_sends_cookie_header(self):
        """session_cookie dict should be serialised as 'name=value' Cookie header."""
        mock_resp = _make_response(data={})
        cookies = {"session": "tok123", "user": "me"}
        with patch("requests.post", return_value=mock_resp) as mock_post:
            client = GraphQLClient(SCHEME, PORT, cookies)
            client.query(GQL)

            _, kwargs = mock_post.call_args
            cookie_header = kwargs["headers"]["Cookie"]
            assert "session=tok123" in cookie_header
            assert "user=me" in cookie_header

    def test_query_returns_data_on_success(self):
        """query() should return response['data'] on a 2xx response."""
        payload = {"findScenes": {"scenes": [], "count": 0}}
        mock_resp = _make_response(data=payload)
        with patch("requests.post", return_value=mock_resp):
            client = GraphQLClient(SCHEME, PORT, SESSION_COOKIE)
            result = client.query(GQL)
        assert result == payload

    def test_query_raises_graphql_error_on_errors_field(self):
        """query() must raise GraphQLError when the response contains an 'errors' key."""
        mock_resp = _make_response(errors=[{"message": "some error"}])
        with patch("requests.post", return_value=mock_resp):
            client = GraphQLClient(SCHEME, PORT, SESSION_COOKIE)
            with pytest.raises(GraphQLError):
                client.query(GQL)

    def test_query_raises_on_http_error(self):
        """query() must propagate requests.HTTPError on non-2xx HTTP status."""
        mock_resp = _make_response(status_code=500)
        with patch("requests.post", return_value=mock_resp):
            client = GraphQLClient(SCHEME, PORT, SESSION_COOKIE)
            with pytest.raises(requests.HTTPError):
                client.query(GQL)

    def test_mutate_uses_same_path_as_query(self):
        """mutate() should POST to the same _base_url as query()."""
        payload = {"tagCreate": {"id": "1"}}
        mock_resp = _make_response(data=payload)
        with patch("requests.post", return_value=mock_resp) as mock_post:
            client = GraphQLClient(SCHEME, PORT, SESSION_COOKIE)
            result = client.mutate(GQL)

        mock_post.assert_called_once_with(
            client._base_url, **mock_post.call_args[1]
        )
        assert result == payload
