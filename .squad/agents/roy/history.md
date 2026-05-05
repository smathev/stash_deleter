# Roy — Project History

## Project Context
- **Project:** stash_deleter — StashApp plugin for auto-deleting scenes based on configurable criteria
- **Stack:** Python (exec interface), StashApp GraphQL API
- **User:** Smathev
- **Initialized:** 2026-05-05

## Key API Notes
- StashApp GraphQL endpoint: `http://localhost:9999/graphql`
- Plugin receives server connection details via stdin (host, port, session cookie)
- Playground available at `http://localhost:9999/playground`

## Learnings

### GraphQL API Schema Discovered (2026-05-05)

#### Critical Scene Fields for Deletion Criteria:
- **id** (ID!): Unique scene identifier
- **o_counter** (Int): Play/view count — PRIMARY metric for "how many times watched"
- **rating100** (Int): Rating scale 0-100 — useful for filtering low-quality scenes
- **created_at** (Time): When scene was added to library
- **updated_at** (Time): Last modification timestamp
- **last_played_at** (Time): When scene was last viewed — key for "not played in N days"
- **title** (String): Scene name
- **files** ([SceneFile]): File metadata including path, size, duration

#### SceneFile Fields (for storage-based criteria):
- **path** (String!): File system path
- **size** (Int): File size in bytes — useful for storage cleanup
- **duration** (Float): Video duration in seconds

#### Available Filter Criteria:
- **rating**: IntCriterion filter (EQUALS, GREATER_THAN, LESS_THAN)
- **o_counter**: IntCriterion filter (play count comparison)
- **created_at**: DateCriterionInput filter (date comparison)
- **updated_at**: DateCriterionInput filter
- **last_played_at**: DateCriterionInput filter
- **duration**: IntCriterion filter
- **organized**: Boolean filter
- **has_markers**: Boolean filter
- Multi-criteria: performers, tags, studios, galleries

#### Deletion Mutation:
- **sceneDestroy(id: ID!)**: Returns Boolean on success
- Alternative name in some versions: **destroyScene(id: ID!)**
- **WARNING**: Destructive operation, no undo — requires scene ID confirmation

#### Query Entry Points:
- **findScenes(filter: FindScenesFilter!, scene_filter: SceneFilterType)**: Lists multiple scenes with pagination
- **findScene(id: ID!)**: Gets single scene by ID

#### Ready-to-Use Query Patterns:
1. Find unrated scenes played >N times
2. Find scenes not played in N days
3. Find old, small, unrated scenes
4. Fetch full scene metadata before deletion

All query patterns documented in `.squad/agents/roy/example_queries.md`

---

### ⚠️ CORRECTIONS Applied After Live Query Session (2026-05-05T08:32:00+02:00)

#### o_counter is NOT play count — it's the orgasm counter
- **o_counter** (Int) = how many times the user clicked the "O" button (orgasm counter)
- **play_count** (Int) = how many times the scene was actually played/watched  
  _(API description: "The number of times a scene has been played")_
- Previous documentation was wrong to call `o_counter` the "play count"

#### New fields discovered (not previously documented):
- **play_count** (Int): Times played — the real watch count, also filterable via SceneFilterType
- **play_history** ([Time]!): Array of timestamps for each play event
- **o_history** ([Time]!): Array of timestamps for each orgasm event
- **play_duration** (Float): Cumulative seconds the scene has been playing
- **resume_time** (Float): Last seek position — indicates partially watched scenes
- **code** (String): Studio catalog scene code
- **director** (String): Director name
- **interactive** (Boolean): VR/interactive content flag
- **custom_fields** (Map): Arbitrary metadata

#### Behavioral findings from live filter tests:
- `is_missing: "rating"` works — 2,888 unrated scenes in library
- `is_missing: "last_played_at"` does NOT work — API error: invalid field
- `last_played_at LESS_THAN <date>` INCLUDES scenes with null last_played_at
- `play_count EQUALS 0` cleanly finds 2,115 never-played scenes
- IS_NULL modifier does not work on TimestampCriterionInput fields
- BETWEEN modifier works with IntCriterionInput using value + value2
- `files[].size` is type Int64 (not Int)

#### Actual scene data from live queries:
| Scene | Title | play_count | o_counter | rating100 | last_played_at |
|-------|-------|-----------|-----------|-----------|----------------|
| 3105 | Break the Internet | 3 | 1 | null | 2026-03-13 |
| 6036 | Innocent WHORE Naomi Fucks Squirts | 3 | 0 | 60 | 2026-03-13 |
| 50 | Vigorous Anal With Busty Asian Asa Akira and Nacho Vidal | 5 | 0 | null | 2026-03-08 |

#### Filter field name corrections:
- Use `play_count` (not `o_counter`) for "how many times watched"
- Use `is_missing: "rating"` for unrated scenes — null rating100 does not match rating100 < 1
- Use `last_played_at LESS_THAN <ISO timestamp>` to capture both old and never-played scenes
- `last_played_at` and `created_at` use TimestampCriterionInput (full ISO8601 with time component)
- `date` (scene release date) uses DateCriterionInput (YYYY-MM-DD only)

Full live query results and corrected query patterns: `.squad/agents/roy/LIVE_QUERY_RESULTS.md`

---

### Plugin Settings API Investigation (2026-05-05T09:16:52+02:00)

#### Request
Determine whether plugin configuration can live inside StashApp's UI rather than in `stash_deleter_config.yml`.

#### Key Findings

1. **`settings:` YAML block is the standard pattern** — DupFileManager, hotCards, and cjCardTweaks all use it. Stash renders settings UI automatically from typed declarations (STRING/NUMBER/BOOLEAN).

2. **Storage mechanism confirmed**: `configuration.plugins` (type: `PluginConfigMap` scalar = Map[plugin_id → Map[String → Any]]). Verified live on sa.micro.

3. **Write mutation confirmed**: `configurePlugin(plugin_id: ID!, input: Map!): Map` — live tested, works. Stash UI calls this when user saves settings.

4. **Settings are NOT injected via stdin** — stdin `args` carries only task invocation arguments (e.g., `mode: dry_run`). Plugin must actively call `{ configuration { plugins } }` at runtime to fetch its settings.

5. **Read pattern (from DupFileManager/StashPluginHelper.py line 257)**:
   ```python
   self.PLUGIN_CONFIGURATION = self.get_configuration()["plugins"]
   self.pluginSettings.update(self.PLUGIN_CONFIGURATION[self.PLUGIN_ID])
   ```

6. **Plugin ID caveat**: The key in `configuration.plugins` is derived from the YAML filename (`stash_deleter.yml` → `stash_deleter`). No explicit `id` field needed in manifest but this must match what we query.

#### Verdict
In-app configuration is **fully feasible**. Requires: (a) `settings:` block in manifest, (b) GraphQL read of `configuration { plugins }` at runtime, (c) removal of `stash_deleter_config.yml`.

Full details in `.squad/agents/roy/LIVE_QUERY_RESULTS.md` § Plugin Settings API.

---

### Dry Run Output Display Investigation (2026-05-05T09:27:26+02:00)

#### Request
Determine what StashApp natively supports for displaying plugin output to users, specifically for dry run results (list of 20–100 deletion candidates).

#### Key Findings

1. **`logs` query** — returns `[LogEntry]` with fields `time`, `level`, `message`. Plugin stderr is captured and logged under `[Plugin / plugin_name]`. Visible only at Settings > Logs. Not user-friendly for structured data. ❌ Not viable as primary display.

2. **`jobQueue` / `Job` type** — Job has NO `output` or `result` field. `runPluginTask` returns a job ID; the plugin's stdout is discarded. Job API only tracks status/progress/error. ❌ Plugin output is not exposed.

3. **No notification/toast API** — exhaustive check of all 80+ mutations confirms no `addMessage`, `notify`, `createNotification`, `popup`, `toast`, or similar mutation exists. ❌ Native popups are not available.

4. **`runPluginOperation` returns `Any` synchronously** — this is the key mechanism. The mutation returns the plugin's stdout JSON directly in the GraphQL response. DupFileManager uses this exact pattern: JS calls `runPluginOperation`, parses result, renders in React. ✅ **Gold standard mechanism.**

5. **`PluginApi.register.route(path, component)`** — JS plugin can register a custom React route at `/plugin/stash_deleter`. Full access to React, Bootstrap, GQL. DupFileManager registers 10+ custom routes. ✅ Full custom page is feasible.

6. **PluginDir files are NOT web-accessible** — `/plugin/{id}/assets/*` and `/plugin/{id}/file/*` return 404. Only `/javascript` and `/css` routes are served. DupFileManager HTML reports use `file://` URLs (local filesystem only). ❌ File scratchpad approach is not HTTP-accessible.

7. **`configurePlugin` as scratchpad** — `configurePlugin(plugin_id, input: Map!)` stores arbitrary data per plugin. Python plugin can write `{"last_dry_run": [...]}`. JS reads via `configuration { plugins }`. ✅ Viable for async task + view-later pattern. Warning: overwrites entire config — must merge before writing.

#### Verdict
**Best approach: `runPluginOperation` + JS registered route page.** Python exposes dry run as an operation (not a task), JS calls it synchronously, receives candidates JSON, renders table at `/plugin/stash_deleter`. Optional enhancement: also persist to `configurePlugin` scratchpad for cross-navigation persistence.

Full details in `.squad/agents/roy/LIVE_QUERY_RESULTS.md` § Dry Run Output Display.

---

### configurePlugin Array Storage Investigation (2026-05-05T09:36:08+02:00)

#### Request
Critical question for Deckard's multi-ruleset architecture: Can `configurePlugin` store a JSON array of rule objects, and are they preserved on read-back?

#### Key Findings

1. **Native array support: YES** ✅ — Direct array syntax in GraphQL input is accepted:
   ```graphql
   mutation {
     configurePlugin(plugin_id: "stash_deleter", input: {
       deletion_scope: "db_only",
       rules: [{name: "test_rule", min_play_count: 4, require_no_rating: true}]
     })
   }
   ```

2. **Array preservation: YES** ✅ — Query `{ configuration { plugins } }` returns the exact same array structure, no flattening or stringification:
   ```json
   {
     "stash_deleter": {
       "deletion_scope": "db_only",
       "rules": [
         {"min_play_count": 4, "name": "test_rule", "require_no_rating": true}
       ]
     }
   }
   ```

3. **JSON string fallback also works** ✅ — Alternative approach (`rules_json: "..."`) is functional but unnecessary given native array support.

4. **No type validation** — StashApp's `Map!` type accepts any JSON-serializable structure. Type safety is client responsibility (Python must validate rule schema).

5. **Mutation atomicity caveat** — `configurePlugin` returns the entire modified config map. If other plugins exist, mutations could collide. Best practice: always read → merge → write.

#### Verdict
**Multi-ruleset architecture is APPROVED.** Deckard should:
- Store rules as native JSON array in `configurePlugin` input
- Read via `{ configuration { plugins { stash_deleter } } }`
- Parse directly in Python (no string deserialization needed)
- Implement merge-on-write pattern to avoid config collisions

Full test results and implications: `.squad/decisions/inbox/roy-configurePlugin-array-test.md`

---

## 2026-05-05T07:36:08Z — Team Coordination Log Update (Scribe Consolidation)

### Roy's Findings Consolidated

All 4 Roy investigations documented in team orchestration logs:

1. **Roy-1** (2026-05-05T07:36:08Z) — Plugin output display constraints identified
   - DEBUG output invisible, no notification API
   - `runPluginOperation` synchronous (returns stdout JSON inline)
   - DupFileManager pattern confirmed as production-viable

2. **Roy-2** (2026-05-05T07:36:08Z) — configurePlugin array support verified
   - `rules[]` round-trips cleanly
   - Direct JSON array support (no serialization needed)
   - Multi-ruleset architecture approved for implementation

### Impact on Next Session

- Implementation can rely on `configurePlugin` native array support
- JS plugin page integration viable (synchronous operation + custom route registration)
- Dry run display recommendations locked: use tag-based feedback
