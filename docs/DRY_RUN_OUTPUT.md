# Dry Run Output — UX Design

**Author:** Deckard (Lead)  
**Date:** 2026-05-05T09:27:26+02:00  
**Status:** DECIDED — locked for implementation

---

## Problem

A dry run with many candidate scenes produces a `output` JSON object written at Stash's **DEBUG log level**. This means:

- Users must have debug logging enabled to see any output at all.
- Even with debug enabled, the task log is a flat text stream — not scannable for dozens/hundreds of scenes.
- There is no Stash popup, notification, or alert system available to plugins.

The result: without a richer output surface, a dry run is essentially invisible to the user.

---

## Options Considered

| Option | Mechanism | UX | Complexity | Verdict |
|--------|-----------|----|-----------:|---------|
| A) Rich task log | Format `output` as multi-line string | Requires debug logs ON; flat text | Very low | ❌ Invisible by default |
| B) Write a file | `{PluginDir}/last_dry_run.md` | User must leave Stash UI | Low | ❌ Poor UX |
| C) JS frontend page | `ui.javascript` injection + file read | Full control | High | ❌ Over-engineered for v1 |
| D) Stash file browser | Serve file via `ui.assets` | No markdown renderer in Stash | Medium | ❌ No renderer available |
| **E) Tag candidates** | `sceneUpdate` → adds tag to each candidate | Browse in normal scene list | Low | ✅ **CHOSEN** |

---

## Recommendation: Option E — Tag Candidates

### What this means

When a dry run executes, the plugin:

1. Creates a Stash tag named **`stash-deleter:candidate`** if it does not already exist (via `tagCreate` mutation, idempotent — check before create).
2. Adds that tag to every candidate scene via `sceneUpdate` mutation.
3. Returns a compact JSON `output` with the count and total size — a summary, not the full list.

The user then navigates to the **Scenes** page in Stash, filters by tag `stash-deleter:candidate`, and reviews exactly which scenes were matched — using Stash's own sort, filter, and preview UI.

### Why this is the right call for v1

- **KISS**: no new UI surface, no file I/O, no JavaScript.
- **YAGNI**: Stash already has a capable scene browser. There is no reason to duplicate it.
- **Actionable**: the user can click into each scene, inspect metadata, play it, and decide.
- **Reversible**: removing the tag reverts the dry run artifact completely.
- **Honest semantics**: dry run is "what _would_ be deleted" — tagging makes candidates browsable. The tag is the output artifact.

### Clarification on "dry" semantics

A dry run with Option E does write to the Stash database (tag assignments). This is intentional: the tag IS the result. It is not file deletion or irreversible. The tag is a low-risk, explicit artefact.

---

## End-to-End User Experience

1. User opens **Settings → Plugins → Stash Deleter**. Configures criteria (e.g. play_count < 3, unrated, no orgasms).
2. `dry_run` setting is `true` (default). User clicks **Run** on the Dry Run task.
3. Plugin runs. Stash task log shows: _"Stash Deleter dry run: 47 candidates tagged. Est. 142 GB freeable. Review tag: stash-deleter:candidate"_
4. User navigates to **Scenes → filter by tag → `stash-deleter:candidate`**.
5. User sees 47 scenes in the normal grid/list view. They review, remove the tag from any they want to keep.
6. When satisfied, user flips `dry_run` to `false` and runs **Delete Scenes** task.
7. Plugin deletes only scenes that still carry the `stash-deleter:candidate` tag AND still match criteria. It removes the tag from any remaining tagged scenes before returning.

---

## Output Contract Changes

### Current contract (dry run)

```json
{
  "output": {
    "mode": "dry_run",
    "candidates": [
      { "id": "123", "title": "Scene Title", "path": "...", "size_bytes": 1234567890 }
    ],
    "summary": "47 candidates found. Total size: 142 GB."
  },
  "error": null
}
```

### Updated contract (dry run with tagging)

```json
{
  "output": {
    "mode": "dry_run",
    "candidate_count": 47,
    "total_size_bytes": 152345678901,
    "candidate_tag": "stash-deleter:candidate",
    "candidate_tag_id": "391",
    "summary": "47 candidates tagged. Est. 142 GB freeable. Filter by tag 'stash-deleter:candidate' to review."
  },
  "error": null
}
```

**Changes from previous contract:**
- `candidates` array removed from `output` (was going to debug log anyway — not useful there; all data is in the Stash tag).
- Added `candidate_count`, `total_size_bytes`, `candidate_tag`, `candidate_tag_id`.
- `summary` string updated to include tag name as a navigation hint.

### Delete run (no change to shape, addendum on tag cleanup)

```json
{
  "output": {
    "mode": "delete",
    "deleted": [...],
    "failed": [...],
    "summary": "12 scenes deleted. 3 failed. stash-deleter:candidate tag cleared."
  },
  "error": null
}
```

The delete run **must** remove the `stash-deleter:candidate` tag from all scenes (tagged or not) upon completion, so the tag is clean for the next dry run.

---

## Impact on Rachael's Implementation

| Module | Change Required |
|--------|----------------|
| `deletion_executor.py` | Add `tag_candidates(scenes, graphql_client)` method for dry run. Add `_ensure_candidate_tag(graphql_client) → tag_id` private helper (create-if-missing). Add `clear_candidate_tags(graphql_client)` called at start of delete run. |
| `main.py` | Update dry run branch: call `tag_candidates` instead of returning candidate list. Update output dict shape per new contract. |
| `docs/OUTPUT_CONTRACT.md` | Update to reflect new dry run output shape. |
| `tests/test_deletion_executor.py` | Add tests for `tag_candidates` and `_ensure_candidate_tag` (mock GraphQL). |

### GraphQL mutations Rachael will need

```graphql
# Create tag (idempotent — check first with findTag)
mutation tagCreate($name: String!) {
  tagCreate(input: { name: $name }) { id name }
}

# Add candidate tag to a scene (merge with existing tags)
mutation sceneUpdate($id: ID!, $tag_ids: [ID!]!) {
  sceneUpdate(input: { id: $id, tag_ids: $tag_ids }) { id tags { id name } }
}

# Remove candidate tag from all scenes (called on delete run start)
mutation sceneUpdate($id: ID!, $tag_ids: [ID!]!) {
  sceneUpdate(input: { id: $id, tag_ids: $tag_ids }) { id }
}
```

> **Note for Rachael:** When adding the tag, fetch the scene's existing `tag_ids` first and merge — do not overwrite all tags with just the candidate tag.

---

## What Was NOT Chosen and Why

- **Option A (task log)**: `output` is DEBUG-level. Users don't see debug logs by default. Even if they did, a list of 100 scenes in a log is not actionable.
- **Option B (file on disk)**: requires the user to leave Stash, find the file, and open it in another application. Fails the "stay in the UI" UX bar.
- **Option C (JS page)**: adds a JavaScript layer, build concerns, and maintenance surface for a v1 feature. YAGNI.
- **Option D (ui.assets)**: StashApp has no built-in markdown or HTML file renderer. Serving a raw file via assets URL is not a meaningful UX improvement over Option B.
