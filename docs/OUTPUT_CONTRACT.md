# Stash Deleter — Output Contract

This document defines the exact JSON shape that `main.py` must write to stdout for every invocation.
Rachael implements this contract; Gaff tests against it.

---

## Envelope (both tasks)

StashApp reads a single JSON object from stdout:

```json
{
  "output": <object | null>,
  "error":  <string | null>
}
```

- `output` — present and non-null on success; logged at DEBUG level by StashApp.
- `error` — present and non-null on failure; logged at ERROR level by StashApp.
- A non-zero exit code is also treated as failure by StashApp.
- Both keys MUST always be present (use `null` for the absent one).

---

## Task: Dry Run (`mode: dry_run`)

### Success

```json
{
  "output": {
    "mode": "dry_run",
    "candidates": [
      {
        "id": "42",
        "title": "Some Scene Title",
        "path": "/data/videos/some_scene.mp4",
        "size_bytes": 2147483648,
        "matched_criteria": ["unrated_after_plays"]
      },
      {
        "id": "117",
        "title": "Another Scene",
        "path": "/data/videos/another.mp4",
        "size_bytes": 1073741824,
        "matched_criteria": ["low_rating_after_plays", "no_orgasm_after_plays"]
      }
    ],
    "summary": {
      "candidate_count": 2,
      "total_size_bytes": 3221225472,
      "total_size_human": "3.00 GB"
    }
  },
  "error": null
}
```

### No candidates found

```json
{
  "output": {
    "mode": "dry_run",
    "candidates": [],
    "summary": {
      "candidate_count": 0,
      "total_size_bytes": 0,
      "total_size_human": "0 B"
    }
  },
  "error": null
}
```

---

## Task: Delete Scenes (`mode: delete`)

### Success

```json
{
  "output": {
    "mode": "delete",
    "deletion_scope": "db_only",
    "deleted": [
      {
        "id": "42",
        "title": "Some Scene Title",
        "path": "/data/videos/some_scene.mp4",
        "size_bytes": 2147483648,
        "matched_criteria": ["unrated_after_plays"]
      }
    ],
    "failed": [
      {
        "id": "117",
        "title": "Another Scene",
        "path": "/data/videos/another.mp4",
        "size_bytes": 1073741824,
        "matched_criteria": ["low_rating_after_plays"],
        "error": "GraphQL mutation returned null"
      }
    ],
    "summary": {
      "deleted_count": 1,
      "failed_count": 1,
      "total_size_freed_bytes": 2147483648,
      "total_size_freed_human": "2.00 GB"
    }
  },
  "error": null
}
```

### Nothing to delete

```json
{
  "output": {
    "mode": "delete",
    "deletion_scope": "db_only",
    "deleted": [],
    "failed": [],
    "summary": {
      "deleted_count": 0,
      "failed_count": 0,
      "total_size_freed_bytes": 0,
      "total_size_freed_human": "0 B"
    }
  },
  "error": null
}
```

---

## Error responses

### Config file missing or invalid

```json
{
  "output": null,
  "error": "Config error: stash_deleter_config.yml not found at /path/to/plugin/stash_deleter_config.yml"
}
```

### GraphQL connection failure

```json
{
  "output": null,
  "error": "GraphQL error: Connection refused — is StashApp running? (http://localhost:9999)"
}
```

### Unknown mode

```json
{
  "output": null,
  "error": "Unknown mode: 'foo'. Expected 'dry_run' or 'delete'."
}
```

### Unhandled exception (safety net)

```json
{
  "output": null,
  "error": "Unhandled exception: <exception type>: <message>"
}
```

---

## Field reference

| Field | Type | Notes |
|---|---|---|
| `output.mode` | string | `"dry_run"` or `"delete"` |
| `output.candidates` | array | Dry run only |
| `output.deleted` | array | Delete mode only |
| `output.failed` | array | Delete mode only — scenes that matched but could not be deleted |
| `output.deletion_scope` | string | Delete mode only — echoes config value |
| `scene.id` | string | StashApp scene ID (string, not int) |
| `scene.title` | string | Scene title from StashApp |
| `scene.path` | string | Absolute path to the primary file |
| `scene.size_bytes` | int | File size in bytes |
| `scene.matched_criteria` | array[string] | Which criteria keys caused this scene to be a candidate |
| `summary.candidate_count` | int | Dry run only |
| `summary.deleted_count` | int | Delete mode only |
| `summary.failed_count` | int | Delete mode only |
| `summary.total_size_*` | int/string | Bytes freed (delete) or bytes at risk (dry run) |

---

## Implementation notes for Rachael

1. Always write exactly one JSON object to stdout before exit.
2. Wrap the entire `main()` in a try/except that catches all exceptions and emits the error envelope.
3. Exit code 0 even on partial failures (failed array) — non-zero exits suppress the output envelope in some StashApp versions.
4. `size_bytes` should be `0` if the file path is unavailable, not omitted.
5. `matched_criteria` must list the criterion key name as it appears in `stash_deleter_config.yml`.
