"""
Pytest fixtures for the blackbox testing harness.
"""

from typing import Generator

import pytest

from .client import BlackboxClient
from .cluster import PostgresClusterManager
from .harness import BlackboxTestHarness


@pytest.fixture(scope="session")
def blackbox_cluster() -> Generator[PostgresClusterManager, None, None]:
    """
    Session-scoped shared PostgreSQL DB cluster container managed by Podman.
    Ensures the cluster container is running.
    """
    cluster = PostgresClusterManager()
    cluster.start_cluster()
    yield cluster


@pytest.fixture(scope="session")
def blackbox_harness(
    blackbox_cluster: PostgresClusterManager,
) -> Generator[BlackboxTestHarness, None, None]:
    """
    Session-scoped blackbox test harness.
    For each test run:
    - Creates a clean test database on the shared PostgreSQL DB cluster.
    - Launches a unique test service instance dedicated to this run.
    - Tears down the unique test service and drops the clean test database on completion.
    """
    harness = BlackboxTestHarness(cluster=blackbox_cluster)
    harness.start()
    try:
        yield harness
    finally:
        harness.stop()


@pytest.fixture
def blackbox_client(blackbox_harness: BlackboxTestHarness) -> BlackboxClient:
    """HTTP client targeting the dedicated test service instance for this test run."""
    return blackbox_harness.client


@pytest.fixture
def blackbox_service_url(blackbox_harness: BlackboxTestHarness) -> str:
    """Base URL of the running test service."""
    return blackbox_harness.base_url


@pytest.fixture
def isolated_blackbox_harness(
    blackbox_cluster: PostgresClusterManager,
) -> Generator[BlackboxTestHarness, None, None]:
    """
    Function-scoped harness for tests requiring a strictly dedicated clean DB and service instance.
    """
    harness = BlackboxTestHarness(cluster=blackbox_cluster)
    harness.start()
    try:
        yield harness
    finally:
        harness.stop()
