# Squad Decisions

## Active Decisions

### 2026-05-05T06:32:13Z: User directive
**By:** smathev (via Copilot)
**What:** `o_counter` in StashApp tracks **orgasm count**, NOT play count. These are two separate fields. Do not conflate them.
**Why:** User correction — captured for team memory. Roy's earlier summary incorrectly described o_counter as "play count".
**Impact:** The deletion criteria "never cum despite watching 5 times" uses o_counter (orgasms); "played 5 times" uses a different field (likely `play_count` or `play_history` — to be confirmed by Roy).

### 2026-05-05T09:05:28+02:00: StashApp Plugin Contract
**By:** Deckard (Lead)  
**Status:** CONFIRMED by smathev — locked for implementation
**What:** 
- Plugin discovered from `~/.stash/plugins/` via `*.yml` manifest
- Stdin/stdout JSON interface: receives `server_connection` + `args`, returns `{error, output}`
- Two separate tasks: "Dry Run" (mode: dry_run) and "Delete Scenes" (mode: delete)
- Structured JSON response with candidates array and summary dict
- Config: **moved from file to in-app UI settings** (see below)
- Tasks accessible via manifest `tasks:` array with `defaultArgs` for each

**Why:** Locked architecture. Defines contract boundary for all agents.

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

### 2026-05-05T09:16:52+02:00: Architecture — manifest, exec, tasks, output contract
**By:** smathev (via Deckard)
**Status:** CONFIRMED — locked for implementation
**What:**
1. **Manifest exec** — always use venv Python: `["{pluginDir}/venv/bin/python3", "{pluginDir}/main.py"]`
2. **Tasks** — two entries: "Dry Run" + "Delete Scenes" with `defaultArgs.mode`
3. **Output contract** — JSON envelope: `{"output": {...}, "error": null}` for success; error: "descriptive string" on failure
4. **Config scope** — db_only (DB record only) vs with_file (+ OS deletion)
5. **venv requirement** — always use virtualenv, never system Python
6. **Dev symlink** — `/mnt/stashForDevelop/config/plugins/stash_deleter` → project root

**Why:** smathev confirmed all architectural decisions. These are locked. Full spec in docs/OUTPUT_CONTRACT.md.

### 2026-05-05T09:16:52+02:00: User directive — In-app configuration only
**By:** smathev (via Copilot)
**Status:** CONFIRMED — implementation underway
**What:** All plugin configuration in StashApp UI, NOT file-based. Users set config on plugin's Settings page. No YAML config file. No post-install manual steps.
**Why:** User request: "in stash, not outside". Config redesigned from file → in-app UI.
**Impact:** `stash_deleter_config.yml` deleted. `config_loader.py` rewritten to fetch from GraphQL `configuration.plugins` API instead of file I/O.

### 2026-05-05T09:16:52+02:00: Config UI approach — settings: block in manifest
**By:** Deckard + Roy
**Status:** CONFIRMED
**What:** 
- Manifest `settings:` block renders form fields in StashApp Settings > Plugins page
- Supported field types: BOOLEAN, NUMBER, STRING (no dropdowns)
- Settings NOT in stdin; plugin calls `query Configuration { configuration { plugins } }` to fetch
- Plugin ID derived from YAML filename: `stash_deleter.yml` → `stash_deleter` key in config map
- Alternative mutation: `configurePlugin(plugin_id, input)` to update settings programmatically
- Manifest fields: `dry_run` (BOOLEAN, default true), `deletion_scope` (STRING, default db_only), criteria fields (NUMBER, default 0 = disabled)

**Why:** StashApp fully supports in-app config. Community plugins (DupFileManager, stash-scheduler) use this pattern. Eliminates file I/O. Better UX.

## Governance

- All meaningful changes require team consensus
- Document architectural decisions here
- Keep history focused on work, decisions focused on direction
