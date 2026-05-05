# Decision: StashApp GraphQL API Findings

**Date:** 2026-05-05T08:17:09+02:00  
**Author:** Roy (API Explorer)  
**Status:** DOCUMENTED  

## Summary

StashApp's GraphQL API provides rich scene metadata that supports multiple deletion criteria. The key findings enable Rachael to implement flexible scene auto-deletion based on play count, rating, age, and file properties.

## Key API Facts

### Primary Deletion Criteria Fields

| Field | Type | Purpose | Query Filter |
|-------|------|---------|--------------|
| `o_counter` | Int | Play/view count | IntCriterion |
| `rating100` | Int | Quality rating (0-100) | IntCriterion |
| `last_played_at` | Time | Last viewed timestamp | DateCriterionInput |
| `created_at` | Time | Scene added to library | DateCriterionInput |
| `files[].size` | Int | File size in bytes | — (fetch then filter) |
| `files[].duration` | Float | Video duration (seconds) | IntCriterion |

### Query Capabilities

- **Multi-criteria filtering:** Can combine rating + play count + dates in single query
- **Pagination:** `per_page` and `page` parameters for batch processing
- **Sorting:** Sort by created_at, updated_at, last_played_at, o_counter, rating
- **Entry point:** `findScenes(filter, scene_filter)` returns paginated results

### Deletion Operation

```graphql
mutation {
  sceneDestroy(id: $sceneId)  # Returns Boolean
}
```

**Important:** This is destructive, non-reversible. Always confirm scene ID before delete.

## Implications for Implementation

1. **Rachael should build deletion criteria logic around:**
   - Play count threshold: `o_counter < X` or `o_counter == 0`
   - Rating threshold: `rating100 < X`
   - Age: `created_at < date_threshold` or `last_played_at < date_threshold`
   - File properties: fetch scenes, then filter in Python for size/duration

2. **Recommended query structure:**
   - Use GraphQL filters for date/rating/count criteria (efficient server-side)
   - Fetch minimal metadata, then apply Python logic for complex rules

3. **Batch deletion safety:**
   - Query returns scene count; can paginate through results
   - Each deletion is atomic via `sceneDestroy` mutation
   - Recommend logging each deleted scene ID for audit trail

## Resources Created

- `.squad/agents/roy/example_queries.md` — Ready-to-use GraphQL queries for common deletion criteria
- `.squad/agents/roy/history.md` — Full API schema reference and learning notes

## Next Steps (for Rachael)

1. Review example queries in `example_queries.md`
2. Implement Python HTTP client to execute queries against GraphQL endpoint
3. Build deletion criteria validator (Python logic that decides which scenes to delete)
4. Implement `sceneDestroy` mutation executor with confirmation checks
