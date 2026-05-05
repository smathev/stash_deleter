"""
Unit tests for plugin/deletion_executor.py.

Verifies dry-run reporting and live deletion behaviour, including scope (db_only / with_file).
"""


class TestDeletionExecutor:
    """Tests for DeletionExecutor — dry-run and live deletion execution."""
