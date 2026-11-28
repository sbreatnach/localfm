"""
Integration tests for the top-albums report query.
"""

from localfm.tracks.models import Album, Track

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


def test_get_by_identifier_matches_artist_with_leading_the(migrated_db):
    """A Last.fm artist with "The " should match a tag without it."""
    artist = ArtistFactory(name="Smashing Pumpkins")
    album = AlbumFactory(
        name="Singles (Original Motion Picture Soundtrack)", artist=artist
    )
    track = TrackFactory(artist=artist, album=album, name="Drown")

    assert (
        Track.get_by_identifier(
            "Drown",
            artist_name="The Smashing Pumpkins",
            album_name=album.name,
        )
        == track
    )


def test_get_by_identifier_matches_artist_without_leading_the(migrated_db):
    """A Last.fm artist without "The " should match a tag with it."""
    artist = ArtistFactory(name="The Raconteurs")
    album = AlbumFactory(name="Help Us Stranger", artist=artist)
    track = TrackFactory(artist=artist, album=album, name="Only Child")

    assert (
        Track.get_by_identifier(
            "Only Child", artist_name="Raconteurs", album_name=album.name
        )
        == track
    )


def test_get_by_identifier_keeps_the_the_distinct_from_the(migrated_db):
    """ "The" must not resolve to a track by "The The"."""
    artist = ArtistFactory(name="The The")
    album = AlbumFactory(name="Soul Mining", artist=artist)
    track = TrackFactory(artist=artist, album=album, name="This Is the Day")

    assert (
        Track.get_by_identifier(
            "This Is the Day", artist_name="The The", album_name=album.name
        )
        == track
    )
    assert (
        Track.get_by_identifier(
            "This Is the Day", artist_name="The", album_name=album.name
        )
        is None
    )


def test_get_by_identifier_keeps_the_distinct_from_the_the(migrated_db):
    """ "The The" must not resolve to a track by "The"."""
    artist = ArtistFactory(name="The")
    album = AlbumFactory(name="The Album", artist=artist)
    track = TrackFactory(artist=artist, album=album, name="The Track")

    assert (
        Track.get_by_identifier("The Track", artist_name="The", album_name=album.name)
        == track
    )
    assert (
        Track.get_by_identifier(
            "The Track", artist_name="The The", album_name=album.name
        )
        is None
    )
