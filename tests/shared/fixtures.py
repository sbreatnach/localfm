"""
Shared pytest fixtures for tests that need an isolated PostgreSQL-backed
Django database.
"""

from typing import Generator

import pytest

from .bootstrap import migrated_database
from .cluster import PostgresClusterManager
from .database import CleanDatabase


@pytest.fixture(scope="session")
def shared_cluster() -> Generator[PostgresClusterManager, None, None]:
    """Ensure the shared PostgreSQL cluster container is running."""
    cluster = PostgresClusterManager()
    cluster.start_cluster()
    yield cluster


@pytest.fixture
def migrated_db(
    shared_cluster: PostgresClusterManager,
    django_db_blocker,
) -> Generator[CleanDatabase, None, None]:
    """
    Function-scoped fixture providing a clean, migrated Django database.
    """
    with django_db_blocker.unblock():
        with migrated_database(shared_cluster) as db:
            yield db
