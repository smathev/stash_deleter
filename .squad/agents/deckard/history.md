# Deckard — Project History

## Project Context
- **Project:** stash_deleter — StashApp plugin for auto-deleting scenes based on configurable criteria
- **Stack:** Python (exec interface), StashApp GraphQL API, YAML plugin config
- **User:** Smathev
- **Initialized:** 2026-05-05

## API Query Patterns (from Roy)

**2026-05-05:** Roy completed live GraphQL queries and documented corrected patterns in `.squad/agents/roy/LIVE_QUERY_RESULTS.md`. Key corrections:
- `o_counter` = orgasm counter (not play count)
- `play_count` = actual watch/view count ← use this for deletion criteria
- Filter gotchas documented: IS_NULL broken on timestamps, null handling in LESS_THAN
- 2,888 unrated scenes, 2,115 never-played in library
- Ready-to-use query patterns for common deletion scenarios

Ready to design query strategies using corrected field mappings.

## Learnings

### 2026-05-05T09:05:28+02:00 — Plugin Contract, Outside-in Boundary, Project Structure

#### Plugin Contract (from official StashApp docs)

**Files required:**
- `{pluginName}.yml` — plugin manifest, placed in StashApp's `plugins/` directory (default: `~/.stash/plugins/`)
- Entry point script(s) referenced by `exec` in the manifest

**Manifest structure (relevant fields for us):**
```yaml
name: Stash Deleter
description: Auto-delete scenes by configurable criteria
version: 0.1.0
exec:
  - python
  - "{pluginDir}/main.py"
interface: json
errLog: warning
tasks:
  - name: Dry Run — Find Deletion Candidates
    description: List scenes matching deletion criteria without deleting
    defaultArgs:
      mode: dry_run
  - name: Delete Scenes
    description: Delete scenes matching criteria (irreversible!)
    defaultArgs:
      mode: delete
```

**`interface` values:** `raw` | `json` | `cbor`  
We use `json` — StashApp writes JSON to our stdin, we write JSON to stdout.

**Stdin payload (from StashApp to plugin):**
```json
{
    "server_connection": {
        "Scheme": "http",
        "Port": 9999,
        "SessionCookie": {
            "Name": "session",
            "Value": "<cookie-value>",
            "Path": "",
            "Domain": "",
            "Expires": "0001-01-01T00:00:00Z",
            "RawExpires": "",
            "MaxAge": 0,
            "Secure": false,
            "HttpOnly": false,
            "SameSite": 0,
            "Raw": "",
            "Unparsed": null
        },
        "Dir": "<path to stash config directory>",
        "PluginDir": "<path to plugin config directory>"
    },
    "args": {
        "mode": "dry_run"
    }
}
```

**Stdout response (plugin to StashApp):**
```json
{
    "error": "<optional error string or null>",
    "output": "<anything — logged at debug level>"
}
```
- `error` present → logged at ERROR level in stash
- `output` → logged at DEBUG level
- Non-zero exit code is also treated as failure

**Hook types available:** `Scene.Create.Post`, `Scene.Update.Post`, `Scene.Destroy.Post` (and equivalents for Image, Gallery, Group, Performer, Studio, Tag).  
We do NOT need hooks — we are a manual task plugin.

**Plugin discovery:** Place `stash_deleter.yml` in `~/.stash/plugins/` (or wherever stash config lives). Click "Reload Plugins" in Settings > Plugins — no restart needed.

**`exec` array:** Forms the shell command. `{pluginDir}` is interpolated by StashApp to the directory of the manifest file. So `exec: [python, "{pluginDir}/main.py"]` calls `python ~/.stash/plugins/stash_deleter/main.py`.

**`defaultArgs`:** Merged into the `args` map at call time. Task-level args can be overridden when triggering the task.

---

#### Outside-in Boundary

**The seam:** StashApp spawns our Python process, pipes JSON to stdin, reads JSON from stdout. The contract is entirely at `main.py`'s stdin/stdout boundary.

**First failing test (pytest):**
```python
# tests/test_main.py
import json, subprocess, sys
from pathlib import Path

def test_plugin_responds_to_dry_run_payload_with_valid_output_shape():
    """
    GIVEN: StashApp invokes main.py with a valid server_connection JSON on stdin
    WHEN: args.mode = 'dry_run'
    THEN: stdout is valid JSON with an 'output' key; 'error' is absent or null
    """
    payload = {
        "server_connection": {
            "Scheme": "http",
            "Port": 9999,
            "SessionCookie": {"Name": "session", "Value": "test",
                              "Path": "", "Domain": "", "MaxAge": 0,
                              "Secure": False, "HttpOnly": False},
            "Dir": "/fake/stash",
            "PluginDir": str(Path(__file__).parent.parent)
        },
        "args": {"mode": "dry_run"}
    }
    result = subprocess.run(
        [sys.executable, "main.py"],
        input=json.dumps(payload),
        capture_output=True, text=True,
        cwd=Path(__file__).parent.parent
    )
    assert result.returncode == 0
    response = json.loads(result.stdout)
    assert "output" in response
    assert response.get("error") is None
```
This test FAILS until `main.py` exists and returns valid JSON — that's the red phase.

---

#### Proposed Project Structure

```
stash_deleter/
├── stash_deleter.yml          # Plugin manifest: StashApp discovery, exec, tasks
├── stash_deleter_config.yml   # User-facing deletion criteria (separate from manifest)
├── main.py                    # Entry point: read stdin JSON → orchestrate → write stdout JSON
├── plugin/
│   ├── __init__.py
│   ├── config_loader.py       # SRP: Load & validate stash_deleter_config.yml
│   ├── graphql_client.py      # SRP: HTTP GraphQL requests (Roy's domain)
│   ├── criteria_engine.py     # SRP: Translate config → filter params, evaluate candidates
│   └── deletion_executor.py   # SRP: Execute or dry-run scene deletion mutations
└── tests/
    ├── __init__.py
    ├── test_main.py            # Outside-in: stdin/stdout contract
    ├── test_config_loader.py
    ├── test_graphql_client.py
    ├── test_criteria_engine.py
    └── test_deletion_executor.py
```

#### Open Questions (as of 2026-05-05 — superseded by later decisions)

1. One task with `mode` arg vs. two separate tasks (`dry_run` task + `delete` task)?
2. What does `output` contain? Status string only, or structured list of candidates (scene IDs, titles, sizes)?
3. Where does `stash_deleter_config.yml` live? In PluginDir (alongside manifest) or configurable via an arg?
4. Does deletion call StashApp's `destroyScene` GraphQL mutation (which removes DB record), or does it also delete the file on disk? (These are separate operations in Stash.)
5. Authentication: use `SessionCookie` from `server_connection`, or API key? SessionCookie is cleaner — no config required.

---

## 2026-05-05T09:16:52+02:00 — Architecture Final: Manifest, Config, Output Contract, Dev Setup

### Work completed

Delivered all five architectural artifacts:

1. **`stash_deleter.yml`** — Definitive manifest. `exec` uses `{pluginDir}/venv/bin/python3` + `{pluginDir}/main.py`. Two tasks: "Dry Run" (mode: dry_run) and "Delete Scenes" (mode: delete). `interface: json`.

2. **`requirements.txt`** — Minimal: `requests`, `PyYAML`, `pytest`.

3. **`stash_deleter_config.yml`** — Sample config with all four criteria, `dry_run: true` default, `deletion_scope: db_only`, full comments marking required vs optional fields.

4. **`docs/SETUP.md`** — venv creation, pip install, dev symlink (`ln -s /home/smathev/git_dev/stash_deleter /mnt/stashForDevelop/config/plugins/stash_deleter`), plugin reload, test invocation.

5. **`docs/OUTPUT_CONTRACT.md`** — Full JSON shape for dry run success/empty, delete success/partial-failure/empty, and four error cases. Field reference table. Implementation notes for Rachael.

### Key findings

- **Dev plugins dir:** `/mnt/stashForDevelop/config/plugins/` (confirmed via filesystem walk of Docker mount at `/mnt/stashForDevelop/`)
- **Stash config root at mount:** `/mnt/stashForDevelop/config/`

### Decisions locked

- `exec` line: `["{pluginDir}/venv/bin/python3", "{pluginDir}/main.py"]`
- Config at `{PluginDir}/stash_deleter_config.yml`
- Criteria: OR semantics (any match = candidate)
- Output: `{output: {mode, candidates|deleted, failed, summary}, error}`
- `dry_run: true` is the default safety catch

---

## 2026-05-05T09:16:52+02:00 — Architecture Pivot: Config in Stash UI via settings: block

### Directive

smathev directed: all plugin configuration must be managed inside StashApp's UI.
No `stash_deleter_config.yml`. No post-install file editing.

### Research findings

Fetched and analysed:
- https://docs.stashapp.cc/in-app-manual/plugins/
- DupFileManager.yml and DupFileManager.py (community plugin, production use)
- stash-scheduler.yml and stash_scheduler.py (community plugin, production use)

**Confirmed capabilities:**

1. `settings:` block in manifest is real and supported. Types: BOOLEAN, NUMBER, STRING.
   Fields render in Settings > Plugins UI automatically.

2. Settings are NOT injected into stdin. Plugin must call:
   `configuration { plugins }` GraphQL query to read them.
   The `server_connection` in stdin provides auth (scheme, port, session cookie).

3. `ui.javascript` / `ui.css` exist for frontend injection — not needed.

4. No SELECT/dropdown type. STRING with documented valid values is the workaround.

### Decision

Option D: settings fields only. `stash_deleter_config.yml` is removed entirely.

### Artifacts delivered

1. **`docs/CONFIG_DESIGN.md`** — Full design: chosen approach, all fields with types,
   runtime flow, module impact table, open questions.

2. **`stash_deleter.yml`** — Updated with `settings:` block (7 fields: dry_run,
   deletion_scope, unrated_after_plays, low_rating_min_plays, low_rating_max_rating,
   no_orgasm_after_plays, never_played_after_days).

3. **`.squad/decisions/inbox/deckard-config-ui-decision.md`** — Decision record with
   StashApp capability summary and full impact analysis for Rachael.

### Key design point for Rachael

`ConfigLoader` must change signature from `(plugin_dir: Path)` to
`(graphql_client: GraphQLClient, plugin_id: str)`. The `stash_deleter_config.yml`
file is deleted. Tests for config_loader must mock the GraphQL response.

Criteria engine needs a guard: `0` for NUMBER fields = criterion disabled.

---

## 2026-05-05T09:27:26+02:00 — Dry Run UX: Tag-based output display

### Question from smathev

How can dry run results be presented to the user? Task log output is not readable for many scenes.

### Research

Fetched and analysed:
- https://docs.stashapp.cc/in-app-manual/plugins/ (official plugin docs, full page)
- Roy's LIVE_QUERY_RESULTS.md — Plugin Settings API section

**Key findings:**
1. `output` field → written at DEBUG log level. Invisible unless debug logging is explicitly enabled by the user.
2. **No notification/alert/popup system** exists for plugins — not documented anywhere.
3. `ui.assets` serves static files from plugin dir at `/plugin/{pluginID}/assets/` but Stash has no built-in markdown or HTML renderer.
4. `ui.javascript` can inject JS for custom UI — adds complexity, YAGNI for v1.
5. Tags are a first-class Stash concept. `sceneUpdate` mutation with `tag_ids` is confirmed working (Roy's session). `tagCreate` mutation also available.
6. DupFileManager has a `zzdryRun` BOOLEAN setting in its manifest — Roy confirmed this but the community scripts repo was inaccessible for detail on what it outputs.

### Decision

**Option E: Tag candidates** — plugin adds `stash-deleter:candidate` tag to each matching scene during dry run. User reviews in scene browser.

KISS: no new UI surface. YAGNI: Stash's scene browser is already the right tool. Reversible. Actionable.

### Output contract changes (dry run)

- Remove `candidates` array from output (was going to debug log, not useful there)
- Add: `candidate_count`, `total_size_bytes`, `candidate_tag`, `candidate_tag_id`
- Delete run: must call `clear_candidate_tags()` first to clean up stale tags

### Artifacts delivered

1. **`docs/DRY_RUN_OUTPUT.md`** — full design: UX flow, contract changes, Rachael's implementation checklist, GraphQL mutations needed.
2. **`.squad/decisions/inbox/deckard-dry-run-display.md`** — decision record for the team.

### Impact on Rachael

Three new methods in `deletion_executor.py`:
- `_ensure_candidate_tag()` — idempotent tag create
- `tag_candidates(scenes)` — add tag to each candidate (merge, don't overwrite)
- `clear_candidate_tags()` — clean up on delete run start

---

## 2026-05-05T09:27:26+02:00 — Dry Run UX Design: Candidate Shape + Output Presentation Options

### Work completed

Designed candidate data shape, assessed five output presentation options, recommended a primary approach.

### Candidate Scene Data Shape

Full schema:
```json
{
  "id": "42",
  "title": "...",
  "path": "/data/videos/scene.mp4",
  "size_bytes": 2147483648,
  "size_human": "2.00 GB",
  "duration_seconds": 3600.0,
  "play_count": 5,
  "o_counter": 0,
  "rating100": null,
  "last_played_at": "2025-06-01T12:00:00Z",
  "matched_criteria": ["no_orgasm_after_plays"],
  "reason": "Watched 5×, never rated, no orgasms"
}
```

Key design notes:
- `play_count` and `o_counter` are always separate fields (locked decision from Roy's corrections)
- `rating100: null` = unrated (not 0)
- `last_played_at: null` = never played
- `reason` is computed human-readable summary for job log / display

### Options Assessed

| Option | Summary | Verdict |
|---|---|---|
| 1: Job log | Format output as text table in Tasks log | Fallback |
| 2: Results file | Write .md/.json to PluginDir | Skip v0.1 |
| 3: JS injection | Modal via ui.javascript | Deferred (pending Roy) |
| 4: Tag candidates | Tag scenes with `stash_deleter:candidate` | **Primary** |
| 5: Toast/notification | Pop summary via notification mutation | Complement (pending Roy) |

### Decision

**Primary: Option 4 — tag all candidate scenes with `stash_deleter:candidate`.**

After dry run:
1. Remove tag from previously-tagged scenes (cleanup)
2. Tag all current candidates
3. User filters Scenes view by tag to review

Uses Stash's own UI, no frontend work, natural review-confirm workflow, reversible, self-documenting.

**Fallback: Option 1** — formatted text table in job log. Always available, zero extra work.

### Artifacts delivered

1. **`docs/DRY_RUN_UX.md`** — Full design: candidate schema, all five options with pros/cons, recommendation, architectural impact, open questions.
2. **`.squad/decisions/inbox/deckard-dry-run-ux-options.md`** — Decision record for team.

### Open questions waiting on Roy

- Does `createNotification` / toast mutation exist? (Option 5)
- What JS APIs are available in `ui.javascript` scope? (Option 3)
- Does `sceneUpdate` accept partial tag assignment or requires full list? (Option 4 impl)
- Are there permission guards on `tagCreate` / `sceneUpdate`? (Option 4 risk)

### Roy confirmed GraphQL patterns

Roy live-tested GraphQL Configuration query on sa.micro:
- `query Configuration { configuration { plugins } }` confirmed working
- Returns map: `plugin_id → settings_dict`
- Auth via SessionCookie from stdin `server_connection`
- Example: `{ "stash_deleter": { "dry_run": true, "deletion_scope": "db_only", ... } }`
- Plugin ID derived from YAML filename: `stash_deleter.yml` → key `"stash_deleter"`

---

## 2026-05-05T09:36:08+02:00 — Multi-Ruleset Architecture: JS Plugin Page in v1 Scope

### Directive

smathev reversed the "defer JS" decision. Multiple named rule sets are required in v1.
The flat `settings:` block cannot represent dynamic named rule sets — confirmed design
dead end. JS plugin page is now in scope.

### Work completed

Delivered all six tasks:

1. **Rule set data model** — JSON structure for `configuration.plugins["stash_deleter"]`:
   - Top-level: `deletion_scope` (string) + `rules` (array)
   - Per-rule: `name`, `label`, `enabled`, and up to six optional criteria fields
   - `name` becomes tag suffix: `stash-deleter:candidate:{name}`
   - `null` / absent criteria are ignored (no `0`-means-disabled ambiguity)

2. **JS component design** — `main.js` responsibilities:
   - `PluginApi.register.route("/stash_deleter", RulesetManager)`
   - RulesetManager: rules table, add/edit/delete modal, run buttons
   - Reads config via `configuration { plugins }` query
   - Saves via `configurePlugin(plugin_id: "stash_deleter", input: {...})`
   - Run buttons call `runPluginOperation`; results shown inline
   - Reference: DupFileManager pattern (confirmed working on dev instance by Roy)

3. **`config_loader.py` contract** — updated stub:
   - New signature: `ConfigLoader(graphql_client, plugin_id: str)`
   - Returns `{ deletion_scope, rules[] }` — flat criteria fields gone
   - Defaults: `deletion_scope = "db_only"`, `rules = []`

4. **`deletion_executor.py` contract** — updated stub:
   - New API: `run_rules(rules, mode)` iterates enabled rules
   - `clear_candidate_tags()` removes all `stash-deleter:candidate:*` before live run
   - `dry_run mode`: find candidates → tag with `stash-deleter:candidate:{name}`
   - `delete mode`: clear tags first → find candidates → delete

5. **`stash_deleter.yml`** — manifest updated:
   - Removed entire `settings:` block (7 flat fields gone)
   - Added `ui: javascript: [main.js]`
   - `exec`, `interface`, `tasks` unchanged

6. **Documentation and decisions**:
   - `docs/CONFIG_DESIGN.md` — fully rewritten for multi-ruleset architecture
   - `.squad/decisions/inbox/deckard-multi-ruleset-architecture.md` — decision record

### Key decisions locked

- Config format: `{ deletion_scope, rules[] }` — no flat criteria fields
- Tag pattern: `stash-deleter:candidate:{rule_name}` (one tag per rule per scene)
- JS in v1 scope: confirmed by smathev
- `clear_candidate_tags()` clears ALL candidate tags (wildcard pattern) before live delete
- Criteria fields: `null` = disabled (replaces `0` = disabled from flat-field era)
- Each rule produces an independent set of candidates and an independent tag

### Impact on Rachael

Full redesign of `config_loader.py` and `deletion_executor.py`. Stubs updated.
`criteria_engine.find_candidates(rule)` must accept a single rule dict.
New file: `main.js` (JS frontend — new scope, assign to appropriate agent).
Tests for config_loader must mock GraphQL returning rule array shape.


---

## 2026-05-05T07:36:08Z — Multi-Ruleset Architecture Final Approval & Team Coordination (Scribe Consolidation)

### Architecture Status: FULLY LOCKED

All team investigations completed and consolidated:

1. **Roy-1 findings** (plugin output display):
   - Confirms: `runPluginOperation` returns stdout JSON synchronously
   - Confirms: PluginApi.register.route("/stash_deleter") viable for custom page
   - Confirms: DupFileManager pattern works in production

2. **Roy-2 findings** (configurePlugin array storage):
   - APPROVED: `rules[]` native JSON array support confirmed
   - APPROVED: No serialization overhead; arrays round-trip cleanly
   - IMPLICATION: Multi-ruleset data model is feasible as designed

3. **Deckard-4** (dry run UX):
   - Recommendation: Tag-based candidate display (Option 4)
   - Rationale: Non-destructive, uses Stash's native UI, reversible

4. **Deckard-5** (multi-ruleset architecture):
   - Decision: JS plugin page for rule management
   - Data model: `{ deletion_scope, rules[] }` format
   - Tag pattern: `stash-deleter:candidate:{rule_name}`

### Ready for Implementation

- Manifest updated with `ui.javascript` block
- `config_loader` and `deletion_executor` stubs updated
- Integration points locked: GraphQL config fetch, tag operations, rule iteration
- JS component (`main.js`) assigned for next session
