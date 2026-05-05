# Rachael — Project History

## Project Context
- **Project:** stash_deleter — StashApp plugin for auto-deleting scenes based on configurable criteria
- **Stack:** Python 3, `requests` library, StashApp exec interface (stdin/stdout JSON)
- **User:** Smathev
- **Initialized:** 2026-05-05

## Plugin Interface Notes
- Plugin receives JSON on stdin: `{ "server_connection": { "Scheme", "Port", "SessionCookie", ... }, "args": {} }`
- Plugin writes JSON to stdout: `{ "output": "...", "error": "..." }`
- GraphQL endpoint constructed from server_connection: `{Scheme}://localhost:{Port}/graphql`

## Live Query Results from Roy

**2026-05-05:** Roy completed live GraphQL queries against https://sa.micro/graphql. Critical files for Python implementation:
- `.squad/agents/roy/LIVE_QUERY_RESULTS.md` — Full data dump with corrected field values, query patterns, filter behavior
- `.squad/agents/roy/API_SUMMARY.txt` — Quick reference (fields, endpoints, mutations, implementation strategy)

**Key Corrections for Python Implementation:**
- Use `play_count` (not `o_counter`) to check view count
- Use `is_missing: "rating"` to find unrated (null rating100)
- `last_played_at < X` includes null (never-played), so combine with `play_count: 0` if needed
- IS_NULL broken for timestamps; use LESS_THAN instead
- Scenes with `o_counter > 0` should be whitelisted (user engaged)

Ready to implement deletion criteria validator and sceneDestroy executor.

## Learnings
_Append new learnings below as work progresses._

---

## 2026-05-05T09:16:52+02:00 — Project Skeleton + TDD Bootstrap

### What Was Created

**Source files:**
- `main.py` — composition root; reads stdin JSON, calls `plugin.run()`, writes stdout JSON; all exception → error JSON; no business logic
- `plugin/__init__.py` — re-exports `run` from `plugin.runner`
- `plugin/runner.py` — single entry point; stubs `run()` returning empty candidates
- `plugin/config_loader.py` — stub `ConfigLoader` class ⚠️ **REDESIGNED (see config pivot below)**
- `plugin/graphql_client.py` — stub `GraphQLClient` class (query + mutate)
- `plugin/criteria_engine.py` — stub `CriteriaEngine` class (find_candidates + is_candidate)
- `plugin/deletion_executor.py` — stub `DeletionExecutor` class (execute)

**Test files:**
- `tests/__init__.py`
- `tests/test_main.py` — full outside-in boundary test suite (5 tests)
- `tests/test_config_loader.py` — stub class, no methods yet
- `tests/test_graphql_client.py` — stub class, no methods yet
- `tests/test_criteria_engine.py` — stub class, no methods yet
- `tests/test_deletion_executor.py` — stub class, no methods yet
- `tests/fixtures/sample_payload.json` — realistic StashApp stdin fixture

**Infra:**
- `venv/` — Python 3.14.4 venv with `pytest` + `requests`

### Test State (2026-05-05T09:16:52+02:00)

```
tests/test_main.py — 5 PASSED (GREEN)
  ✅ test_dry_run_returns_valid_json_with_output_key
  ✅ test_dry_run_output_has_candidates_and_summary
  ✅ test_delete_run_returns_valid_json
  ✅ test_malformed_stdin_returns_error_key
  ✅ test_missing_server_connection_returns_error

tests/test_config_loader.py    — 0 tests (stub class only)
tests/test_graphql_client.py   — 0 tests (stub class only)
tests/test_criteria_engine.py  — 0 tests (stub class only)
tests/test_deletion_executor.py — 0 tests (stub class only)
```

### Key Structural Decisions

1. **`plugin/__init__.py` imports `plugin.runner.run`** — main.py calls `plugin.run(payload)`, not an internal class. Single entry point, no coupling to internals.
2. **`plugin/runner.py` owns orchestration** — criteria_engine, config_loader, graphql_client, deletion_executor will be wired here. main.py stays pure I/O.
3. **`criteria_engine` never imports `graphql_client`** — client passed as argument (DIP). No `if dry_run:` outside `deletion_executor`.
4. **Stub `run()` returns `{"candidates": [], "summary": "Dry run: 0 candidates (stub)"}** — satisfies contract-shape tests without any real implementation.
5. **Error contract enforced**: invalid JSON → `{"output": null, "error": "..."}`, missing `server_connection` → same. Never crashes without JSON response.

---

## Implementation Notes for Future Work

### Module Responsibilities (SOLID SRP)

1. **`main.py`** — Pure I/O orchestrator. Read stdin, catch all exceptions, return JSON with `output` and `error` keys. No business logic.

2. **`plugin/runner.py`** — Composition root for business logic. Receives payload dict, orchestrates config_loader → criteria_engine → deletion_executor. Returns result dict for main.py to serialize.

3. **`plugin/config_loader.py`** — Fetch + validate user configuration. ⚠️ **NEW**: Takes `(graphql_client, plugin_id)` instead of `(plugin_dir)`. Calls GraphQL Configuration query. Applies in-code defaults. Returns validated config dict.

4. **`plugin/graphql_client.py`** — HTTP transport layer. Methods: `query(query_string) → response_dict`, `mutate(mutation_string) → response_dict`. Auth via SessionCookie from stdin. No retry logic (plugins timeout if slow).

5. **`plugin/criteria_engine.py`** — Pure function: config dict → (graphql_client) → candidates list. No coupling to config_loader or deletion_executor. Filter builder and scene evaluation.

6. **`plugin/deletion_executor.py`** — Execute or simulate deletions. Receives graphql_client (DIP). Respects `dry_run` flag. Returns deleted[] + failed[] + summary.

### Test Infrastructure

- `tests/fixtures/sample_payload.json` — realistic stdin with server_connection (scheme, port, cookie path) and args
- `pytest.ini` — standard config (or none, use defaults)
- No fixtures for StashApp GraphQL; mock with `unittest.mock.patch` or similar
- Aim for >90% code coverage; red → green → refactor cycle per module

### Key Design Patterns

- **DIP (Dependency Injection)**: graphql_client passed to criteria_engine, deletion_executor
- **No chained calls**: No `obj.method1().method2()` — breaks testability
- **Guard clauses**: Early returns for error cases
- **Output shape**: Always `{"output": {...}, "error": null}` or `{"output": null, "error": "..."}`

---

## 2026-05-05T09:16:52+02:00 — CONFIG PIVOT: File-based → In-app UI

### Directive Impact

**smathev:** All config must be in StashApp UI. NO YAML config file post-install.

### `config_loader.py` Redesign Required

**Old signature:** `ConfigLoader(plugin_dir: Path).load() -> dict`  
**New signature:** `ConfigLoader(graphql_client: GraphQLClient, plugin_id: str).load() -> dict`

**What changed:**
1. Constructor takes GraphQL client (DIP) instead of file path
2. `load()` calls `configuration { plugins }` query and extracts `plugins["stash_deleter"]`
3. Apply in-code defaults (no YAML file)
4. Validate `deletion_scope` string
5. Return same-shaped dict (rest of stack unchanged)

### `criteria_engine.py` Minor Change

Guard on NUMBER fields: `0` = "criterion disabled" → skip filter

### Test Changes

`tests/test_config_loader.py` — Rewrite. Mock GraphQL response instead of file I/O.

### Files Impacted

- ✅ `stash_deleter.yml` — now has `settings:` block (7 fields); no external config file
- 🗑️ `stash_deleter_config.yml` — DELETE (no longer used)
- ⚠️ `plugin/config_loader.py` — Redesign (GraphQL instead of file)
- ⚠️ `plugin/criteria_engine.py` — Add 0-check for NUMBER fields
- ⚠️ `main.py` — Pass graphql_client to ConfigLoader
- ⚠️ `tests/test_config_loader.py` — Rewrite (GraphQL mocks)

---

## 2026-05-05T09:44:24+02:00 — GraphQLClient + ConfigLoader Implementation (TDD)

### What Was Implemented

**`plugin/graphql_client.py`** — Full HTTP transport layer:
- `GraphQLError(Exception)` — custom exception with `.errors` attribute; raised when response contains `"errors"` key
- `GraphQLClient.__init__` — stores scheme, port, session_cookie; builds `_base_url = f"{scheme}://localhost:{port}/graphql"`
- `GraphQLClient.query` / `GraphQLClient.mutate` — both delegate to private `_post()` (no code duplication)
- `_post()` — serialises body as JSON string (not dict), sets `Content-Type: application/json`, builds `Cookie` header from dict as `k=v; k=v`, calls `raise_for_status()` before parsing, raises `GraphQLError` on `"errors"` key, returns `response["data"]`

**`plugin/config_loader.py`** — GraphQL config fetcher/validator:
- `ConfigLoader.__init__` — stores `_client` and `_plugin_id`
- `ConfigLoader.load()` — calls `{ configuration { plugins } }`, extracts `plugins.get(plugin_id, {})`, applies defaults (`"db_only"`, `[]`), validates scope, returns `{"deletion_scope": str, "rules": list}`
- Uses `or` defaulting for missing/falsy values; raises `ValueError` with clear message including field name

**`tests/test_graphql_client.py`** — 7 tests:
- `test_builds_correct_url`, `test_query_sends_post_with_json_body`, `test_query_sends_cookie_header`
- `test_query_returns_data_on_success`, `test_query_raises_graphql_error_on_errors_field`
- `test_query_raises_on_http_error`, `test_mutate_uses_same_path_as_query`

**`tests/test_config_loader.py`** — 6 tests:
- `test_load_returns_deletion_scope_and_rules`, `test_load_defaults_deletion_scope_to_db_only`
- `test_load_defaults_rules_to_empty_list`, `test_load_raises_on_invalid_deletion_scope`
- `test_load_returns_all_rules_including_disabled`, `test_load_with_empty_plugin_config`

### Test State (2026-05-05T09:44:24+02:00)

```
tests/test_main.py          — 5 PASSED (GREEN, unchanged)
tests/test_config_loader.py — 6 PASSED (GREEN, new)
tests/test_graphql_client.py — 7 PASSED (GREEN, new)
tests/test_criteria_engine.py — 32 PASSED (GREEN, unchanged)
Total: 50 passed
```

### Patterns Discovered / Decisions Made

1. **`query` and `mutate` share `_post()`** — DRY; both methods are one-liners delegating to `_post()`. Avoids future drift if HTTP logic changes.

2. **`json.dumps()` for body, not `json=` kwarg in requests** — The task spec and tests check `kwargs["data"]` (not `kwargs["json"]`), so body is manually serialised and passed as `data=`. This also makes the `Content-Type` header explicit.

3. **`raise_for_status()` before `.json()`** — Prevents `ValueError` on non-JSON error bodies (e.g. 502 HTML responses from proxies). HTTP error takes precedence.

4. **`or` defaulting pattern for config** — `raw.get("deletion_scope") or "db_only"` handles both missing key AND empty string in one expression. Consistent with KISS.

5. **`_VALID_SCOPES` as a module-level set** — Enables O(1) lookup and makes the constraint self-documenting without a comment.

6. **`ValueError` message includes field name** — `"Invalid deletion_scope ..."` so test can `match="deletion_scope"` and the error is immediately actionable.
