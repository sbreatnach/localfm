"""
Blackbox tests validating the LocalFM Ninja REST API endpoints.
"""

import pytest

from tests.blackbox.client import BlackboxClient
from tests.blackbox.cluster import PostgresClusterManager
from tests.blackbox.harness import BlackboxTestHarness


@pytest.mark.blackbox
def test_list_artists_empty(blackbox_client: BlackboxClient):
    """Verify that /api/v1/artists returns an empty paginated list on a clean database."""
    res = blackbox_client.get("/api/v1/artists")
    assert res.status_code == 200
    data = res.json()
    assert data["items"] == []
    assert data["count"] == 0


@pytest.mark.blackbox
def test_list_albums_empty(blackbox_client: BlackboxClient):
    """Verify that /api/v1/albums returns an empty paginated list on a clean database."""
    res = blackbox_client.get("/api/v1/albums")
    assert res.status_code == 200
    data = res.json()
    assert data["items"] == []
    assert data["count"] == 0


@pytest.mark.blackbox
def test_list_genres_empty(blackbox_client: BlackboxClient):
    """Verify that /api/v1/genres returns an empty paginated list on a clean database."""
    res = blackbox_client.get("/api/v1/genres")
    assert res.status_code == 200
    data = res.json()
    assert data["items"] == []
    assert data["count"] == 0


@pytest.mark.blackbox
def test_list_tracks_empty(blackbox_client: BlackboxClient):
    """Verify that /api/v1/tracks returns an empty paginated list on a clean database."""
    res = blackbox_client.get("/api/v1/tracks")
    assert res.status_code == 200
    data = res.json()
    assert data["items"] == []
    assert data["count"] == 0


@pytest.mark.blackbox
def test_list_track_plays_empty(blackbox_client: BlackboxClient):
    """Verify that /api/v1/track-plays returns an empty paginated list on a clean database."""
    res = blackbox_client.get("/api/v1/track-plays")
    assert res.status_code == 200
    data = res.json()
    assert data["items"] == []
    assert data["count"] == 0


@pytest.mark.blackbox
def test_data_isolation_between_test_runs(
    blackbox_cluster: PostgresClusterManager,
):
    """
    Verify that data populated in one clean test database is completely isolated
    and not visible in a separate test run with a new clean database.
    """
    # 1. Start first test run, insert an artist into its database
    harness_1 = BlackboxTestHarness(cluster=blackbox_cluster)
    with harness_1:
        with harness_1.get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO tracks_artist (name) VALUES (%s);", ("Radiohead",)
                )

        # Verify artist is returned by API
        res1 = harness_1.client.get("/api/v1/artists")
        assert res1.status_code == 200
        items = res1.json()["items"]
        assert len(items) == 1
        assert items[0]["name"] == "Radiohead"

    # 2. Start a second test run with a fresh clean database
    harness_2 = BlackboxTestHarness(cluster=blackbox_cluster)
    with harness_2:
        # Verify second run has completely clean state (Radiohead is NOT present)
        res2 = harness_2.client.get("/api/v1/artists")
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["items"] == []
        assert data2["count"] == 0
