"""Single responsibility: execute dry-run reporting or live scene deletion."""


class DeletionExecutor:
    """Performs dry-run logging or live deletion depending on the configured mode."""

    def __init__(self, client, dry_run: bool, deletion_scope: str) -> None:
        pass

    def execute(self, candidates: list[dict]) -> dict:
        """
        Process candidates.

        In dry-run mode: log what would be deleted, return report without mutating.
        In live mode: delete each candidate via the client and return a result report.
        """
        pass
