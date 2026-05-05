# Configuration Design — Stash Deleter

**Status:** Active  
**Author:** Deckard (Lead)  
**Last updated:** 2026-05-05T09:36:08+02:00  
**Supersedes:** flat `settings:` block approach (2026-05-05T09:16:52+02:00)

---

## Architecture: JS plugin page + Python backend

The plugin has two components:

| Component | File | Responsibility |
|---|---|---|
| JS frontend | `main.js` | Renders rule-set management UI; reads/writes config via `configurePlugin` |
| Python backend | `main.py` | Executes `dry_run` / `delete` tasks; reads rule array from `configuration.plugins` |

The manifest exposes the JS page via:

```yaml
ui:
  javascript:
    - main.js
```

No `settings:` block. All configuration lives in the structured JSON rule array stored
by the JS UI through the `configurePlugin` GraphQL mutation.

> **Note:** The "defer JS" decision (2026-05-05T09:16:52+02:00) is **reversed**.
> smathev confirmed on 2026-05-05: build the JS plugin page in v1 scope.
> Reason: multiple named rule sets cannot be represented by the flat `settings:` block.

---

## Rule set data model

Configuration is stored in `configuration.plugins["stash_deleter"]` via `configurePlugin`.

```json
{
  "deletion_scope": "db_only",
  "rules": [
    {
      "name": "no_rating",
      "label": "Unrated after views",
      "enabled": true,
      "min_play_count": 4,
      "require_no_rating": true
    },
    {
      "name": "no_orgasm",
      "label": "Watched but no orgasm",
      "enabled": true,
      "min_play_count": 5,
      "require_no_o_counter": true
    },
    {
      "name": "unwatched",
      "label": "Never played after 30 days",
      "enabled": false,
      "days_on_disk_without_play": 30,
      "max_play_count": 0
    }
  ]
}
```

### Top-level fields

| Field | Type | Description |
|---|---|---|
| `deletion_scope` | `"db_only"` \| `"with_file"` | Controls whether file is deleted alongside DB record |
| `rules` | array | Ordered list of rule objects |

### Per-rule fields

| Field | Type | Required | Notes |
|---|---|---|---|
| `name` | string | yes | Slug used as tag suffix: `stash-deleter:candidate:{name}` |
| `label` | string | yes | Human-readable display name shown in UI table |
| `enabled` | boolean | yes | Disabled rules are skipped by the Python backend |
| `min_play_count` | number \| null | no | Minimum plays for rule to match |
| `max_play_count` | number \| null | no | Maximum plays (0 = never played) |
| `require_no_rating` | boolean \| null | no | True = scene must be unrated |
| `require_no_o_counter` | boolean \| null | no | True = o_counter must be 0 |
| `days_on_disk_without_play` | number \| null | no | Scene age in days with no play |
| `max_rating100` | number \| null | no | Rating must be ≤ this value (0–100 scale) |

`null` / absent criteria are ignored — only present non-null fields are applied.

---

## Tag pattern

Each rule produces a distinct tag on matching scenes:

```
stash-deleter:candidate:{rule_name}
```

Examples:
- `stash-deleter:candidate:no_rating`
- `stash-deleter:candidate:no_orgasm`
- `stash-deleter:candidate:unwatched`

`DeletionExecutor.clear_candidate_tags()` removes **all** `stash-deleter:candidate:*` tags
before a live delete run to clear stale state from previous dry runs.

---

## JS frontend responsibilities (`main.js`)

- Registers a React page: `PluginApi.register.route("/stash_deleter", RulesetManager)`
- `RulesetManager` component:
  - Reads current config from `{ configuration { plugins } }` on mount
  - Renders rules table (name, label, enabled toggle, criteria summary)
  - Add / Edit / Delete rule UI (modal or inline form)
  - Saves via `configurePlugin(plugin_id: "stash_deleter", input: {...})` mutation
  - "Dry Run (All Rules)" button → `runPluginOperation("stash_deleter", "dry_run")`
  - "Delete (All Rules)" button → `runPluginOperation("stash_deleter", "delete")`
  - Shows per-rule results inline after `runPluginOperation` returns

Reference implementation: DupFileManager (confirmed working on the dev instance by Roy).

---

## Python backend responsibilities

### `config_loader.py`

```python
ConfigLoader(graphql_client: GraphQLClient, plugin_id: str).load() -> dict
```

1. Query `configuration { plugins }` 
2. Extract `plugins["stash_deleter"]` (default: `{}`)
3. Apply defaults: `deletion_scope = "db_only"`, `rules = []`
4. Validate `deletion_scope` — fall back to `"db_only"` on invalid value
5. Return clean config dict with `deletion_scope` + `rules` array

### `runner.py`

Receives the full config dict from `ConfigLoader`. Filters to `enabled` rules only.
Passes enabled rules to `DeletionExecutor.run_rules(rules, mode)`.

### `deletion_executor.py`

```python
DeletionExecutor(client, deletion_scope: str)
  .run_rules(rules: list[dict], mode: str) -> dict
  .clear_candidate_tags() -> None
```

For **dry_run**: per rule → `criteria_engine.find_candidates(rule)` → tag scenes with
`stash-deleter:candidate:{rule.name}`.

For **delete**: `clear_candidate_tags()` first → per rule → find candidates → delete.

---

## How settings reach the backend at runtime

The plugin reads `configuration.plugins` via GraphQL, not stdin:

```python
gql_result = graphql_client.query("query { configuration { plugins } }")
raw_config = gql_result["configuration"]["plugins"].get("stash_deleter", {})
```

Auth: `server_connection` (scheme, port, session cookie) from stdin provides credentials.

---

## Module impact summary

| Module | Impact |
|---|---|
| `main.py` | Pass `graphql_client` + `plugin_id` to `ConfigLoader`; pass rules to `DeletionExecutor` |
| `plugin/config_loader.py` | New contract: returns `{deletion_scope, rules[]}` not flat fields |
| `plugin/criteria_engine.py` | Accept single rule dict; build filter per rule's criteria fields |
| `plugin/deletion_executor.py` | New contract: `run_rules(rules, mode)` iterates rules; `clear_candidate_tags()` clears all `stash-deleter:candidate:*` |
| `plugin/graphql_client.py` | No change |
| `stash_deleter.yml` | `settings:` block removed; `ui.javascript: [main.js]` added |
| `main.js` | **New file** — React UI for rule set management |
| `tests/` | Update to mock GraphQL returning rule array; add tests for multi-rule iteration |

---

## Decision: Option D — Manifest `settings:` fields only, no YAML file

### Rationale

StashApp's plugin manifest supports a `settings:` block that renders form fields directly
on the plugin's page in Settings > Plugins. This is confirmed in the official docs and
demonstrated by production community plugins (DupFileManager, stash-scheduler).

This approach:
- Fully satisfies smathev's directive: all configuration in the Stash UI, no file editing
- Eliminates `stash_deleter_config.yml` entirely
- Requires zero post-install setup from users
- Is the documented, supported pattern for Python task plugins in StashApp

Option B (custom JS frontend) is unnecessary overhead — the built-in `settings:` block
provides a settings page for free. Option C (hybrid with YAML override) contradicts the
directive. Both are rejected.

---

## What StashApp's `settings:` block actually supports

Confirmed from official documentation:

```yaml
settings:
  fieldName:
    displayName: Human Readable Label
    description: Optional description shown in UI
    type: BOOLEAN   # BOOLEAN | NUMBER | STRING only
```

**Supported field types:** `BOOLEAN`, `NUMBER`, `STRING` — no SELECT/dropdown.  
**No native date or list types.** Use `STRING` with documented format for those.

Settings defined here appear in Settings > Plugins on the plugin's page.  
Settings can also be set programmatically via the `configurePlugin` GraphQL mutation.

---

## How settings values reach the plugin at runtime

**Settings are NOT passed via stdin.** The stdin payload from StashApp only contains:

```json
{
    "server_connection": { "Scheme", "Port", "SessionCookie", "Dir", "PluginDir" },
    "args": { <defaultArgs only> }
}
```

The plugin must query the Stash API to retrieve settings:

```graphql
query Configuration {
  configuration {
    plugins
  }
}
```

`configuration.plugins` returns a map of `plugin_id → settings_dict`. The plugin ID
is the manifest filename without extension — `stash_deleter`.

Example at task startup:

```python
gql_result = graphql_client.query(CONFIGURATION_QUERY)
raw_settings = gql_result["configuration"]["plugins"].get("stash_deleter", {})
```

The `server_connection` in stdin (scheme, port, session cookie) provides everything
needed to authenticate and call this query. No separate credentials required.

---

## Fields exposed in the UI

| Internal name            | Display name                       | Type    | Default  | Notes                              |
|--------------------------|------------------------------------|---------|----------|------------------------------------|
| `dry_run`                | Dry Run Mode                       | BOOLEAN | `true`   | Safety default — must opt out      |
| `deletion_scope`         | Deletion Scope                     | STRING  | `db_only`| Valid: `db_only`, `with_file`      |
| `unrated_after_plays`    | Unrated After N Plays              | NUMBER  | `0`      | `0` = criterion disabled           |
| `low_rating_min_plays`   | Low-Rating: Min Plays              | NUMBER  | `3`      | Works with low_rating_max_rating   |
| `low_rating_max_rating`  | Low-Rating: Max Rating (0–100)     | NUMBER  | `30`     | Works with low_rating_min_plays    |
| `no_orgasm_after_plays`  | No Orgasm After N Plays            | NUMBER  | `0`      | `0` = criterion disabled           |
| `never_played_after_days`| Never Played Older Than N Days     | NUMBER  | `0`      | `0` = criterion disabled           |

**Disabled semantics for NUMBER criteria:** A value of `0` means the criterion is
inactive. This is documented in each field's `description` in the manifest.

**`deletion_scope` validation:** The plugin validates the STRING value at startup.
If invalid, it logs an error and falls back to `db_only`.

---

## What happens to `stash_deleter_config.yml`

**Removed.** The file is deleted from the repository and from the plugin directory.

No override mechanism. No hybrid. The UI is the only configuration surface.

---

## Manifest changes

Add a `settings:` block to `stash_deleter.yml`. See the manifest for the current
canonical form. No other manifest changes are needed — `exec`, `interface`, `tasks`
remain unchanged.

---

## Changes to `plugin/config_loader.py`

`ConfigLoader` must be redesigned. The new contract:

**Old (file-based):**
```python
ConfigLoader(plugin_dir: Path).load() -> dict
```

**New (API-based):**
```python
ConfigLoader(graphql_client: GraphQLClient, plugin_id: str).load() -> dict
```

Responsibilities:
1. Call `configuration { plugins }` via the injected `GraphQLClient`
2. Extract `plugins[plugin_id]` (default: `{}` if not found)
3. Apply defaults for any missing keys
4. Validate types and constrained values (`deletion_scope`)
5. Return a clean, validated config dict — same shape as before so downstream
   modules (`criteria_engine`, `deletion_executor`) are unaffected

**Defaults applied in code (replaces YAML defaults):**

```python
DEFAULTS = {
    "dry_run": True,
    "deletion_scope": "db_only",
    "unrated_after_plays": 0,
    "low_rating_min_plays": 3,
    "low_rating_max_rating": 30,
    "no_orgasm_after_plays": 0,
    "never_played_after_days": 0,
}
```

`criteria_engine.py` must treat `0` for NUMBER criteria as "criterion disabled" — it
should skip building a filter for any criterion with a threshold of `0`.

---

## Impact on other modules

| Module                   | Impact                                                          |
|--------------------------|-----------------------------------------------------------------|
| `main.py`                | Pass `graphql_client` to `ConfigLoader`; remove YAML path logic |
| `plugin/config_loader.py`| Full redesign — reads API, not file                             |
| `plugin/criteria_engine.py` | Add disabled-criterion guard (`if threshold == 0: skip`)    |
| `plugin/graphql_client.py` | Confirm `configuration { plugins }` query is available        |
| `plugin/deletion_executor.py` | No change                                                  |
| `tests/test_config_loader.py` | Rewrite — mock GraphQL response, not file I/O             |
| `stash_deleter.yml`      | Add `settings:` block                                          |
| `stash_deleter_config.yml` | **Deleted**                                                  |

---

## Open questions for implementation

1. Does `configuration.plugins` exist in the Stash GraphQL schema? Confirm via
   `graphql_client.py` introspection before Rachael implements `ConfigLoader`.
   (Evidence: stash-scheduler uses this query in production — strong confidence.)

2. What is the exact plugin ID Stash assigns? Assumption: manifest filename without
   `.yml` = `stash_deleter`. Verify against a live Stash instance.
