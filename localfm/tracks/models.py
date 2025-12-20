import hashlib
import logging
import os
from pathlib import Path

from django.db import models
from tinytag import TinyTag

logger = logging.getLogger(__name__)


def library_directory():
    return os.environ.get("LIBRARY_DIRECTORY", "e:/Music")


def generate_identifier(*args):
    hasher = hashlib.md5(usedforsecurity=False)
    for arg in args:
        # force all text to lower-case (if applicable to the language)
        # since Last.fm has a weird way of not retaining capitalisation correctly
        hasher.update(str(arg).lower().encode())
    return hasher.hexdigest()


class Artist(models.Model):
    name = models.CharField(max_length=256, unique=True)


class Genre(models.Model):
    name = models.CharField(max_length=256, unique=True)


class Album(models.Model):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name="albums")
    album_artist = models.ForeignKey(
        Artist, on_delete=models.CASCADE, null=True, related_name="artist_albums"
    )
    genre = models.ForeignKey(
        Genre, on_delete=models.CASCADE, null=True, related_name="albums"
    )
    name = models.CharField(max_length=2048)
    disc_number = models.PositiveIntegerField(null=True)
    hashed_identifier = models.CharField(max_length=64, unique=True)

    @classmethod
    def get_or_create_by_tagged_data(cls, tagged_data: TinyTag):
        if not tagged_data.album:
            logger.warning("No album data for tagged data %s", tagged_data.filename)
            return None
        album_identifier = cls.generate_identifier(
            tagged_data.album,
            album_artist_name=tagged_data.albumartist,
            artist_name=tagged_data.artist,
            genre=tagged_data.genre,
            disc_number=tagged_data.disc,
        )
        persisted_album = cls.objects.filter(hashed_identifier=album_identifier).first()
        if not persisted_album:
            persisted_genre = None
            if tagged_data.genre:
                persisted_genre = Genre.objects.get_or_create(name=tagged_data.genre)[0]
            persisted_artist = None
            if tagged_data.artist:
                persisted_artist = Artist.objects.get_or_create(
                    name=tagged_data.artist
                )[0]
            persisted_album_artist = None
            if tagged_data.albumartist:
                persisted_album_artist = Artist.objects.get_or_create(
                    name=tagged_data.albumartist
                )[0]
            persisted_album = cls.objects.create(
                name=tagged_data.album,
                disc_number=tagged_data.disc,
                artist=persisted_artist,
                album_artist=persisted_album_artist,
                genre=persisted_genre,
                hashed_identifier=album_identifier,
            )
        return persisted_album

    @classmethod
    def generate_identifier(
        cls,
        album_name,
        album_artist_name=None,
        artist_name=None,
        genre=None,
        disc_number=None,
    ):
        identifier_args = [
            album_name,
            album_artist_name or artist_name,
            genre,
            disc_number,
        ]
        valid_args = [arg for arg in identifier_args if arg]
        return generate_identifier(*valid_args)


class Track(models.Model):
    artist = models.ForeignKey(
        Artist, on_delete=models.CASCADE, related_name="tracks", null=True
    )
    album = models.ForeignKey(
        Album, on_delete=models.CASCADE, related_name="tracks", null=True
    )
    track_number = models.PositiveIntegerField(null=True)
    name = models.CharField(max_length=2048)
    file_path = models.FilePathField(path=library_directory, max_length=2048)
    play_count = models.PositiveIntegerField(default=0)
    hashed_identifier = models.CharField(max_length=64, unique=True)

    @classmethod
    def get_by_identifier(cls, track_name=None, **track_data):
        track_identifier = cls.generate_identifier(track_name, **track_data)
        logger.debug("Retrieving track with identifier %s", track_identifier)
        return cls.objects.filter(hashed_identifier=track_identifier).first()

    @classmethod
    def get_or_create_by_tagged_data(cls, file_path: Path, tagged_data: TinyTag):
        track_identifier = cls.generate_identifier(
            track_name=tagged_data.title,
            artist_name=tagged_data.artist,
            album_name=tagged_data.album,
        )
        persisted_track = cls.objects.filter(hashed_identifier=track_identifier).first()
        if not persisted_track:
            persisted_artist = None
            if tagged_data.artist:
                persisted_artist = Artist.objects.get_or_create(
                    name=tagged_data.artist
                )[0]
            else:
                logger.warning(
                    "Failed to generate artist name for track %s", tagged_data
                )
            persisted_album = Album.get_or_create_by_tagged_data(tagged_data)
            persisted_track = cls.objects.create(
                name=tagged_data.title,
                track_number=tagged_data.track,
                artist=persisted_artist,
                album=persisted_album,
                file_path=file_path,
                hashed_identifier=track_identifier,
            )
        return persisted_track

    @classmethod
    def generate_identifier(
        cls,
        track_name,
        artist_name=None,
        album_name=None,
    ):
        # note the subtle difference of arguments compared to the other
        # get_or_create_by_identifier implementations: Last.fm can only
        # give us track name, artist name and album name as identifiable data
        # so we use that for identifying tracks. But the album and album artist
        # will be created by the library import so they will have album artist +
        # genre as further identification data points.
        identifier_args = [track_name, artist_name, album_name]
        valid_args = [arg for arg in identifier_args if arg]
        return generate_identifier(*valid_args)


class TrackPlay(models.Model):
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name="plays")
    occurred_on = models.DateTimeField()
