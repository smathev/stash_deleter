# Session Log: plugin-contract
**Date:** 2026-05-05  
**Lead:** Deckard  
**Scribe:** Copilot  

## Objective
Define the complete contract between StashApp and our plugin before implementation begins. Establish the interface boundary for outside-in test development and enable parallel work (Rachael on main.py, Roy on GraphQL client).

## Work Completed

### Contract Research & Documentation
- Fetched official StashApp plugin documentation (https://docs.stashapp.cc/in-app-manual/plugins/)
- Documented complete interface:
  - Manifest file structure (yml), task definitions, exec array
  - Stdin payload: server_connection (GraphQL URL, auth cookie, PluginDir) + args
  - Stdout response: {error, output} JSON structure
  - Interface types: json (ours), raw, cbor

### Architecture Proposals
- **Two separate tasks** (recommended): "Dry Run" and "Delete Scenes" — safer UX than single mode toggle
- **Structured JSON output** — candidates array + summary (better for audit logs)
- **Fixed config location** — `{PluginDir}/stash_deleter_config.yml` (simpler than plugin UI settings)
- **TDD outside-in boundary** — test_main.py mocks stdin/stdout at this contract seam

### Decision Points Flagged
1. **Deletion scope**: destroyScene (DB-only) vs. +file deletion — requires smathev clarification
2. **Python interpreter**: python vs. python3 in exec array — recommendation: python3
3. (Three others resolved in proposal: config location, output format, task structure)

### Team Directives Captured
- **TDD philosophy**: Red → Green → Refactor
- **Outside-in**: Interface and integration first
- **Architecture**: SOLID, DRY, KISS, YAGNI, SoC, Tell-Don't-Ask, Composition, Law of Demeter
- **Ceremonies**: Refine → Document → Plan → Implement → Review

## Decision Documents
1. `.squad/decisions.md` — Plugin contract and development philosophy
2. `.squad/agents/deckard/history.md` — Session checkpoint with full technical details

## Handoff Status
- ✅ **Rachael**: Can now write main.py with exact stdin/stdout contract
- ✅ **Roy**: Can now build GraphQL client using server_connection fields
- ✅ **All**: Can write outside-in tests using stdin/stdout seam
- ⏳ **smathev**: Two decision points pending (deletion scope, interpreter)

## Files Modified This Session
- `.squad/decisions.md` (merged inbox)
- `.squad/orchestration-log/20260505-070541-deckard.md` (created)
- `.squad/log/20260505-plugin-contract.md` (created — this file)
