"""Single responsibility: execute dry-run tagging per rule (deletion is not implemented)."""

from plugin.criteria_engine import CriteriaEngine

_TAG_PREFIX = "stash-deleter:candidate:"

# GraphQL mutations — tag-safe writes only (no scene destruction)
_TAG_CREATE_MUTATION = """
mutation TagCreate($input: TagCreateInput!) {
  tagCreate(input: $input) { id name }
}
"""

_SCENE_UPDATE_MUTATION = """
mutation SceneUpdate($input: SceneUpdateInput!) {
  sceneUpdate(input: $input) { id tag_ids }
}
"""

_FIND_TAG_QUERY = """
query FindTag($name: String!) {
  allTags { id name }
}
"""

_SCENE_TAGS_QUERY = """
query SceneTags($id: ID!) {
  findScene(id: $id) { id tags { id } }
}
"""


class DeletionExecutor:
    """
    Performs dry-run candidate tagging for each enabled rule.

    Dry run per rule:
      - Builds a CriteriaEngine for the rule
      - Calls find_candidates(client) to get matching scenes
      - Ensures the tag stash-deleter:candidate:{rule_name} exists
      - Tags each candidate scene (appending to existing tags — never replacing)

    Deletion is explicitly NOT implemented. This class will raise NotImplementedError
    if mode != "dry_run" to enforce the safety boundary.

    Tag pattern: stash-deleter:candidate:{rule_name}
    """

    def __init__(self, client, deletion_scope: str) -> None:
        self._client = client
        self._deletion_scope = deletion_scope
        self._tag_id_cache: dict[str, str] = {}

    def run_rules(self, rules: list[dict], mode: str) -> dict:
        """
        Iterate over enabled rules, find candidates, tag them (dry_run only).

        Args:
            rules: list of rule dicts from ConfigLoader (ALL rules — we filter enabled here)
            mode: must be "dry_run" — "delete" raises NotImplementedError

        Returns:
            {
                "mode": str,
                "rules": [...per-rule result dicts...],
                "summary": str,
            }
        """
        if mode != "dry_run":
            raise NotImplementedError(
                "Deletion mode is not implemented. Only 'dry_run' is supported."
            )

        rule_results = []
        total_candidates = 0

        for rule in rules:
            if not rule.get("enabled", True):
                continue
            result = self._run_single_rule_dry(rule)
            rule_results.append(result)
            total_candidates += result["candidate_count"]

        summary = (
            f"Dry run complete. {total_candidates} candidate(s) across "
            f"{len(rule_results)} rule(s). "
            "Filter by tag 'stash-deleter:candidate:<rule_name>' to review."
        )

        return {"mode": mode, "rules": rule_results, "summary": summary}

    def clear_candidate_tags(self) -> None:
        """Not used in dry-run — reserved for future delete sprint."""
        raise NotImplementedError(
            "clear_candidate_tags() is reserved for the deletion sprint. "
            "Not available in dry-run only mode."
        )

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _run_single_rule_dry(self, rule: dict) -> dict:
        """Find candidates for one rule and tag each scene."""
        engine = CriteriaEngine(rule)
        candidates = engine.find_candidates(self._client)
        tag_name = f"{_TAG_PREFIX}{rule['name']}"
        tag_id = self._ensure_tag(tag_name)

        failed = []
        for scene in candidates:
            try:
                self._tag_scene(scene["id"], tag_id)
            except Exception as exc:  # noqa: BLE001
                failed.append({"scene_id": scene["id"], "error": str(exc)})

        return {
            "name": rule["name"],
            "candidate_count": len(candidates),
            "candidate_tag": tag_name,
            "failed": failed,
        }

    def _ensure_tag(self, tag_name: str) -> str:
        """Return existing tag ID or create a new tag. Caches results."""
        if tag_name in self._tag_id_cache:
            return self._tag_id_cache[tag_name]

        # Fetch all tags to check existence (StashApp has no findTagByName)
        data = self._client.query(_FIND_TAG_QUERY, variables={"name": tag_name})
        existing = {t["name"]: t["id"] for t in data.get("allTags", [])}

        if tag_name in existing:
            tag_id = existing[tag_name]
        else:
            result = self._client.mutate(
                _TAG_CREATE_MUTATION,
                variables={"input": {"name": tag_name}},
            )
            tag_id = result["tagCreate"]["id"]

        self._tag_id_cache[tag_name] = tag_id
        return tag_id

    def _tag_scene(self, scene_id: str, tag_id: str) -> None:
        """Append tag_id to scene's existing tags — never replaces other tags."""
        data = self._client.query(
            _SCENE_TAGS_QUERY, variables={"id": scene_id}
        )
        existing_tag_ids = [t["id"] for t in data["findScene"]["tags"]]
        if tag_id in existing_tag_ids:
            return  # already tagged — idempotent

        updated_tag_ids = existing_tag_ids + [tag_id]
        self._client.mutate(
            _SCENE_UPDATE_MUTATION,
            variables={"input": {"id": scene_id, "tag_ids": updated_tag_ids}},
        )
