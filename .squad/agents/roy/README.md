# Roy — API Explorer Investigation Complete

**Investigation Date:** 2026-05-05T08:17:09+02:00  
**Status:** ✅ COMPLETE — Ready for Rachael's implementation

## What Roy Discovered

Roy investigated the StashApp GraphQL API to identify all available data fields that can support scene auto-deletion. The investigation revealed a rich set of queryable metadata that enables flexible deletion criteria.

## Critical Findings

### Scene Fields Available for Deletion Logic

| Field | Type | Use Case | GraphQL Filter |
|-------|------|----------|---|
| `o_counter` | Int | Play count ("never watched" = 0) | ✅ IntCriterion |
| `rating100` | Int | Quality rating (0-100) | ✅ IntCriterion |
| `last_played_at` | Time | "Last viewed 30+ days ago" | ✅ DateCriterionInput |
| `created_at` | Time | "Added 90+ days ago" | ✅ DateCriterionInput |
| `files[].size` | Int | File size in bytes | ⚠️ Fetch, filter in Python |
| `files[].duration` | Float | Video length | ⚠️ Fetch, filter in Python |

### Deletion Operation

```graphql
mutation DestroyScene($id: ID!) {
  sceneDestroy(id: $id)  # ⚠️ Destructive, no undo
}
```

### Query Method

```graphql
query FindCandidates {
  findScenes(
    filter: { per_page: 50, sort: "created_at", direction: "DESC" }
    scene_filter: {
      # Combine these to find deletion candidates
      rating: { value: 0, modifier: "EQUALS" }
      o_counter: { value: 5, modifier: "LESS_THAN" }
      created_at: { value: "2026-02-05", modifier: "LESS_THAN" }
    }
  ) {
    count
    scenes { id title rating100 o_counter created_at files { size } }
  }
}
```

## Documentation Artifacts

### 📖 For Learning the API
- **`history.md`** — Complete GraphQL schema reference with all discovered fields
- **`SKILL.md`** — Reusable patterns, implementation checklist, common issues

### 🚀 For Building the Plugin (Rachael)
- **`example_queries.md`** — 4 working GraphQL query examples ready to copy/paste
- **`API_SUMMARY.txt`** — One-page quick reference (print this!)

### 📋 For Team Knowledge
- **`decisions/roy-graphql-findings.md`** — Key API facts team needs to know
- **`skills/stashapp-graphql/SKILL.md`** — Reusable skill for future StashApp work

## Ready-to-Use Query Examples

Roy created 4 complete, working query examples:

1. **Find unrated scenes watched multiple times** — Low-quality content that's popular
2. **Find scenes not watched in 30+ days** — Forgotten content for cleanup
3. **Find old, small, unrated scenes** — Storage reclamation candidates
4. **Fetch full scene metadata** — Pre-deletion validation query

⟹ See `example_queries.md` for the complete queries.

## Next Steps (for Rachael)

1. Read `example_queries.md` to understand GraphQL query structure
2. Study `skills/stashapp-graphql/SKILL.md` implementation guide
3. Build Python GraphQL client:
   - HTTP POST to endpoint
   - Compose filter criteria from YAML config
   - Paginate through results
   - Execute `sceneDestroy` mutation with confirmation
4. Test against local StashApp instance

## Key Insights

- **Server-side filtering is efficient:** Use scene_filter for date/rating/count criteria
- **Modifiers are limited:** Only EQUALS, GREATER_THAN, LESS_THAN (no regex/complex logic)
- **File properties require post-fetch filtering:** Size/duration must be checked in Python
- **Deletion is atomic:** Each scene requires separate `sceneDestroy` call
- **Pagination is required:** Batch process large libraries with per_page=50

## Files Created by Roy

```
.squad/agents/roy/
├── history.md                     ← Full API schema, learnings, field types
├── example_queries.md             ← 4 working query examples
├── API_SUMMARY.txt                ← One-page quick reference
└── README.md                       ← This file

.squad/decisions/
└── roy-graphql-findings.md        ← Team decision document

.squad/skills/stashapp-graphql/
└── SKILL.md                       ← Reusable implementation guide
```

## Questions?

- **What fields are available?** → See `history.md` Learnings section
- **How do I write a query?** → See `example_queries.md`
- **What's the deletion mutation?** → See `API_SUMMARY.txt` "DELETION MUTATION"
- **How do I implement this?** → See `skills/stashapp-graphql/SKILL.md`
- **What key facts should the team know?** → See `decisions/roy-graphql-findings.md`

---

**Investigation completed by Roy** — Ready to hand off to Rachael for implementation! 🎬
