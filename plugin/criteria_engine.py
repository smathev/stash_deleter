"""Single responsibility: evaluate scenes against configured deletion criteria."""
from datetime import datetime, timezone, timedelta


_FIND_CANDIDATES_QUERY = """
query FindCandidates($scene_filter: SceneFilterType, $filter: FindFilterType) {
  findScenes(scene_filter: $scene_filter, filter: $filter) {
    count
    scenes {
      id
      title
      path
      play_count
      o_counter
      rating100
      last_played_at
      created_at
      files { size duration }
    }
  }
}
"""


class CriteriaEngine:
    """Determines whether a scene matches the configured deletion criteria."""

    def __init__(self, criteria: dict) -> None:
        self._criteria = criteria

    def find_candidates(self, client) -> list[dict]:
        """Query StashApp and return scenes that satisfy all configured criteria."""
        scene_filter = self._build_scene_filter()
        variables = {
            "filter": {"per_page": -1},
            "scene_filter": scene_filter,
        }
        result = client.query(_FIND_CANDIDATES_QUERY, variables=variables)
        scenes = result["findScenes"]["scenes"]
        return [s for s in scenes if self.is_candidate(s)]

    def is_candidate(self, scene: dict) -> bool:
        """Return True if the given scene satisfies every configured criterion."""
        return (
            self._check_min_play_count(scene)
            and self._check_max_play_count(scene)
            and self._check_require_no_rating(scene)
            and self._check_require_no_o_counter(scene)
            and self._check_days_on_disk_without_play(scene)
            and self._check_max_rating100(scene)
        )

    # ------------------------------------------------------------------
    # Private: per-criterion checks
    # ------------------------------------------------------------------

    def _check_min_play_count(self, scene: dict) -> bool:
        threshold = self._criteria.get("min_play_count")
        if threshold is None:
            return True
        return scene["play_count"] >= threshold

    def _check_max_play_count(self, scene: dict) -> bool:
        threshold = self._criteria.get("max_play_count")
        if threshold is None:
            return True
        return scene["play_count"] <= threshold

    def _check_require_no_rating(self, scene: dict) -> bool:
        if not self._criteria.get("require_no_rating"):
            return True
        return scene["rating100"] is None

    def _check_require_no_o_counter(self, scene: dict) -> bool:
        if not self._criteria.get("require_no_o_counter"):
            return True
        return scene["o_counter"] == 0

    def _check_days_on_disk_without_play(self, scene: dict) -> bool:
        days = self._criteria.get("days_on_disk_without_play")
        if days is None:
            return True
        if scene["play_count"] != 0:
            return False
        created = datetime.fromisoformat(scene["created_at"].replace("Z", "+00:00"))
        age_days = (datetime.now(timezone.utc) - created).days
        return age_days >= days

    def _check_max_rating100(self, scene: dict) -> bool:
        max_rating = self._criteria.get("max_rating100")
        if max_rating is None:
            return True
        if scene["rating100"] is None:
            return True  # unrated scenes are not excluded by this criterion
        return scene["rating100"] <= max_rating

    # ------------------------------------------------------------------
    # Private: GraphQL filter building
    # ------------------------------------------------------------------

    def _build_scene_filter(self) -> dict:
        scene_filter: dict = {}
        if "min_play_count" in self._criteria:
            scene_filter["play_count"] = {
                "value": self._criteria["min_play_count"],
                "modifier": "GREATER_THAN_EQUALS",
            }
        if "max_play_count" in self._criteria:
            scene_filter["play_count"] = {
                "value": self._criteria["max_play_count"],
                "modifier": "LESS_THAN_EQUALS",
            }
        if self._criteria.get("require_no_rating"):
            scene_filter["rating100"] = {"modifier": "IS_NULL"}
        if self._criteria.get("require_no_o_counter"):
            scene_filter["o_counter"] = {"value": 0, "modifier": "EQUALS"}
        if "days_on_disk_without_play" in self._criteria:
            scene_filter["play_count"] = {"value": 0, "modifier": "EQUALS"}
        if "max_rating100" in self._criteria:
            scene_filter["rating100"] = {
                "value": self._criteria["max_rating100"],
                "modifier": "LESS_THAN_EQUALS",
            }
        return scene_filter
