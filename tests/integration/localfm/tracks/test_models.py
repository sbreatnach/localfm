"""
Integration tests for the top-albums report query.
"""

from datetime import UTC, datetime, timedelta

from localfm.tracks.models import Album, Artist, Track, TrackPlay, generate_identifier


def create_album(artist, album_artist=None, name="Test Album"):
    return Album.objects.create(
        name=name,
        artist=artist,
        album_artist=album_artist,
        hashed_identifier=generate_identifier(name, album_artist, artist),
    )


def create_track(album, artist, name, play_count=0):
    track = Track.objects.create(
        name=name,
        artist=artist,
        album=album,
        file_path=f"/tmp/{name}.mp3",
        hashed_identifier=generate_identifier(name, artist.name, album.name),
    )
    start = datetime(2026, 1, 1, tzinfo=UTC)
    TrackPlay.objects.bulk_create(
        TrackPlay(track=track, occurred_on=start + timedelta(minutes=i))
        for i in range(play_count)
    )
    return track


def test_list_with_play_count_includes_albums_without_album_artist(migrated_db):
    """Albums with no album-artist tag should still appear in the report."""
    artist = Artist.objects.create(name="Fleetwood Mac")
    album = create_album(artist, album_artist=None, name="Mystery To Me")
    create_track(album, artist, "Hypnotized", play_count=2)

    reported_albums = list(Album.list_with_play_count())

    assert [reported.id for reported in reported_albums] == [album.id]
    assert reported_albums[0].artist_name == "Fleetwood Mac"


def test_list_with_play_count_prefers_album_artist_when_present(migrated_db):
    """The report should use the album artist for naming when it is set."""
    track_artist = Artist.objects.create(name="Fleetwood Mac")
    album_artist = Artist.objects.create(name="Various Artists")
    album = create_album(
        track_artist, album_artist=album_artist, name="Compilation Album"
    )
    create_track(album, track_artist, "Some Track", play_count=1)

    reported_albums = list(Album.list_with_play_count())

    assert reported_albums[0].artist_name == "Various Artists"


def test_list_with_play_count_uses_integer_average(migrated_db):
    """The average should retain the existing integer-division behaviour."""
    artist = Artist.objects.create(name="Fleetwood Mac")
    album = create_album(artist, album_artist=None, name="Kiln House")
    create_track(album, artist, "Station Man", play_count=2)
    create_track(album, artist, "Blood On The Floor", play_count=1)

    reported_album = list(Album.list_with_play_count())[0]

    assert reported_album.approx_play_count == 1
