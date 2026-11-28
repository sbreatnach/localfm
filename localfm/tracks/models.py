import hashlib
import logging
import unicodedata
from pathlib import Path

from django.conf import settings
from django.db import IntegrityError, models, transaction
from tinytag import TinyTag

logger = logging.getLogger(__name__)


def library_directory():
    return settings.MUSIC_LIBRARY_DIRECTORY


def generate_identifier(*args):
    hasher = hashlib.md5(usedforsecurity=False)
    for arg in args:
        # Normalise Unicode so that composed and decomposed forms of the same
        # text (e.g. "é" vs "e" + combining acute) produce the same identifier.
        # Then force all text to lower-case (if applicable to the language)
        # since Last.fm has a weird way of not retaining capitalisation correctly;
        # also strip out any leading or trailing whitespace characters
        normalized = unicodedata.normalize("NFC", str(arg))
        hasher.update(normalized.strip().lower().encode())
    return hasher.hexdigest()


def artist_name_variants(artist_name):
    """
    Return artist names that should be considered equivalent when resolving a
    track. Last.fm and file tags disagree about leading "The " articles, so
    allow one to be present on either side.

    "The The" is left alone: stripping its leading article would produce
    "The", which is a different (valid) artist name. For the same reason, an
    artist called "The" is never expanded to "The The".
    """
    if not artist_name:
        return [artist_name]

    name = str(artist_name).strip()
    if not name:
        return [artist_name]

    normalized_name = name.lower()
    variants = [name]

    if normalized_name.startswith("the "):
        without_article = name[4:].strip()
        starts_another_article = (
            without_article.lower() == "the"
            or without_article.lower().startswith("the ")
        )
        if without_article and not starts_another_article:
            variants.append(without_article)
    elif normalized_name != "the":
        variants.append(f"The {name}")

    return variants


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
    def list_with_play_count(cls, limit=100):
        raw_query = """
        SELECT albums.*,
               artists.name as artist_name,
               (album_listens.total_album_listens /
                album_totals.total_tracks) as approx_play_count
        FROM tracks_album albums
        INNER JOIN tracks_artist artists
                ON artists.id = COALESCE(albums.album_artist_id, albums.artist_id)
        INNER JOIN (
            SELECT albums.id as album_id, count(*) as total_tracks
            FROM tracks_track tracks
            INNER JOIN tracks_album albums ON albums.id = tracks.album_id
            GROUP BY albums.id
        ) album_totals ON album_totals.album_id = albums.id
        INNER JOIN (
            SELECT albums.id as album_id, albums.name, count(*) as total_album_listens
            FROM tracks_trackplay plays
            INNER JOIN tracks_track tracks ON tracks.id = plays.track_id
            INNER JOIN tracks_album albums ON albums.id = tracks.album_id
            GROUP BY albums.id, albums.name
        ) album_listens ON album_listens.album_id = albums.id
        ORDER BY approx_play_count DESC
        LIMIT %s;
        """
        return Album.objects.raw(raw_query, [limit])

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
        if persisted_album:
            return persisted_album

        try:
            with transaction.atomic():
                persisted_genre = None
                if tagged_data.genre:
                    persisted_genre = Genre.objects.get_or_create(
                        name=tagged_data.genre.strip()
                    )[0]
                persisted_artist = None
                if tagged_data.artist:
                    persisted_artist = Artist.objects.get_or_create(
                        name=tagged_data.artist.strip()
                    )[0]
                persisted_album_artist = None
                if tagged_data.albumartist:
                    persisted_album_artist = Artist.objects.get_or_create(
                        name=tagged_data.albumartist.strip()
                    )[0]
                return cls.objects.create(
                    name=tagged_data.album.strip(),
                    disc_number=tagged_data.disc,
                    artist=persisted_artist,
                    album_artist=persisted_album_artist,
                    genre=persisted_genre,
                    hashed_identifier=album_identifier,
                )
        except IntegrityError:
            # Another thread may have created the same album between our filter
            # and create. If so, use the existing row instead of failing.
            persisted_album = cls.objects.filter(
                hashed_identifier=album_identifier
            ).first()
            if persisted_album is None:
                raise
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
        # album identifiers are driven by the album artist primarily and only use artist
        # as a fallback if album artist not set
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
        persisted_track = cls.objects.filter(hashed_identifier=track_identifier).first()
        if persisted_track is not None:
            return persisted_track

        artist_name = track_data.get("artist_name")
        fallback_identifiers = []
        for variant in artist_name_variants(artist_name):
            identifier = cls.generate_identifier(
                track_name, **{**track_data, "artist_name": variant}
            )
            if (
                identifier != track_identifier
                and identifier not in fallback_identifiers
            ):
                fallback_identifiers.append(identifier)

        if not fallback_identifiers:
            return None

        logger.debug(
            "Retrieving track with fallback identifiers %s", fallback_identifiers
        )
        matches = list(
            cls.objects.filter(hashed_identifier__in=fallback_identifiers)[:2]
        )
        if len(matches) == 1:
            logger.info(
                "Matched track %s for artist %r using an alternate artist name",
                matches[0].id,
                artist_name,
            )
            return matches[0]
        if len(matches) > 1:
            logger.warning(
                "Ambiguous track match for %r / %r: %s",
                track_name,
                artist_name,
                [match.id for match in matches],
            )
        return None

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
                    name=tagged_data.artist.strip()
                )[0]
            else:
                logger.warning(
                    "Failed to generate artist name for track %s", tagged_data
                )
            persisted_album = Album.get_or_create_by_tagged_data(tagged_data)
            persisted_track = cls.objects.create(
                name=tagged_data.title.strip(),
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
