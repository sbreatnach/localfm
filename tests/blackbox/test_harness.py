"""
Tests validating the blackbox testing harness itself.
"""

import pytest

from tests.blackbox.cluster import PostgresClusterManager
from tests.blackbox.database import CleanDatabase
from tests.blackbox.harness import BlackboxTestHarness


@pytest.mark.blackbox
def test_clean_database_lifecycle(blackbox_cluster: PostgresClusterManager):
    """Verify that CleanDatabase creates a database and completely tears it down."""
    db = CleanDatabase(cluster=blackbox_cluster)
    assert not blackbox_cluster.database_exists(db.name)

    with db:
        assert blackbox_cluster.database_exists(db.name)
        # Verify connection can be made to the new clean database
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT current_database();")
                row = cur.fetchone()
                assert row[0] == db.name

    # After exiting context, the database must be dropped
    assert not blackbox_cluster.database_exists(db.name)


@pytest.mark.blackbox
def test_harness_container_mode(blackbox_cluster: PostgresClusterManager):
    """Verify that BlackboxTestHarness works in Container mode and tears down cleanly."""
    harness = BlackboxTestHarness(cluster=blackbox_cluster, service_type="container")
    with harness:
        db_name = harness.db_name
        assert blackbox_cluster.database_exists(db_name)

        # Service must be reachable via HTTP
        response = harness.client.get("/tracks")
        assert response.status_code == 200

        api_response = harness.client.get("/api/v1/artists")
        assert api_response.status_code == 200
        assert api_response.json() == {"items": [], "count": 0}

    # After harness teardown, database must be dropped
    assert not blackbox_cluster.database_exists(db_name)
    # Service must no longer be responding
    assert not harness.service._is_running


@pytest.mark.blackbox
def test_harness_process_mode(blackbox_cluster: PostgresClusterManager):
    """Verify that BlackboxTestHarness works in Process mode and tears down cleanly."""
    harness = BlackboxTestHarness(cluster=blackbox_cluster, service_type="process")
    with harness:
        db_name = harness.db_name
        assert blackbox_cluster.database_exists(db_name)

        # Service must be reachable via HTTP
        response = harness.client.get("/tracks")
        assert response.status_code == 200

        api_response = harness.client.get("/api/v1/artists")
        assert api_response.status_code == 200
        assert api_response.json() == {"items": [], "count": 0}

    # After harness teardown, database must be dropped
    assert not blackbox_cluster.database_exists(db_name)
    assert not harness.service._is_running
