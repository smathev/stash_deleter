# Gaff — Project History

## Project Context
- **Project:** stash_deleter — StashApp plugin for auto-deleting scenes based on configurable criteria
- **Stack:** Python 3, pytest (optional), mock GraphQL responses
- **User:** Smathev
- **Initialized:** 2026-05-05

## Test Strategy Notes
- Priority 1: dry-run mode never deletes — must be verified first
- Priority 2: each criterion fires only when it should
- Priority 3: edge cases (nulls, zeros, very new files)


## 2026-05-05T09:44:24+02:00 — Implemented CriteriaEngine (TDD)

### What was done
- Wrote **32 tests** in `tests/test_criteria_engine.py` covering all six criteria and the `find_candidates` integration path (RED first, then GREEN)
- Implemented `plugin/criteria_engine.py` with full criteria logic and GraphQL filter building
- All 50 tests in the suite pass

### Tests written
**`is_candidate` (pure logic, no mock):**
- `TestIsCandidateMinPlayCount` (3 tests): ≥ threshold, < threshold, exact
- `TestIsCandidateMaxPlayCount` (3 tests): ≤ threshold, > threshold, exact
- `TestIsCandidateRequireNoRating` (3 tests): None=pass, value=fail, **rating100=0 is rated (not None)**
- `TestIsCandidateRequireNoOCounter` (2 tests): 0=pass, >0=fail
- `TestIsCandidateDaysOnDisk` (4 tests): old+unplayed=pass, recent=fail, old+played=fail, exact age=pass
- `TestIsCandidateMaxRating` (4 tests): below=pass, above=fail, exact=pass, None=pass (skip criterion)
- `TestIsCandidateCombined` (2 tests): AND logic, empty rule=all pass
- `TestIsCandidateNeverDestructive` (1 test): idempotency over 5 calls

**`find_candidates` (mocked GraphQL client):**
- `test_find_candidates_never_calls_mutate` — **SAFETY TEST**: assert `client.mutate` never called
- Filter correctness for min_play_count, require_no_rating (IS_NULL), days_on_disk (play_count=0 only)
- Post-filter: GraphQL scenes not passing `is_candidate()` are excluded
- `per_page: -1` verified
- Empty criteria returns all scenes

### Safety enforcement
`find_candidates` calls only `client.execute()` — never `client.mutate()`. Verified by dedicated test.

### Design notes
- `_build_scene_filter()` — GraphQL filter only approximates criteria; `is_candidate()` post-filters for criteria that need in-memory logic (e.g., age calculation for `days_on_disk_without_play`)
- `require_no_rating` uses IS_NULL modifier as Roy confirmed — value comparison fails for rating100=0
- `max_rating100` skips unrated scenes (rating100=None) — None means "not rated", not "rated 0"

