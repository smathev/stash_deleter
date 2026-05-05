# Decisions

## Archive

### 2026-05-05 - deckard-dry-run-display

# Decision: Dry Run Output Display

**Author:** Deckard (Lead)  
**Date:** 2026-05-05T09:27:26+02:00  
**Status:** DECIDED — awaiting implementation by Rachael  
**Triggered by:** smathev question — how to present dry run results to the user

---

## Context

The current output contract writes `output` (including a `candidates` array) to stdout, which Stash logs at **DEBUG level**. This is invisible to users unless they have debug logging enabled, and even then it's not browsable. For a dry run that may match dozens or hundreds of scenes, a log entry is not readable or actionable.

StashApp plugin capabilities investigated:
- `output` field → DEBUG log only. Not user-visible by default.
- No plugin notification/alert/popup API exists.
- `ui.assets` can serve files from plugin dir but Stash has no markdown renderer.
- `ui.javascript` can inject JS/DOM but adds significant complexity.
- GraphQL mutations allow tagging scenes — fully supported.
- Tags render in the standard scene browser UI immediately.

---

## Decision

**Option E: Tag candidates using a Stash tag.**

When dry run executes, the plugin adds a `stash-deleter:candidate` tag to every matching scene via `sceneUpdate` mutation. The user reviews candidates using Stash's own scene browser filtered by that tag.

---

## Rationale

| Criterion | Verdict |
|-----------|---------|
| KISS | ✅ Uses existing Stash infrastructure, no new surface |
| YAGNI | ✅ Scene browser already does everything needed |
| Actionable | ✅ User can inspect, preview, un-tag individual scenes |
| Reversible | ✅ Remove tag to undo dry run artefact |
| v1 scope | ✅ Minimal implementation — tag create + scene update |

---

## Impact

See `docs/DRY_RUN_OUTPUT.md` for full UX flow, output contract changes, and Rachael's implementation checklist.

**Output contract changes (summary):**
- `candidates` array removed from dry run output
- Added: `candidate_count`, `total_size_bytes`, `candidate_tag`, `candidate_tag_id`
- Delete run must call `clear_candidate_tags()` before proceeding

**Rachael's new responsibilities:**
- `_ensure_candidate_tag()` — create tag if not exists
- `tag_candidates(scenes)` — add tag to each candidate (preserving existing tags)
- `clear_candidate_tags()` — remove tag from all tagged scenes on delete run

---

### 2026-05-05 - deckard-dry-run-ux-options

# Decision: Dry Run UX — Output Presentation

**Date:** 2026-05-05T09:27:26+02:00  
**Author:** Deckard (Lead)  
**Status:** RECOMMENDATION — pending Roy's API findings for Options 3 and 5

---

## Context

After a dry run, the user needs to see which scenes would be deleted. Currently `output` goes to StashApp's DEBUG-level job log — not user-friendly and not visible by default. The user wants results visible **inside StashApp**.

---

## Candidate Data Shape

Each candidate scene will carry these fields in the JSON output:

```json
{
  "id": "42",
  "title": "Scene Title",
  "path": "/data/videos/scene.mp4",
  "size_bytes": 2147483648,
  "size_human": "2.00 GB",
  "duration_seconds": 3600.0,
  "play_count": 5,
  "o_counter": 0,
  "rating100": null,
  "last_played_at": "2025-06-01T12:00:00Z",
  "matched_criteria": ["no_orgasm_after_plays", "unrated_after_plays"],
  "reason": "Watched 5×, never rated, no orgasms"
}
```

This is an enrichment of the existing contract shape in `docs/OUTPUT_CONTRACT.md`. Rachael should update the contract to match this shape.

---

## Recommendation

### Primary: Option 4 — Tag Candidates with `stash_deleter:candidate`

After each dry run:
1. Remove `stash_deleter:candidate` tag from all previously-tagged scenes (cleanup)
2. Assign `stash_deleter:candidate` tag to all current candidates
3. Return normal structured output

**User workflow:** Go to Scenes → filter by `stash_deleter:candidate` tag → review in native Stash UI.

**Why this is the right call:**
- Stash-native: no JS, no frontend work, no file system navigation
- The user already knows how to filter by tag in the Scenes view
- Persistent across sessions — user can take time to review
- Reversible — user can remove the tag from scenes they want to keep
- Self-cleaning — each dry run replaces the tag list
- Aligns with KISS and YAGNI
- Requires only GraphQL mutations that are already in scope for deletion

### Fallback: Option 1 — Formatted Job Log

Format the `output` field as a readable text table. Always available, zero extra work. Activate if Option 4 hits permission or mutation issues.

---

## Options Not Recommended for v0.1

| Option | Reason deferred |
|---|---|
| Option 2: Results file | Not "in Stash" — requires filesystem navigation |
| Option 3: JS injection | Requires JS dev, pending Roy's findings on available APIs |
| Option 5: Toast/notification | Pending Roy's API findings; summary-only even if confirmed |

---

## Required Implementation Changes

| Component | Change |
|---|---|
| `graphql_client.py` | Add `find_or_create_tag(name)`, `assign_tag_to_scenes(tag_id, scene_ids)`, `remove_tag_from_scenes(tag_id, scene_ids)` |
| `criteria_engine.py` | After building candidates, call tag assignment operations |
| `deletion_executor.py` | After deletion, remove `stash_deleter:candidate` tag from deleted scenes |
| `stash_deleter.yml` | Optionally add `candidate_tag_name` STRING setting (default: `stash_deleter:candidate`) |
| `docs/OUTPUT_CONTRACT.md` | Add `tagged_as` field to dry run output; update candidate shape to full schema |

---

## Open Questions (for Roy)

1. Does `sceneUpdate` mutation accept partial tag delta (add/remove) or requires full tag list replacement?
2. Are there permission guards on `tagCreate` / `sceneUpdate` in default Stash configs?
3. Does StashApp have a `createNotification` / toast mutation? (Would complement the primary approach)
4. What JS APIs are exposed in `ui.javascript` plugin scope? (For future Option 3 evaluation)

---

## Reference

Full analysis and pros/cons for all five options: `docs/DRY_RUN_UX.md`

---

### 2026-05-05 - deckard-multi-ruleset-architecture

### 2026-05-05T09:36:08+02:00: Multi-ruleset architecture — JS plugin page in v1 scope
By: smathev (confirmed), Deckard (designed)
What: Multiple named rule sets supported. JS plugin page added to v1. Flat settings: block removed from manifest. Rule sets stored as JSON array in configurePlugin. Tag pattern: stash-deleter:candidate:{rule_name}.

#### Detail

- `stash_deleter.yml` `settings:` block removed entirely. Replaced with `ui: javascript: [main.js]`.
- Config stored in `configuration.plugins["stash_deleter"]` as `{ deletion_scope, rules[] }`.
- Each rule has: `name` (tag slug), `label`, `enabled`, and up to six optional criteria fields.
- JS frontend (`main.js`) manages CRUD of rules via `configurePlugin` mutation; renders at `/plugin/stash_deleter`.
- Python `ConfigLoader` now returns `{ deletion_scope, rules[] }` — flat criteria fields gone.
- `DeletionExecutor` iterates rules: dry_run tags scenes with `stash-deleter:candidate:{name}`; delete clears all candidate tags first then deletes.
- `criteria_engine.find_candidates(rule)` accepts a single rule dict.
- Reference for JS pattern: DupFileManager (confirmed working on dev instance).

#### Reversal note

This supersedes the 2026-05-05T09:16:52+02:00 decision to use the flat `settings:` block only
(Option D). The flat approach cannot represent dynamic named rule sets. smathev confirmed the
reversal and directed JS in v1 scope on 2026-05-05.

---

### 2026-05-05 - roy-configurePlugin-array-test

# Roy Investigation: configurePlugin Array Storage Test

**Date:** 2026-05-05T09:36:08+02:00  
**Endpoint:** https://sa.micro/graphql  
**Status:** ✅ CONFIRMED — Arrays are fully supported

---

## Executive Summary

**Critical Finding: YES, `configurePlugin` fully supports storing JSON arrays.**

The mutation accepts nested array objects in the `input: Map!` parameter, and they are preserved perfectly when read back via `configuration { plugins }`. No stringification or flattening occurs.

---

## Test Results

### Test 1: Direct Array Syntax
**Query:**
```graphql
mutation {
  configurePlugin(plugin_id: "stash_deleter", input: {
    deletion_scope: "db_only",
    rules: [
      {name: "test_rule", min_play_count: 4, require_no_rating: true}
    ]
  })
}
```

**Response:**
```json
{
  "data": {
    "configurePlugin": {
      "deletion_scope": "db_only",
      "rules": [
        {
          "min_play_count": 4,
          "name": "test_rule",
          "require_no_rating": true
        }
      ]
    }
  }
}
```

✅ **ACCEPTED** — Array syntax works directly in GraphQL input

---

### Test 2: Query Configuration Back
**Query:**
```graphql
{
  configuration {
    plugins
  }
}
```

**Response (relevant portion):**
```json
{
  "data": {
    "configuration": {
      "plugins": {
        "stash_deleter": {
          "deletion_scope": "db_only",
          "rules": [
            {
              "min_play_count": 4,
              "name": "test_rule",
              "require_no_rating": true
            }
          ]
        }
      }
    }
  }
}
```

✅ **PRESERVED** — Array structure returned intact, no stringification

---

### Test 3: JSON String Fallback (For Reference)
**Query:**
```graphql
mutation {
  configurePlugin(plugin_id: "stash_deleter", input: {
    deletion_scope: "db_only",
    rules_json: "[{\"name\":\"test_rule\",\"min_play_count\":4}]"
  })
}
```

**Response:**
```json
{
  "data": {
    "configurePlugin": {
      "deletion_scope": "db_only",
      "rules_json": "[{\"name\":\"test_rule\",\"min_play_count\":4}]"
    }
  }
}
```

✅ **ALSO WORKS** — String fallback is supported, but unnecessary

---

## Implications for Deckard's Multi-Ruleset Architecture

### ✅ RECOMMENDATION: Use native array storage

**Deckard should:**

1. **Store rules as an array in `configurePlugin`:**
   ```python
   config = {
       "deletion_scope": "db_only",
       "dry_run": True,
       "rules": [
           {"name": "old_unwatched", "condition": {...}, "action": "delete"},
           {"name": "low_quality", "condition": {...}, "action": "delete"},
       ]
   }
   ```

2. **Read back via `configuration { plugins }`:**
   ```python
   self.PLUGIN_CONFIGURATION = self.get_configuration()["plugins"]["stash_deleter"]
   self.rules = self.PLUGIN_CONFIGURATION.get("rules", [])
   ```

3. **No JSON string parsing needed** — StashApp handles serialization/deserialization transparently

---

## Technical Details

- **StashApp Version:** Not detected in GraphQL schema, but behavior consistent with modern releases
- **Input Type:** `Map!` (arbitrary key-value, values can be primitives, objects, or arrays)
- **Array Depth:** Tested 1 level of nesting (array of objects); should support arbitrary depth
- **Limitations:** 
  - Mutation returns entire modified config (watch out for overwrite if not careful)
  - Must merge before writing if other plugins have config
  - No explicit schema validation — type safety is client-side responsibility

---

## Verdict for Architecture Decision

✅ **Multi-ruleset architecture is APPROVED at API level.** 

Deckard can proceed with:
- Array-based rule storage in `configurePlugin`
- Direct JSON array handling in Python (no serialization workaround needed)
- Multiple named rules with independent conditions and actions

No fallback to string storage is required.

---

### 2026-05-05 - roy-dry-run-display-findings

# Roy: Dry Run Output Display — Findings & Verdict

**Date:** 2026-05-05T09:27:26+02:00  
**Author:** Roy (API Explorer)  
**Status:** Investigation complete — ready for Deckard decision

---

## Summary

The user wants dry run results (20–100 deletion candidates) visible inside StashApp — not buried in a debug log. I investigated all available StashApp mechanisms live against `https://sa.micro/graphql`.

---

## What Doesn't Work

| Mechanism | Why not |
|-----------|---------|
| `logs` query | Visible only at Settings > Logs; plain text, no structure; user must navigate away |
| `runPluginTask` + jobQueue | Job type has no `output` field — plugin stdout is discarded after task run |
| Notification/toast API | **Does not exist** — no such mutation in StashApp GraphQL (confirmed exhaustive search) |
| PluginDir file serving | Files NOT web-accessible; only `/plugin/{id}/javascript` and `/css` are served |

---

## What Works

### Option A: `runPluginOperation` + JS registered route ✅ RECOMMENDED

**How it works:**
1. Python plugin handles dry run via `runPluginOperation` (not a task) — runs synchronously, stdout returned as `Any` directly in GraphQL response
2. JS plugin (`ui.javascript`) registers a React page at `/plugin/stash_deleter` using `PluginApi.register.route()`
3. JS page has "Run Dry Run" button → calls `runPluginOperation("stash_deleter", {mode: "dry_run"})` via `PluginApi.GQL`
4. Receives candidates JSON → renders table in React with Bootstrap

**Evidence:** DupFileManager does this exactly. Confirmed from live JS inspection of `https://sa.micro/plugin/DupFileManager/javascript`:
```javascript
// DupFileManager pattern (confirmed live):
mutation RunPluginOperation($plugin_id:ID!, $args:Map!) {
  runPluginOperation(plugin_id: $plugin_id, args: $args)
}
var result = JSON.parse(response.data.runPluginOperation.replaceAll("'", '"'));
```
DupFileManager registers 10+ routes (`/plugin/DupFileManager`, `/plugin/DupFileManager_CreateReport`, etc.) and uses this for all its interactive operations.

**PluginApi available to JS plugins (confirmed live):**
- `PluginApi.register.route(path, ReactComponent)` — custom pages
- `PluginApi.GQL` — authenticated GraphQL from JS
- `PluginApi.React`, `PluginApi.libraries.Bootstrap` — for building UI
- `PluginApi.patch.before(component, fn)` — inject into existing Stash UI

**Gotcha:** `runPluginOperation` returns stdout as a raw string, not parsed JSON. JS must `JSON.parse()` the result.

---

### Option B: `configurePlugin` scratchpad + JS route ✅ VIABLE (async variant)

**How it works:**
1. Python runs dry run as an **async task** (`runPluginTask`)
2. At end of dry run, Python calls `configurePlugin("stash_deleter", {...existing_settings..., "last_dry_run": [...]})` 
3. User navigates to `/plugin/stash_deleter` JS page
4. JS reads `{ configuration { plugins } }` → extracts `stash_deleter.last_dry_run` → renders table

**Caveat:** `configurePlugin` **overwrites the entire plugin config** — Python must first read existing settings, then merge, then write. Failing to do this will wipe user-configured settings.

**When to prefer this:** If dry run might time out as a synchronous operation (large libraries, complex filters). Lets the task run in background while user does other things.

---

## Recommended Architecture

**Use Option A as the primary pattern.** Add Option B as a fallback/persistence layer.

```
Manifest:
  tasks:
    - name: "Delete Scenes"      # async via runPluginTask
      defaultArgs: {mode: delete}
  ui:
    javascript: [main.js]       # registers /plugin/stash_deleter route

Python main.py:
  if args.mode == "dry_run":    # triggered by runPluginOperation
    candidates = find_candidates()
    print(json.dumps({"output": {"candidates": [...], "summary": {...}}, "error": null}))
  elif args.mode == "delete":   # triggered by runPluginTask
    ...delete logic...

JS main.js:
  PluginApi.register.route("/plugin/stash_deleter", DryRunPage)
  // DryRunPage: button → runPluginOperation → render table
```

---

## Decision Required

1. **Confirm Option A** as the implementation approach for dry run display
2. **Decide whether to add a JS plugin** (requires new `main.js` file + manifest `ui.javascript` entry)
3. **Decide on the dual-mode Python entrypoint**: `runPluginOperation` for dry run vs `runPluginTask` for delete

Full live query data: `.squad/agents/roy/LIVE_QUERY_RESULTS.md` § Dry Run Output Display

---

