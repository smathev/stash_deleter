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

#### Open Questions (as of 2026-05-05)

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
