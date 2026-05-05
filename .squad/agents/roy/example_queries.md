# StashApp GraphQL Example Queries

## Query 1: Find Scenes with 0 Rating and Play Count > 3

```graphql
query FindUnratedPopularScenes {
  findScenes(
    filter: {
      per_page: 100
      sort: "created_at"
      direction: "DESC"
    }
    scene_filter: {
      rating: { value: 0, modifier: "EQUALS" }
      o_counter: { value: 3, modifier: "GREATER_THAN" }
    }
  ) {
    count
    scenes {
      id
      title
      rating100
      o_counter
      created_at
      files {
        path
        size
        duration
      }
    }
  }
}
```

**Use case:** Find unpopular scenes that have been viewed frequently (might indicate low-quality content).

---

## Query 2: Find Scenes Not Played in 30 Days

```graphql
query FindUnplayedScenes {
  findScenes(
    filter: {
      per_page: 100
      sort: "last_played_at"
      direction: "ASC"
    }
    scene_filter: {
      last_played_at: {
        value: "2026-04-05"  # 30 days before query date (2026-05-05)
        modifier: "LESS_THAN"
      }
    }
  ) {
    count
    scenes {
      id
      title
      last_played_at
      o_counter
      created_at
      files {
        path
        duration
      }
    }
  }
}
```

**Use case:** Find scenes that haven't been viewed recently (candidate for cleanup).

---

## Query 3: Find Small, Unrated Scenes Created More Than 90 Days Ago

```graphql
query FindOldSmallScenes {
  findScenes(
    filter: {
      per_page: 100
      sort: "created_at"
      direction: "ASC"
    }
    scene_filter: {
      created_at: {
        value: "2026-02-05"  # 90 days before query date
        modifier: "LESS_THAN"
      }
      rating: { value: 0, modifier: "EQUALS" }
    }
  ) {
    count
    scenes {
      id
      title
      created_at
      rating100
      o_counter
      files {
        path
        size
        duration
      }
    }
  }
}
```

**Use case:** Find old, low-quality scenes to reclaim storage.

---

## Query 4: Full Scene Details for Deletion Decision

```graphql
query GetSceneForDeletion($id: ID!) {
  findScene(id: $id) {
    id
    title
    details
    created_at
    updated_at
    last_played_at
    o_counter
    rating100
    files {
      id
      path
      size
      duration
      video_codec
      audio_codec
      width
      height
    }
    performers {
      id
      name
    }
    tags {
      id
      name
    }
  }
}
```

**Use case:** Get full scene metadata before applying deletion logic.

---

## Mutation: Delete a Scene

```graphql
mutation DestroyScene($id: ID!) {
  sceneDestroy(id: $id)
}
```

**Alternative:** Some versions use `destroyScene(id: $id): Boolean`

**Important:** This is destructive and cannot be undone. Always confirm the scene ID before executing.

