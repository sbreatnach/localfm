"""
Blackbox tests validating the web views and Last.fm bridge endpoints.
"""

import pytest

from tests.blackbox.client import BlackboxClient


@pytest.mark.blackbox
def test_tracks_html_page(blackbox_client: BlackboxClient):
    """Verify that GET /tracks returns 200 OK with the HTML layout."""
    res = blackbox_client.get("/tracks")
    assert res.status_code == 200
    assert "text/html" in res.headers.get("content-type", "")
    content = res.text
    assert "<title>My tracks</title>" in content
    assert 'id="track-plays"' in content
    assert 'id="top-albums"' in content
    assert 'id="top-tracks"' in content


@pytest.mark.blackbox
def test_tracks_css_stylesheet(blackbox_client: BlackboxClient):
    """Verify that the tabs stylesheet referenced by /tracks returns 200 OK with text/css."""
    res = blackbox_client.get("/tracksstyles/tabs.css")
    assert res.status_code == 200
    assert "text/css" in res.headers.get("content-type", "")


@pytest.mark.blackbox
def test_bridge_endpoint_methods(blackbox_client: BlackboxClient):
    """Verify the Last.fm bridge API endpoint at /2.0 handles requests properly."""
    # GET request is not allowed on /2.0 (only POST)
    get_res = blackbox_client.get("/2.0")
    assert get_res.status_code == 400

    # POST with unsupported method parameter returns 404
    post_invalid = blackbox_client.post("/2.0", data={"method": "invalid.action"})
    assert post_invalid.status_code == 404

    # POST with supported method but without authentication credentials returns 403
    post_unauth = blackbox_client.post("/2.0", data={"method": "track.scrobble"})
    assert post_unauth.status_code == 403
