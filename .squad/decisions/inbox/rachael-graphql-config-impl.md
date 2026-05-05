# Implementation Decisions — graphql_client + config_loader

**Author:** Rachael  
**Date:** 2026-05-05T09:44:24+02:00  
**Status:** Implemented (50/50 tests GREEN)

---

## Decision 1: `query` and `mutate` are thin wrappers over `_post()`

**Context:** Both methods share identical HTTP logic (same URL, headers, body shape, error handling).

**Decision:** Extract a private `_post(gql, variables)` method. `query()` and `mutate()` each call `_post()` as a one-liner.

**Rationale:** DRY — any future change to the HTTP layer (retry logic, timeout, logging) has one place to change. OCP — extend `_post` without touching the public interface.

**Alternative rejected:** Duplicating the body in both methods — would create silent drift risk.

---

## Decision 2: Use `data=json.dumps(body)` not `json=body` in `requests.post`

**Context:** `requests` supports both `data=` (raw string) and `json=` (auto-serialised dict + Content-Type).

**Decision:** Manually serialise with `json.dumps()` and pass as `data=`, set `Content-Type` explicitly.

**Rationale:** Tests assert on `kwargs["data"]` (a string). Explicit serialisation makes the Content-Type header owner clear. Also avoids any quirks with `json=` when `requests` decides the encoding.

---

## Decision 3: `raise_for_status()` before `response.json()`

**Context:** Non-2xx responses may return non-JSON bodies (HTML from proxies, NGINX 502 pages, etc.).

**Decision:** Call `response.raise_for_status()` first. `requests.HTTPError` is raised before any attempt to parse JSON.

**Rationale:** Prevents `json.JSONDecodeError` masking the real HTTP error. Keeps error hierarchy clean: HTTP transport errors are not GraphQL errors.

---

## Decision 4: `GraphQLError` lives in `graphql_client.py`, importable as `from plugin.graphql_client import GraphQLError`

**Context:** The error is tightly coupled to the HTTP transport layer.

**Decision:** Define `GraphQLError(Exception)` in `graphql_client.py` with a `.errors` attribute containing the raw errors list.

**Rationale:** Callers that want to inspect the errors list can do so. The exception belongs to the same responsibility boundary as the client. No separate `exceptions.py` needed (YAGNI).

---

## Decision 5: `or` defaulting in `ConfigLoader.load()`

**Context:** `deletion_scope` can be absent, `None`, or an empty string — all should default to `"db_only"`.

**Decision:** Use `raw.get("deletion_scope") or "db_only"`.

**Rationale:** Single expression handles all falsy cases. `dict.get()` returns `None` for missing keys; `or` catches `None`, `""`, and `0` in one shot. KISS.

---

## Decision 6: `_VALID_SCOPES` as a module-level frozenset equivalent

**Context:** Two valid values for `deletion_scope`: `"db_only"` and `"with_file"`.

**Decision:** Module-level `_VALID_SCOPES = {"db_only", "with_file"}`. Validation: `if deletion_scope not in _VALID_SCOPES: raise ValueError(...)`.

**Rationale:** O(1) lookup. Self-documenting — the set IS the documentation of valid values. Adding a new scope is a one-line change to the set. `ValueError` message includes the field name for immediate actionability in logs.

---

## Decision 7: `ConfigLoader.load()` returns ALL rules (caller filters enabled)

**Context:** Should `load()` pre-filter to only enabled rules?

**Decision:** Return all rules. Caller (runner.py / criteria_engine.py) filters by `rule["enabled"]`.

**Rationale:** SRP — config loading ≠ rule selection. Tests explicitly verify that disabled rules are included in the returned list. This makes config inspection possible without re-fetching.
