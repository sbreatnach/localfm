"""
factory_boy factories for generating database fixtures in tests.
"""

from datetime import UTC, datetime, timedelta

import factory

from localfm.tracks.models import Album, Artist, Genre, Track, TrackPlay


class ArtistFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Artist

    name = factory.Sequence(lambda n: f"Artist {n}")


class GenreFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Genre

    name = factory.Sequence(lambda n: f"Genre {n}")


class AlbumFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Album

    name = factory.Sequence(lambda n: f"Album {n}")
    artist = factory.SubFactory(ArtistFactory)
    album_artist = None
    genre = None
    disc_number = None
    hashed_identifier = factory.LazyAttribute(
        lambda album: Album.generate_identifier(
            album.name,
            album_artist_name=album.album_artist.name if album.album_artist else None,
            artist_name=album.artist.name,
            genre=album.genre.name if album.genre else None,
            disc_number=album.disc_number,
        )
    )


class TrackFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Track

    name = factory.Sequence(lambda n: f"Track {n}")
    artist = factory.SubFactory(ArtistFactory)
    album = factory.SubFactory(AlbumFactory)
    track_number = None
    file_path = factory.LazyAttribute(lambda track: f"/tmp/{track.name}.mp3")
    play_count = 0
    hashed_identifier = factory.LazyAttribute(
        lambda track: Track.generate_identifier(
            track.name,
            artist_name=track.artist.name if track.artist else None,
            album_name=track.album.name if track.album else None,
        )
    )


class TrackPlayFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TrackPlay

    track = factory.SubFactory(TrackFactory)
    occurred_on = factory.Sequence(
        lambda n: datetime(2026, 1, 1, tzinfo=UTC) + timedelta(minutes=n)
    )
