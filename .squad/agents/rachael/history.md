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
