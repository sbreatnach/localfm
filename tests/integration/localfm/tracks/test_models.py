"""
Integration tests for the top-albums report query.
"""

from localfm.tracks.models import Album

from tests.shared.factories import (
    AlbumFactory,
    ArtistFactory,
    TrackFactory,
    TrackPlayFactory,
)


def test_list_with_play_count_includes_albums_without_album_artist(migrated_db):
    """Albums with no album-artist tag should still appear in the report."""
    artist = ArtistFactory(name="Fleetwood Mac")
    album = AlbumFactory(name="Mystery To Me", artist=artist, album_artist=None)
    track = TrackFactory(album=album, artist=artist, name="Hypnotized")
    TrackPlayFactory.create_batch(2, track=track)

    reported_albums = list(Album.list_with_play_count())

    assert [reported.id for reported in reported_albums] == [album.id]
    assert reported_albums[0].artist_name == "Fleetwood Mac"


def test_list_with_play_count_prefers_album_artist_when_present(migrated_db):
    """The report should use the album artist for naming when it is set."""
    track_artist = ArtistFactory(name="Fleetwood Mac")
    album_artist = ArtistFactory(name="Various Artists")
    album = AlbumFactory(
        name="Compilation Album",
        artist=track_artist,
        album_artist=album_artist,
    )
    track = TrackFactory(album=album, artist=track_artist, name="Some Track")
    TrackPlayFactory(track=track)

    reported_albums = list(Album.list_with_play_count())

    assert reported_albums[0].artist_name == "Various Artists"


def test_list_with_play_count_uses_integer_average(migrated_db):
    """The average should retain the existing integer-division behaviour."""
    artist = ArtistFactory(name="Fleetwood Mac")
    album = AlbumFactory(name="Kiln House", artist=artist, album_artist=None)
    station_man = TrackFactory(album=album, artist=artist, name="Station Man")
    blood_on_the_floor = TrackFactory(
        album=album, artist=artist, name="Blood On The Floor"
    )
    TrackPlayFactory.create_batch(2, track=station_man)
    TrackPlayFactory(track=blood_on_the_floor)

    reported_album = list(Album.list_with_play_count())[0]

    assert reported_album.approx_play_count == 1
