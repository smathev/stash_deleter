# Stash Deleter — Dry Run UX Design

**Author:** Deckard (Lead)  
**Date:** 2026-05-05T09:27:26+02:00  
**Status:** Draft — awaiting Roy's API findings for Options 3 and 5

> Roy is investigating technical feasibility of Options 3 and 5. This document will be updated when his findings are in.

---

## 1. Candidate Scene Data Shape

### Purpose

Each scene the dry run would delete must carry enough information for the user to make an informed keep/delete decision. The shape must be:
- Serialisable to JSON (machine-readable)
- Renderable as a human-readable table
- Sufficient for the user to identify the scene and understand *why* it matched

### Schema

```json
{
  "id": "42",
  "title": "Scene Title (or empty string if untitled)",
  "path": "/data/videos/scene.mp4",
  "size_bytes": 2147483648,
  "size_human": "2.00 GB",
  "duration_seconds": 3600.0,
  "play_count": 5,
  "o_counter": 0,
  "rating100": null,
  "last_played_at": "2025-06-01T12:00:00Z",
  "matched_criteria": ["no_orgasm_after_plays", "unrated_after_plays"],
  "reason": "Watched 5 times, never rated, no orgasms recorded"
}
```

### Field Reference

| Field | Type | Source | Notes |
|---|---|---|---|
| `id` | string | StashApp `Scene.id` | String, not int |
| `title` | string | `Scene.title` | Empty string if untitled |
| `path` | string | `Scene.files[0].path` | Primary file path |
| `size_bytes` | int | `Scene.files[0].size` | 0 if unavailable |
| `size_human` | string | Computed | e.g. "2.00 GB" |
| `duration_seconds` | float | `Scene.files[0].duration` | Total video length |
| `play_count` | int | `Scene.play_count` | View/watch count |
| `o_counter` | int | `Scene.o_counter` | Orgasm counter (separate from play_count) |
| `rating100` | int \| null | `Scene.rating100` | 0–100 scale, null = unrated |
| `last_played_at` | string \| null | `Scene.last_played_at` | ISO 8601 timestamp |
| `matched_criteria` | array[string] | Computed | Criterion key names from config |
| `reason` | string | Computed | Human-readable summary of match |

### Field Notes

- `play_count` and `o_counter` are **separate counters** — confirmed by Roy's live API queries. Never conflate them. See `.squad/decisions.md`.
- `rating100` uses `null` (not `0`) for unrated scenes. Stash's `LESS_THAN` filter does NOT match nulls — use `is_missing: "rating"` for unrated queries.
- `last_played_at` is `null` for never-played scenes. The `IS_NULL` GraphQL modifier is broken for timestamps — use `LESS_THAN` with an early sentinel date.
- `matched_criteria` lists all criterion keys that triggered the match (OR semantics — any one is enough).
- `reason` is a rendered summary for human display, e.g. `"Watched 5×, never rated, no orgasms"`.

### As a Text Table

```
ID    | Title                          | Size    | Plays | O | Rating | Last Played  | Reason
------+--------------------------------+---------+-------+---+--------+--------------+------------------------------------
42    | Some Scene Title               | 2.00 GB | 5     | 0 | -      | 2025-06-01   | Watched 5×, never rated, no orgasms
117   | Another Scene                  | 1.00 GB | 3     | 0 | 60/100 | 2025-09-12   | Low rating after 3 plays
```

---

## 2. Output Presentation Options

### Option 1: StashApp Job Log (Built-in)

Plugin formats `output` as a human-readable text table. StashApp logs it to the Tasks/Jobs console.

**Pros:**
- Zero extra implementation effort — output goes to log already
- No new infrastructure
- Available today

**Cons:**
- Logged at DEBUG level — buried, not visible by default
- User must open Tasks log and scroll to find it
- No filtering or interactivity
- Not "in Stash" in any meaningful UX sense
- Disappears on log rotation

**Verdict:** Adequate as a fallback. Insufficient as primary UX for a deletion tool.

---

### Option 2: Write Results File to PluginDir

After each dry run, write `dry_run_results.md` (or `.json`) to the plugin's directory alongside `main.py`.

**Pros:**
- Simple to implement (one `open().write()` call)
- Markdown is human-readable in any editor
- Persists between runs
- JSON variant is machine-parseable for future tooling

**Cons:**
- Requires filesystem access — user must navigate outside StashApp
- Path varies per installation
- Not "in Stash"

**Verdict:** Good for debugging and audit trails. Not suitable as the primary user-facing result display.

---

### Option 3: JavaScript UI Injection

StashApp supports `ui.javascript` in the manifest to inject JS into the frontend. A script could poll for a results file or call a custom endpoint and render a modal.

**Pros:**
- Fully "in Stash" — modal or panel appears in the UI
- Rich presentation (tables, links to scenes, confirm/deny per scene)
- Most polished user experience

**Cons:**
- Requires substantial JS development alongside Python
- Maintenance surface doubles (Python + JS)
- Polling/endpoint approach is fragile
- Requires Roy to confirm what JS APIs are available
- Significant scope creep for v0.1

**Verdict:** Ideal long-term target. Out of scope for v0.1. Deferred pending Roy's findings.

> ⚠️ **Roy is investigating:** What JS APIs does StashApp expose for plugin UI injection? Can injected JS read the plugin output or call back to a plugin endpoint?

---

### Option 4: Tag Candidates with `stash_deleter:candidate` ⭐

After dry run, create the tag `stash_deleter:candidate` in StashApp (if it doesn't exist) and assign it to all candidate scenes. User can then filter the Scenes view by this tag.

**Workflow:**
1. User runs "Dry Run" task
2. Plugin evaluates criteria → produces candidate list
3. Plugin calls `findOrCreateTag(name: "stash_deleter:candidate")`
4. Plugin calls `sceneUpdate` to assign the tag to each candidate (and only candidates — removes from any scenes no longer matching)
5. Plugin returns structured output as normal
6. User navigates to Scenes → filters by tag `stash_deleter:candidate`
7. User reviews the full list in StashApp's native scene browser
8. User may manually remove the tag from scenes they want to keep
9. User runs "Delete Scenes" task → plugin re-evaluates criteria (or optionally reads the tag)

**Pros:**
- Stash-native — uses the existing Scenes view with all its sorting, filtering, thumbnails
- No new UI code whatsoever
- Creates a natural "review → confirm" workflow
- Tag is persistent across sessions — user can take time to review
- User can remove the tag from individual scenes to exclude them (if future work makes delete-by-tag supported)
- Tag doubles as an audit trail — visible in scene metadata
- Tag cleanup on each dry run keeps the list fresh

**Cons:**
- Dry run now performs GraphQL writes (tag assignment) — not purely read-only
- Need to handle tag cleanup (remove tag from previously-tagged scenes that no longer match)
- Adds `sceneUpdate` and `findOrCreateTag`/`tagCreate` mutations to the implementation scope
- Must not create side-effects that confuse users ("Why do my scenes have this tag?")

**Mitigation for the write concern:**
Tagging is reversible. The dry run clearly states it makes no deletions — tagging scenes is acceptable metadata. The tag name is self-documenting. A visible note in the plugin output (`"Tagged N scenes with 'stash_deleter:candidate'"`) makes the side effect transparent.

**Verdict:** **Recommended primary approach.** Best ratio of UX value to implementation cost. Fully Stash-native.

---

### Option 5: StashApp Notification/Toast API

If StashApp exposes a `createNotification` or similar mutation, pop a summary toast after dry run.

**Pros:**
- Immediate, visible feedback
- Minimal implementation

**Cons:**
- Summary only — can't list 50+ scenes in a toast
- Roy has not confirmed this API exists
- Likely limited to status messages, not tabular data

**Verdict:** Useful as a complement (e.g. "Dry run complete — 23 candidates tagged"), not as standalone. Deferred pending Roy's findings.

> ⚠️ **Roy is investigating:** Does StashApp have a `createNotification` mutation or equivalent toast API?

---

## 3. Recommendation

### Primary: Option 4 — Tag Candidates

**Assign `stash_deleter:candidate` tag to all matching scenes after each dry run.**

Rationale:
- Uses StashApp's existing Scenes browser — the user already knows how to use it
- No JS, no frontend work, no file system navigation
- The "review tagged scenes → run delete" workflow is intuitive and safe
- Aligns with KISS: we're adding one tag operation, not building a new UI
- The tag is self-cleaning (each dry run replaces the tag list) and reversible (deletion is still a separate task)

**Required implementation additions:**
- `graphql_client.py`: add `find_or_create_tag(name)`, `assign_tag_to_scenes(tag_id, scene_ids)`, `remove_tag_from_scenes(tag_id, scene_ids)`
- `criteria_engine.py`: after building candidate list, call tag operations
- `stash_deleter.yml`: optionally add `candidate_tag_name` STRING setting (default: `stash_deleter:candidate`) so users can rename the tag
- `OUTPUT_CONTRACT.md`: update dry run output to include `"tagged_as": "stash_deleter:candidate"`

**Tag lifecycle:**
```
Dry Run run N:   Remove tag from all previously-tagged scenes
                 → Tag all current candidates
Delete Scenes:   (reads criteria fresh, not tag — tag is informational only for now)
```

### Fallback: Option 1 — Formatted Job Log

If tagging proves unexpectedly complex (e.g. `sceneUpdate` has permission issues in some Stash configs), fall back to formatting the `output` field as a readable text table. This is always available and requires zero additional work.

---

## 4. Architectural Impact

### What Changes (Option 4)

| Component | Change |
|---|---|
| `graphql_client.py` | Add `find_or_create_tag`, `update_scene_tags`, `find_scenes_by_tag` mutations |
| `criteria_engine.py` | After producing candidates list, call tagging operations |
| `deletion_executor.py` | On delete run: optionally remove `stash_deleter:candidate` tag after deletion |
| `stash_deleter.yml` | Add optional `candidate_tag_name` STRING setting |
| `OUTPUT_CONTRACT.md` | Add `tagged_as` field to dry run output |
| `docs/OUTPUT_CONTRACT.md` | Update dry run schema + examples |

### What Stays The Same

- Core criteria evaluation logic
- GraphQL query patterns for scene filtering
- Deletion flow in `deletion_executor.py`
- Plugin stdin/stdout contract envelope
- Config loading via `configuration.plugins`

### Candidate Data Shape — Impact on Existing Contract

The current `OUTPUT_CONTRACT.md` candidate shape is:
```json
{"id", "title", "path", "size_bytes", "matched_criteria"}
```

The enriched shape adds: `size_human`, `duration_seconds`, `play_count`, `o_counter`, `rating100`, `last_played_at`, `reason`.

These fields are already being fetched by the GraphQL query (Roy's queries retrieve all of them). The additions are pure enrichment — backward-compatible.

**Recommendation:** Update `OUTPUT_CONTRACT.md` to match the full candidate shape defined in Section 1 of this document.

---

## 5. Open Questions (Pending Roy's Findings)

| # | Question | Blocks |
|---|---|---|
| 1 | Does StashApp expose a `createNotification` or toast mutation? | Option 5 viability |
| 2 | What JS APIs does StashApp expose in `ui.javascript` scope? Can injected JS read plugin task output? | Option 3 viability |
| 3 | Does `sceneUpdate` mutation accept partial tag assignment (add/remove individual tags)? Or does it require the full tag list? | Option 4 implementation detail |
| 4 | Are there permission guards on `tagCreate` / `sceneUpdate` in default Stash configs? | Option 4 risk |
| 5 | Does StashApp allow the plugin's own job log output to be formatted with Markdown or ANSI color? | Option 1 enhancement |

---

## 6. Decision Summary

| Option | Status | Decision |
|---|---|---|
| 1: Job log | Available now | **Fallback** — implement as baseline |
| 2: Results file | Available now | Skip for v0.1 (not "in Stash") |
| 3: JS injection | Pending Roy | Deferred — out of scope for v0.1 |
| 4: Tag candidates | Available now | **Primary recommendation** |
| 5: Toast/notification | Pending Roy | Complement only if confirmed |
