"""
Integration tests for the localfm track library importer.
"""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from django.conf import settings
from django.db import IntegrityError

from localfm.tracks import library
from localfm.tracks.models import Album, Artist, Genre, Track

FIXTURES_DIR = Path(settings.BASE_DIR) / "tests" / "fixtures"


def test_import_file_updates_database(migrated_db):
    """Importing the fixture MP3s should populate tracks, artists and albums."""
    for filename in ("test_1.mp3", "test_2.mp3"):
        library.import_file(str(FIXTURES_DIR / filename))

    assert Track.objects.count() == 2
    assert Artist.objects.count() == 3
    assert Album.objects.count() == 2
    assert Genre.objects.count() == 1

    track_1 = Track.objects.get(name="Act Of The Apostle II")
    assert track_1.artist.name == "Belle & Sebastian"
    assert track_1.album.name == "The Life Pursuit"
    assert track_1.album.genre.name == "Alternative"
    assert track_1.track_number == 11

    track_2 = Track.objects.get(name="Kazucuta")
    assert track_2.artist.name == "Os Bongos"
    assert (
        track_2.album.name
        == "Angola Soundtrack - The Unique Sound Of Luanda 1968-1976 (Analog Africa Nr. 9)"
    )
    assert track_2.album.album_artist.name == "Analog Africa"
    assert track_2.track_number == 15


def test_import_file_with_leading_empty_id3_frame(migrated_db):
    """A zero-sized ID3 frame before the metadata frames should still import."""
    library.import_file(str(FIXTURES_DIR / "test_3.mp3"))

    assert Track.objects.count() == 1
    assert Artist.objects.count() == 1
    assert Album.objects.count() == 1
    assert Genre.objects.count() == 1

    track = Track.objects.get(name="Elderly Woman Behind the Counter in a Small Town")
    assert track.artist.name == "Pearl Jam"
    assert track.album.name == "Vs."
    assert track.album.album_artist.name == "Pearl Jam"
    assert track.album.genre.name == "Rock"
    assert track.track_number == 10


def test_album_get_or_create_recovers_from_concurrent_insert(migrated_db, monkeypatch):
    """A losing race to create an album should return the winner's row."""
    tagged_data = SimpleNamespace(
        filename="track.mp3",
        album="Race Album",
        albumartist="Album Artist",
        artist="Track Artist",
        genre="Rock",
        disc=None,
    )
    identifier = Album.generate_identifier(
        tagged_data.album,
        album_artist_name=tagged_data.albumartist,
        artist_name=tagged_data.artist,
        genre=tagged_data.genre,
        disc_number=tagged_data.disc,
    )

    artist = Artist.objects.create(name=tagged_data.artist)
    album_artist = Artist.objects.create(name=tagged_data.albumartist)
    genre = Genre.objects.create(name=tagged_data.genre)
    existing_album = Album.objects.create(
        name=tagged_data.album,
        artist=artist,
        album_artist=album_artist,
        genre=genre,
        hashed_identifier=identifier,
    )

    def raise_integrity_error(*_args, **_kwargs):
        raise IntegrityError(
            "duplicate key value violates unique constraint "
            '"tracks_album_hashed_identifier_key"'
        )

    # Simulate another thread creating the album after the initial lookup but
    # before this thread's create completes.
    filter_results = iter([None, existing_album])

    def fake_filter(*_args, **_kwargs):
        queryset = Mock()
        queryset.first.return_value = next(filter_results)
        return queryset

    monkeypatch.setattr(Album.objects, "filter", fake_filter)
    monkeypatch.setattr(Album.objects, "create", raise_integrity_error)

    assert Album.get_or_create_by_tagged_data(tagged_data) == existing_album
