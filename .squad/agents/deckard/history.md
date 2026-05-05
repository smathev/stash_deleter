# Deckard — Project History

## Project Context
- **Project:** stash_deleter — StashApp plugin for auto-deleting scenes based on configurable criteria
- **Stack:** Python (exec interface), StashApp GraphQL API, YAML plugin config
- **User:** Smathev
- **Initialized:** 2026-05-05

## API Query Patterns (from Roy)

**2026-05-05:** Roy completed live GraphQL queries and documented corrected patterns in `.squad/agents/roy/LIVE_QUERY_RESULTS.md`. Key corrections:
- `o_counter` = orgasm counter (not play count)
- `play_count` = actual watch/view count ← use this for deletion criteria
- Filter gotchas documented: IS_NULL broken on timestamps, null handling in LESS_THAN
- 2,888 unrated scenes, 2,115 never-played in library
- Ready-to-use query patterns for common deletion scenarios

Ready to design query strategies using corrected field mappings.

## Learnings
_Append new learnings below as work progresses._
