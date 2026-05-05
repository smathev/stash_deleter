# Deckard — History Summary
**Created:** 2026-05-05T07:36:08Z
**Summarization threshold trigger:** history.md exceeded 15360 bytes (19791 bytes)

## Mission

Deckard leads architectural design for stash_deleter plugin: a Python-based StashApp plugin for auto-deleting scenes based on configurable, named rule sets.

## Key Architectural Decisions (LOCKED)

### 1. Plugin Contract
- **Manifest:** `stash_deleter.yml` (YAML)
- **Entry point:** `{pluginDir}/venv/bin/python3` + `{pluginDir}/main.py`
- **Interface:** JSON (stdin/stdout)
- **Tasks:** "Dry Run" (`mode: dry_run`) + "Delete Scenes" (`mode: delete`)
- **Output shape:** `{ output: {...}, error: null }`

### 2. Configuration Architecture (PIVOTED 2x)
- **v0:** File-based (`stash_deleter_config.yml`)
- **v1:** In-app UI (`settings:` block in manifest) — **REJECTED** (insufficient for multiple rule sets)
- **v2:** Multi-ruleset with JS plugin page (GraphQL config + custom React component) — **APPROVED**

### 3. Multi-Ruleset Data Model (FINAL)
```json
{
  "deletion_scope": "db_only|with_file",
  "rules": [
    {
      "name": "old_unrated",
      "label": "Old & Unrated",
      "enabled": true,
      "unrated_after_plays": 5,
      "low_rating_min_plays": null,
      "low_rating_max_rating": null,
      "no_orgasm_after_plays": null,
      "never_played_after_days": null
    }
  ]
}
```

### 4. Dry Run UX
- **Primary:** Tag candidates with `stash-deleter:candidate:{rule_name}` during dry run
- **User flow:** User reviews in Scenes browser, filters by tag
- **Reversible:** Tags removed before live delete run (idempotent `clear_candidate_tags()`)
- **Fallback:** Formatted text table in job log (always available)

### 5. JS Plugin Page
- **Route:** `/plugin/stash_deleter` (registered via PluginApi.register.route)
- **UI:** React-based rule set manager (add/edit/delete rules, run buttons)
- **Config I/O:** `configurePlugin` mutation (write) + `configuration { plugins }` query (read)
- **Operation invocation:** `runPluginOperation` (synchronous, returns JSON directly)
- **Reference:** DupFileManager pattern (confirmed working in production)

### 6. Python Module Contracts
- **config_loader.py:** `ConfigLoader(graphql_client, plugin_id) → { deletion_scope, rules[] }`
- **deletion_executor.py:** `run_rules(rules, mode)` (iterate enabled rules, tag/delete per rule)
- **criteria_engine.py:** `find_candidates(rule, graphql_client) → [Scene]`
- **graphql_client.py:** `query()`, `mutate()` (handle auth via SessionCookie, query pooling)

## Deliverables This Session

1. ✅ **docs/CONFIG_DESIGN.md** — Rewritten for multi-ruleset architecture; GraphQL flow; module impact table
2. ✅ **stash_deleter.yml** — Updated manifest: removed flat `settings:` block, added `ui.javascript: [main.js]`
3. ✅ **config_loader.py stub** — Updated signature: `(graphql_client, plugin_id)`
4. ✅ **deletion_executor.py stub** — Updated API: `run_rules(rules, mode)`, `clear_candidate_tags()`
5. ✅ **docs/DRY_RUN_UX.md** — Full dry run UX design
6. ✅ **docs/DRY_RUN_OUTPUT.md** — Output contract + JSON shapes

## Team Coordination

**Roy** (API Explorer):
- ✅ Confirmed plugin output display constraints (no notification API, `runPluginOperation` synchronous)
- ✅ Verified `configurePlugin` native array support
- ✅ Documented GraphQL query patterns (play_count vs o_counter corrections)

**Rachael** (Python Dev):
- Next: Implement config_loader with GraphQL mocking; add rule iteration to deletion_executor

**Gaff** (QA):
- Scope: Integration tests for rule set execution

## Critical Dependencies

1. **Roy's GraphQL API:** config_loader depends on accurate `configuration { plugins }` query pattern
2. **Roy's deletion mutations:** deletion_executor depends on `sceneUpdate` (tag operations) and `sceneDestroy` patterns
3. **JS component assignment:** main.js development assigned to upcoming agent sprint

## Context for Next Session

- All architectural decisions locked (no more pivots planned)
- Implementation follows TDD: Red → Green → Refactor
- Skeleton with 5 GREEN boundary tests ready (c1b1208)
- venv with pytest, requests configured
- `ConfigLoader` and `deletion_executor` stubs ready for test-driven development
