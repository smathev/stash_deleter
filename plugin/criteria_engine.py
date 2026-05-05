"""Single responsibility: evaluate scenes against configured deletion criteria."""


class CriteriaEngine:
    """Determines whether a scene matches the configured deletion criteria."""

    def __init__(self, criteria: dict) -> None:
        pass

    def find_candidates(self, client) -> list[dict]:
        """Query StashApp and return scenes that satisfy all configured criteria."""
        pass

    def is_candidate(self, scene: dict) -> bool:
        """Return True if the given scene satisfies every configured criterion."""
        pass
