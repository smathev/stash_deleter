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
