# Squad Decisions

## Active Decisions

### 2026-05-05T06:32:13Z: User directive
**By:** smathev (via Copilot)
**What:** `o_counter` in StashApp tracks **orgasm count**, NOT play count. These are two separate fields. Do not conflate them.
**Why:** User correction — captured for team memory. Roy's earlier summary incorrectly described o_counter as "play count".
**Impact:** The deletion criteria "never cum despite watching 5 times" uses o_counter (orgasms); "played 5 times" uses a different field (likely `play_count` or `play_history` — to be confirmed by Roy).

### 2026-05-05T09:05:28+02:00: StashApp Plugin Contract
**By:** Deckard (Lead)  
**Status:** Proposed — awaiting smathev confirmation  
**What:** 
- Plugin discovered from `~/.stash/plugins/` via `*.yml` manifest
- Stdin/stdout JSON interface: receives `server_connection` + `args`, returns `{error, output}`
- Two separate tasks recommended: "Dry Run" (mode: dry_run) and "Delete Scenes" (mode: delete)
- Structured JSON response with candidates array and summary string
- Config file at fixed path: `{PluginDir}/stash_deleter_config.yml`

**Decision Points Pending smathev Input:**
1. Deletion scope: `destroyScene` DB-only vs. `destroyScene` + OS file deletion
2. Python interpreter: `python` vs. `python3` in exec array

**Impact:** Defines contract boundary for Roy (GraphQL auth), Rachael (main.py entry), and all tests.

### 2026-05-05T09:05:41+02:00: Development Philosophy Directives
**By:** smathev (via Copilot)  
**Status:** Active  
**What:** Non-negotiable project principles:
- **TDD**: Red → Green → Refactor
- **Outside-in**: Plugin interface and integration first
- **Ceremonies**: Refine → Document → Plan → Implement → Review per feature
- **Architecture**: SOLID (SRP/OCP/LSP/ISP/DIP), DRY, KISS, YAGNI, SoC, Tell-Don't-Ask, Composition over Inheritance, Law of Demeter
- **Quality**: Small, single-purpose, testable functions; no chained calls

**Impact:** Enforcement directive — call out violations during code review and design phases.

## Governance

- All meaningful changes require team consensus
- Document architectural decisions here
- Keep history focused on work, decisions focused on direction
