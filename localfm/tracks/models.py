import hashlib

from django.db import models


def generate_identifier(*args):
    hasher = hashlib.md5(usedforsecurity=False)
    for arg in args:
        hasher.update(arg.encode())
    return hasher.hexdigest()


class Artist(models.Model):
    name = models.CharField(max_length=256)
    hashed_identifier = models.CharField(max_length=64, unique=True)

    @classmethod
    def get_or_create_by_identifier(cls, artist_name=None, **_artist_data):
        artist_identifier = cls.generate_identifier(artist_name)
        persisted_album = cls.objects.filter(
            hashed_identifier=artist_identifier
        ).first()
        if not persisted_album:
            persisted_album = cls.objects.create(
                name=artist_name, hashed_identifier=artist_identifier
            )
        return persisted_album

    @classmethod
    def generate_identifier(cls, artist_name):
        return generate_identifier(artist_name)


class AlbumArtist(models.Model):
    name = models.CharField(max_length=256)
    hashed_identifier = models.CharField(max_length=64, unique=True)


class Genre(models.Model):
    name = models.CharField(max_length=256, unique=True)


class Album(models.Model):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    album_artist = models.ForeignKey(AlbumArtist, on_delete=models.CASCADE, null=True)
    genre = models.ForeignKey(Genre, on_delete=models.CASCADE, null=True)
    name = models.CharField(max_length=2048)
    hashed_identifier = models.CharField(max_length=64, unique=True)

    @classmethod
    def get_or_create_by_identifier(cls, album_name=None, artist=None, **album_data):
        album_identifier = cls.generate_identifier(album_name, **album_data)
        persisted_album = cls.objects.filter(hashed_identifier=album_identifier).first()
        if not persisted_album:
            persisted_artist = artist or Artist.get_or_create_by_identifier(**album_data)
            persisted_album = cls.objects.create(
                name=album_name,
                artist=persisted_artist,
                hashed_identifier=album_identifier,
            )
        return persisted_album

    @classmethod
    def generate_identifier(cls, album_name, artist_name=None, album_artist_name=None):
        identifier_args = [album_name, artist_name, album_artist_name]
        valid_args = [arg for arg in identifier_args if arg]
        return generate_identifier(*valid_args)


class Track(models.Model):
    artist = models.ForeignKey(
        Artist, on_delete=models.CASCADE, related_name="tracks", null=True
    )
    album = models.ForeignKey(
        Album, on_delete=models.CASCADE, related_name="tracks", null=True
    )
    track_number = models.PositiveIntegerField(default=0)
    name = models.CharField(max_length=2048)
    play_count = models.PositiveIntegerField(default=0)
    hashed_identifier = models.CharField(max_length=64, unique=True)

    @classmethod
    def get_or_create_by_identifier(cls, track_name=None, play_count=0, **track_data):
        track_identifier = cls.generate_identifier(track_name, **track_data)
        persisted_track = cls.objects.filter(hashed_identifier=track_identifier).first()
        if not persisted_track:
            persisted_artist = Artist.get_or_create_by_identifier(**track_data)
            persisted_album = Album.get_or_create_by_identifier(
                artist=persisted_artist, **track_data
            )
            persisted_track = cls.objects.create(
                name=track_name,
                play_count=play_count,
                artist=persisted_artist,
                album=persisted_album,
                hashed_identifier=track_identifier,
            )
        return persisted_track

    @classmethod
    def generate_identifier(
        cls, track_name, artist_name=None, album_name=None, album_artist_name=None
    ):
        identifier_args = [track_name, artist_name, album_name, album_artist_name]
        valid_args = [arg for arg in identifier_args if arg]
        return generate_identifier(*valid_args)


class AlbumGenre(models.Model):
    album = models.ForeignKey(Album, on_delete=models.CASCADE)
    genre = models.ForeignKey(Genre, on_delete=models.CASCADE)


class TrackPlay(models.Model):
    track = models.ForeignKey(Track, on_delete=models.CASCADE)
    occurred_on = models.DateTimeField()
