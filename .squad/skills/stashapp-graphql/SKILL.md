# Skill: StashApp GraphQL API Interaction

**Domain:** StashApp plugin development  
**Difficulty:** Intermediate  
**Tags:** graphql, stashapp, api, queries, mutations  

## Overview

This skill enables building GraphQL queries and mutations for the StashApp media server. StashApp exposes a comprehensive GraphQL API for scene management, filtering, and deletion.

## Key Concepts

### Schema Structure

StashApp GraphQL organizes data around the `Scene` type with metadata about video files, performers, tags, ratings, and play history.

**Primary types:**
- `Scene`: Video content (title, rating, play count, dates)
- `SceneFile`: File metadata (path, size, duration, codecs)
- `Performer`, `Tag`, `Studio`: Related entities
- `IntCriterion`, `DateCriterionInput`: Filter types for queries

### Query Pattern: findScenes

```graphql
query {
  findScenes(
    filter: { per_page: 50, sort: "created_at", direction: "DESC" }
    scene_filter: { ... criteria ... }
  ) {
    count
    scenes { ... fields ... }
  }
}
```

**Filter parameters:**
- `per_page`: Pagination limit (default 25)
- `sort`: Sort field (created_at, updated_at, last_played_at, o_counter, rating)
- `direction`: "ASC" or "DESC"

**scene_filter supports:**
- `rating: IntCriterion` — Filter by rating (0-100)
- `o_counter: IntCriterion` — Filter by play count
- `created_at: DateCriterionInput` — Filter by creation date
- `last_played_at: DateCriterionInput` — Filter by last viewed date
- `performers`, `tags`, `studios`: MultiCriterionInput for multi-select filters

### Criterion Types

**IntCriterion:**
```graphql
{
  value: Int!
  modifier: "EQUALS" | "GREATER_THAN" | "LESS_THAN"
}
```

**DateCriterionInput:**
```graphql
{
  value: "YYYY-MM-DD"
  modifier: "EQUALS" | "GREATER_THAN" | "LESS_THAN"
}
```

## Common Patterns

### Pattern 1: Find Unrated Scenes

```graphql
query FindUnrated {
  findScenes(scene_filter: { rating: { value: 0, modifier: "EQUALS" } }) {
    count
    scenes { id title rating100 }
  }
}
```

### Pattern 2: Find Old Content (N days)

Calculate threshold date, then query:
```graphql
query FindOld {
  findScenes(
    scene_filter: {
      created_at: { value: "YYYY-MM-DD", modifier: "LESS_THAN" }
    }
  ) {
    count
    scenes { id title created_at }
  }
}
```

### Pattern 3: Combined Criteria

```graphql
query FindCleanupCandidates {
  findScenes(
    scene_filter: {
      rating: { value: 50, modifier: "LESS_THAN" }
      o_counter: { value: 1, modifier: "LESS_THAN" }
      created_at: { value: "2025-01-01", modifier: "LESS_THAN" }
    }
  ) {
    count
    scenes { id title rating100 o_counter created_at }
  }
}
```

### Pattern 4: Delete Scene (Mutation)

```graphql
mutation DestroyScene($id: ID!) {
  sceneDestroy(id: $id)  # Returns Boolean
}
```

## Variables Pattern

For reusable queries, use GraphQL variables:

```graphql
query FindByFilter($rating_threshold: Int!, $days_old: String!) {
  findScenes(
    scene_filter: {
      rating: { value: $rating_threshold, modifier: "LESS_THAN" }
      created_at: { value: $days_old, modifier: "LESS_THAN" }
    }
  ) {
    count
    scenes { id title rating100 created_at }
  }
}
```

**Pass variables as JSON:**
```json
{
  "rating_threshold": 40,
  "days_old": "2026-02-05"
}
```

## Implementation Checklist

- [ ] Establish HTTP connection to GraphQL endpoint (default: http://localhost:9999/graphql)
- [ ] Build query builder that composes filter criteria from config
- [ ] Implement pagination loop for batch scene fetching
- [ ] Parse response JSON and extract scene IDs
- [ ] Validate deletion criteria before executing `sceneDestroy` mutation
- [ ] Log all deleted scene IDs for audit trail
- [ ] Handle GraphQL errors (invalid filters, auth failures, etc.)

## Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| Empty results | Wrong field names or filter values | Verify field names match schema exactly |
| Auth errors | Missing session/API key | Include authentication headers (cookie or bearer token) |
| Date filter fails | Incorrect date format | Use ISO 8601 format: "YYYY-MM-DD" |
| Slow queries | No server-side filtering | Use scene_filter to push filters to server |
| Delete fails silently | Scene ID invalid or permissions | Verify scene exists before delete mutation |

## Resources

- StashApp main repo: https://github.com/stashapp/stash
- Local playground: http://localhost:9999/playground (interactive query builder)
- GraphQL spec: https://graphql.org/learn/
- This project's query examples: `.squad/agents/roy/example_queries.md`

## Related Skills

- Python HTTP clients (requests, httpx)
- JSON parsing
- Date arithmetic (timedelta, strftime)
- Error handling and logging
