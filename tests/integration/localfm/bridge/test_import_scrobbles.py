"""
Integration tests for the scrobble import management command.
"""

import json

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from localfm.tracks.models import TrackPlay

from tests.shared.factories import AlbumFactory, ArtistFactory, TrackFactory


def write_scrobble_file(path, scrobbles):
    path.write_text(json.dumps(scrobbles), encoding="utf-8")


def test_import_scrobbles_accepts_globbed_sources(migrated_db, tmp_path):
    """A quoted glob should import every matching scrobble file."""
    artist = ArtistFactory(name="Smashing Pumpkins")
    album = AlbumFactory(
        name="Singles (Original Motion Picture Soundtrack)", artist=artist
    )
    track = TrackFactory(artist=artist, album=album, name="Drown")

    write_scrobble_file(
        tmp_path / "scrobbles_20261123.json",
        [
            [
                "The Smashing Pumpkins",
                album.name,
                track.name,
                "2026-11-23T15:21:12+00:00",
            ]
        ],
    )
    write_scrobble_file(
        tmp_path / "scrobbles_20261124.json",
        [
            [
                "Smashing Pumpkins",
                album.name,
                track.name,
                "2026-11-24T15:21:12+00:00",
            ]
        ],
    )

    call_command(
        "import_scrobbles",
        str(tmp_path / "scrobbles_*.json"),
        "database",
        log_level="WARNING",
    )

    assert TrackPlay.objects.filter(track=track).count() == 2
    track.refresh_from_db()
    assert track.play_count == 2


def test_import_scrobbles_accepts_multiple_sources_before_target(migrated_db, tmp_path):
    """Multiple explicit source files should work with database as the last argument."""
    artist = ArtistFactory(name="Fleetwood Mac")
    album = AlbumFactory(name="Mystery To Me", artist=artist, album_artist=None)
    first_track = TrackFactory(artist=artist, album=album, name="Hypnotized")
    second_track = TrackFactory(artist=artist, album=album, name="Emerald Eyes")

    first_file = tmp_path / "first.json"
    second_file = tmp_path / "second.json"
    write_scrobble_file(
        first_file,
        [["Fleetwood Mac", album.name, first_track.name, "2026-11-26T17:26:46+00:00"]],
    )
    write_scrobble_file(
        second_file,
        [["Fleetwood Mac", album.name, second_track.name, "2026-11-26T17:14:18+00:00"]],
    )

    call_command(
        "import_scrobbles",
        str(first_file),
        str(second_file),
        "database",
        log_level="WARNING",
    )

    assert TrackPlay.objects.filter(track=first_track).count() == 1
    assert TrackPlay.objects.filter(track=second_track).count() == 1


def test_import_scrobbles_combines_sources_into_target_file(tmp_path):
    """When the target is a file, all sources should be combined into it."""
    first_file = tmp_path / "first.json"
    second_file = tmp_path / "second.json"
    output_file = tmp_path / "combined.json"
    write_scrobble_file(
        first_file,
        [["Artist", "Album", "Track One", "2026-11-23T15:21:12+00:00"]],
    )
    write_scrobble_file(
        second_file,
        [["Artist", "Album", "Track Two", "2026-11-24T15:21:12+00:00"]],
    )

    call_command(
        "import_scrobbles",
        str(first_file),
        str(second_file),
        str(output_file),
        log_level="WARNING",
    )

    combined_scrobbles = json.loads(output_file.read_text(encoding="utf-8"))
    assert [scrobble[2] for scrobble in combined_scrobbles] == [
        "Track One",
        "Track Two",
    ]


def test_import_scrobbles_rejects_unmatched_glob(migrated_db, tmp_path):
    with pytest.raises(CommandError, match="No scrobble files match"):
        call_command(
            "import_scrobbles",
            str(tmp_path / "missing_*.json"),
            "database",
            log_level="WARNING",
        )


def test_import_scrobbles_rejects_lastfm_with_files(migrated_db, tmp_path):
    scrobble_file = tmp_path / "scrobbles.json"
    write_scrobble_file(
        scrobble_file,
        [["Artist", "Album", "Track", "2026-11-23T15:21:12+00:00"]],
    )

    with pytest.raises(CommandError, match="cannot be combined"):
        call_command(
            "import_scrobbles",
            "lastfm",
            str(scrobble_file),
            "database",
            log_level="WARNING",
        )
