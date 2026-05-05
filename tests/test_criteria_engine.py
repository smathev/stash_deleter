"""
Unit tests for plugin/criteria_engine.py.

Verifies scene-candidate evaluation against each supported criterion.
Tests are ordered by TDD phase: is_candidate (pure logic) then find_candidates (mocked client).
"""
import sys
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, call, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "plugin"))

from criteria_engine import CriteriaEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _scene(**overrides):
    """Return a minimal valid scene dict with safe defaults."""
    base = {
        "id": "1",
        "title": "Test Scene",
        "path": "/data/test.mp4",
        "play_count": 0,
        "o_counter": 0,
        "rating100": None,
        "last_played_at": None,
        "created_at": "2020-01-01T00:00:00Z",
        "files": [{"size": 1073741824, "duration": 3600.0}],
    }
    base.update(overrides)
    return base


def _days_ago(n: int) -> str:
    """Return an ISO-8601 UTC timestamp n days in the past."""
    dt = datetime.now(timezone.utc) - timedelta(days=n)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _mock_client(scenes: list[dict]):
    """Return a mock GraphQL client whose execute() returns the given scenes."""
    client = MagicMock()
    client.query.return_value = {
        "findScenes": {
            "count": len(scenes),
            "scenes": scenes,
        }
    }
    return client


# ===========================================================================
# TestIsCandidateMinPlayCount
# ===========================================================================

class TestIsCandidateMinPlayCount:
    """is_candidate — min_play_count criterion."""

    def test_scene_with_enough_plays_is_candidate(self):
        engine = CriteriaEngine({"min_play_count": 3})
        assert engine.is_candidate(_scene(play_count=5)) is True

    def test_scene_with_too_few_plays_is_not_candidate(self):
        engine = CriteriaEngine({"min_play_count": 3})
        assert engine.is_candidate(_scene(play_count=2)) is False

    def test_scene_with_exact_threshold_is_candidate(self):
        engine = CriteriaEngine({"min_play_count": 3})
        assert engine.is_candidate(_scene(play_count=3)) is True


# ===========================================================================
# TestIsCandidateMaxPlayCount
# ===========================================================================

class TestIsCandidateMaxPlayCount:
    """is_candidate — max_play_count criterion."""

    def test_scene_below_max_play_count_is_candidate(self):
        engine = CriteriaEngine({"max_play_count": 10})
        assert engine.is_candidate(_scene(play_count=5)) is True

    def test_scene_above_max_play_count_is_not_candidate(self):
        engine = CriteriaEngine({"max_play_count": 10})
        assert engine.is_candidate(_scene(play_count=11)) is False

    def test_scene_at_exact_max_play_count_is_candidate(self):
        engine = CriteriaEngine({"max_play_count": 10})
        assert engine.is_candidate(_scene(play_count=10)) is True


# ===========================================================================
# TestIsCandidateRequireNoRating
# ===========================================================================

class TestIsCandidateRequireNoRating:
    """is_candidate — require_no_rating criterion."""

    def test_unrated_scene_is_candidate(self):
        engine = CriteriaEngine({"require_no_rating": True})
        assert engine.is_candidate(_scene(rating100=None)) is True

    def test_rated_scene_is_not_candidate(self):
        engine = CriteriaEngine({"require_no_rating": True})
        assert engine.is_candidate(_scene(rating100=75)) is False

    def test_zero_rating_is_not_treated_as_unrated(self):
        """rating100=0 is a valid rating of 0, not absence of rating."""
        engine = CriteriaEngine({"require_no_rating": True})
        assert engine.is_candidate(_scene(rating100=0)) is False


# ===========================================================================
# TestIsCandidateRequireNoOCounter
# ===========================================================================

class TestIsCandidateRequireNoOCounter:
    """is_candidate — require_no_o_counter criterion."""

    def test_scene_with_o_counter_zero_is_candidate(self):
        engine = CriteriaEngine({"require_no_o_counter": True})
        assert engine.is_candidate(_scene(o_counter=0)) is True

    def test_scene_with_o_counter_above_zero_is_not_candidate(self):
        engine = CriteriaEngine({"require_no_o_counter": True})
        assert engine.is_candidate(_scene(o_counter=1)) is False


# ===========================================================================
# TestIsCandidateDaysOnDisk
# ===========================================================================

class TestIsCandidateDaysOnDisk:
    """is_candidate — days_on_disk_without_play criterion."""

    def test_old_unplayed_scene_is_candidate(self):
        engine = CriteriaEngine({"days_on_disk_without_play": 30})
        scene = _scene(play_count=0, created_at=_days_ago(60))
        assert engine.is_candidate(scene) is True

    def test_recent_unplayed_scene_is_not_candidate(self):
        engine = CriteriaEngine({"days_on_disk_without_play": 30})
        scene = _scene(play_count=0, created_at=_days_ago(10))
        assert engine.is_candidate(scene) is False

    def test_played_scene_is_not_candidate_even_if_old(self):
        """play_count > 0 disqualifies even an ancient file."""
        engine = CriteriaEngine({"days_on_disk_without_play": 30})
        scene = _scene(play_count=5, created_at=_days_ago(365))
        assert engine.is_candidate(scene) is False

    def test_scene_at_exact_age_threshold_is_candidate(self):
        engine = CriteriaEngine({"days_on_disk_without_play": 30})
        scene = _scene(play_count=0, created_at=_days_ago(30))
        assert engine.is_candidate(scene) is True


# ===========================================================================
# TestIsCandidateMaxRating
# ===========================================================================

class TestIsCandidateMaxRating:
    """is_candidate — max_rating100 criterion."""

    def test_scene_below_max_rating_is_candidate(self):
        engine = CriteriaEngine({"max_rating100": 50})
        assert engine.is_candidate(_scene(rating100=40)) is True

    def test_scene_above_max_rating_is_not_candidate(self):
        engine = CriteriaEngine({"max_rating100": 50})
        assert engine.is_candidate(_scene(rating100=60)) is False

    def test_scene_at_exact_max_rating_is_candidate(self):
        engine = CriteriaEngine({"max_rating100": 50})
        assert engine.is_candidate(_scene(rating100=50)) is True

    def test_unrated_scene_passes_max_rating_check(self):
        """None rating means unrated; the max_rating100 criterion is skipped."""
        engine = CriteriaEngine({"max_rating100": 50})
        assert engine.is_candidate(_scene(rating100=None)) is True


# ===========================================================================
# TestIsCandidateCombined
# ===========================================================================

class TestIsCandidateCombined:
    """is_candidate — multiple criteria must ALL pass."""

    def test_all_criteria_must_pass(self):
        engine = CriteriaEngine({"min_play_count": 4, "require_no_rating": True})
        # Both criteria satisfied
        assert engine.is_candidate(_scene(play_count=5, rating100=None)) is True
        # Only play_count satisfied
        assert engine.is_candidate(_scene(play_count=5, rating100=75)) is False
        # Only require_no_rating satisfied
        assert engine.is_candidate(_scene(play_count=2, rating100=None)) is False

    def test_none_criteria_always_passes(self):
        """An empty rule dict means every scene is a candidate."""
        engine = CriteriaEngine({})
        assert engine.is_candidate(_scene()) is True
        assert engine.is_candidate(_scene(play_count=999, rating100=100, o_counter=5)) is True


# ===========================================================================
# TestIsCandidateNeverDestructive
# ===========================================================================

class TestIsCandidateNeverDestructive:
    """is_candidate must have no side effects."""

    def test_is_candidate_has_no_side_effects(self):
        """Calling is_candidate repeatedly must return identical results."""
        engine = CriteriaEngine({"min_play_count": 2, "require_no_rating": True})
        scene = _scene(play_count=5, rating100=None)
        results = [engine.is_candidate(scene) for _ in range(5)]
        assert all(r is True for r in results)
        assert results == [True, True, True, True, True]


# ===========================================================================
# TestFindCandidates
# ===========================================================================

class TestFindCandidates:
    """find_candidates — GraphQL integration with a mocked client."""

    FIND_SCENES_QUERY_FRAGMENT = "findScenes"

    def test_find_candidates_calls_findScenes_query(self):
        client = _mock_client([])
        engine = CriteriaEngine({"min_play_count": 1})
        engine.find_candidates(client)
        client.query.assert_called_once()
        query_arg = client.query.call_args[0][0]
        assert self.FIND_SCENES_QUERY_FRAGMENT in query_arg

    def test_find_candidates_never_calls_mutate(self):
        """SAFETY: candidate discovery must NEVER call any mutation."""
        client = _mock_client([])
        engine = CriteriaEngine({"min_play_count": 1})
        engine.find_candidates(client)
        client.mutate.assert_not_called()

    def test_find_candidates_returns_matching_scenes(self):
        scene = _scene(play_count=5, rating100=None)
        client = _mock_client([scene])
        engine = CriteriaEngine({"min_play_count": 4})
        result = engine.find_candidates(client)
        assert result == [scene]

    def test_find_candidates_post_filters_with_is_candidate(self):
        """Scenes returned by GraphQL that fail is_candidate are excluded."""
        passing = _scene(id="1", play_count=5)
        failing = _scene(id="2", play_count=1)
        client = _mock_client([passing, failing])
        engine = CriteriaEngine({"min_play_count": 4})
        result = engine.find_candidates(client)
        assert len(result) == 1
        assert result[0]["id"] == "1"

    def test_find_candidates_returns_empty_list_when_no_matches(self):
        client = _mock_client([])
        engine = CriteriaEngine({"min_play_count": 999})
        result = engine.find_candidates(client)
        assert result == []

    def test_find_candidates_builds_correct_filter_for_min_play_count(self):
        client = _mock_client([])
        engine = CriteriaEngine({"min_play_count": 5})
        engine.find_candidates(client)
        _, kwargs = client.query.call_args
        variables = kwargs.get("variables") or client.query.call_args[0][1]
        scene_filter = variables["scene_filter"]
        assert scene_filter["play_count"] == {"value": 5, "modifier": "GREATER_THAN_EQUALS"}

    def test_find_candidates_builds_correct_filter_for_require_no_rating(self):
        """Must use IS_NULL modifier — NOT value comparison (Roy's confirmed gotcha)."""
        client = _mock_client([])
        engine = CriteriaEngine({"require_no_rating": True})
        engine.find_candidates(client)
        _, kwargs = client.query.call_args
        variables = kwargs.get("variables") or client.query.call_args[0][1]
        scene_filter = variables["scene_filter"]
        assert scene_filter["rating100"] == {"modifier": "IS_NULL"}

    def test_find_candidates_builds_correct_filter_for_days_on_disk(self):
        """days_on_disk_without_play → GraphQL filter is play_count=0; age is post-filtered."""
        client = _mock_client([])
        engine = CriteriaEngine({"days_on_disk_without_play": 30})
        engine.find_candidates(client)
        _, kwargs = client.query.call_args
        variables = kwargs.get("variables") or client.query.call_args[0][1]
        scene_filter = variables["scene_filter"]
        assert scene_filter["play_count"] == {"value": 0, "modifier": "EQUALS"}

    def test_empty_criteria_returns_all_scenes(self):
        """No criteria → no scene_filter restrictions → all scenes returned."""
        scenes = [_scene(id=str(i)) for i in range(3)]
        client = _mock_client(scenes)
        engine = CriteriaEngine({})
        result = engine.find_candidates(client)
        assert len(result) == 3

    def test_find_candidates_passes_per_page_minus_one(self):
        """Must request all scenes in one shot: filter.per_page = -1."""
        client = _mock_client([])
        engine = CriteriaEngine({})
        engine.find_candidates(client)
        _, kwargs = client.query.call_args
        variables = kwargs.get("variables") or client.query.call_args[0][1]
        assert variables["filter"]["per_page"] == -1
