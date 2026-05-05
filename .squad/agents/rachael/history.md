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

## Learnings
_Append new learnings below as work progresses._
