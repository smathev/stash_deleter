# Squad Team

> stash_deleter

## Coordinator

| Name | Role | Notes |
|------|------|-------|
| Squad | Coordinator | Routes work, enforces handoffs and reviewer gates. |

## Members

| Name | Role | Charter | Status |
|------|------|---------|--------|
| Deckard | Lead | `.squad/agents/deckard/charter.md` | active |
| Roy | API Explorer | `.squad/agents/roy/charter.md` | active |
| Rachael | Python Dev | `.squad/agents/rachael/charter.md` | active |
| Gaff | Tester | `.squad/agents/gaff/charter.md` | active |
| Scribe | Session Logger | `.squad/agents/scribe/charter.md` | active |
| Ralph | Work Monitor | `.squad/agents/ralph/charter.md` | active |

## Project Context

- **Project:** stash_deleter — StashApp plugin for auto-deleting scenes based on configurable criteria
- **Stack:** Python (exec interface), StashApp GraphQL API, YAML plugin config
- **Goal:** Query StashApp for scenes matching deletion criteria (unrated after N plays, never played after N days, etc.) and optionally delete them
- **User:** Smathev
- **Created:** 2026-05-05
