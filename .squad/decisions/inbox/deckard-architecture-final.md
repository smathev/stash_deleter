# Architecture Final — Deckard
**Date:** 2026-05-05T09:16:52+02:00  
**Author:** Deckard (Lead)  
**Status:** CONFIRMED — ready for implementation

---

## 1. Manifest exec line

```yaml
exec:
  - "{pluginDir}/venv/bin/python3"
  - "{pluginDir}/main.py"
```

Always reference the venv interpreter — never the system `python` or `python3`.

---

## 2. Tasks

| Task name | defaultArgs.mode | Purpose |
|---|---|---|
| Dry Run | `dry_run` | List candidates, no mutations |
| Delete Scenes | `delete` | Execute deletions per config scope |

---

## 3. Config schema (confirmed)

File: `{PluginDir}/stash_deleter_config.yml`

```yaml
dry_run: true                    # OPTIONAL, default true
deletion_scope: db_only          # REQUIRED: db_only | with_file

criteria:
  - unrated_after_plays: 4
  - low_rating_after_plays:
      min_plays: 3
      max_rating: 30
  - no_orgasm_after_plays: 5
  - never_played_after_days: 30
```

Criteria semantics: **OR** — any single match makes a scene a candidate.

---

## 4. Output contract (confirmed)

### Dry run success envelope
```json
{
  "output": {
    "mode": "dry_run",
    "candidates": [{ "id", "title", "path", "size_bytes", "matched_criteria" }],
    "summary": { "candidate_count", "total_size_bytes", "total_size_human" }
  },
  "error": null
}
```

### Delete success envelope
```json
{
  "output": {
    "mode": "delete",
    "deletion_scope": "db_only",
    "deleted": [{ "id", "title", "path", "size_bytes", "matched_criteria" }],
    "failed": [{ "id", "title", "path", "size_bytes", "matched_criteria", "error" }],
    "summary": { "deleted_count", "failed_count", "total_size_freed_bytes", "total_size_freed_human" }
  },
  "error": null
}
```

### Error envelope
```json
{ "output": null, "error": "<descriptive string>" }
```

Full spec: `docs/OUTPUT_CONTRACT.md`

---

## 5. Dev symlink path

Docker mount root: `/mnt/stashForDevelop/`  
Plugins directory (confirmed): `/mnt/stashForDevelop/config/plugins/`

Symlink command:
```bash
ln -s /home/smathev/git_dev/stash_deleter /mnt/stashForDevelop/config/plugins/stash_deleter
```

---

## 6. Open items for other agents

- **Roy:** Implement GraphQL queries using confirmed field mappings (`play_count`, `o_counter`, `rating100`). Auth via `SessionCookie` from stdin `server_connection`.
- **Rachael:** Implement `main.py` + `plugin/` modules against the output contract above. Dry-run guard: respect `dry_run` flag in config AND `args.mode`.
- **Gaff:** Write integration tests validating stdout shape for both tasks against this contract.
