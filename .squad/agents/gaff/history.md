# Gaff — Project History

## Project Context
- **Project:** stash_deleter — StashApp plugin for auto-deleting scenes based on configurable criteria
- **Stack:** Python 3, pytest (optional), mock GraphQL responses
- **User:** Smathev
- **Initialized:** 2026-05-05

## Test Strategy Notes
- Priority 1: dry-run mode never deletes — must be verified first
- Priority 2: each criterion fires only when it should
- Priority 3: edge cases (nulls, zeros, very new files)

## Learnings
_Append new learnings below as work progresses._
