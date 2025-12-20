from datetime import datetime
from typing import Annotated, Optional

from ninja import FilterLookup, FilterSchema, Schema


class ArtistSchema(Schema):
    name: str
    artist_id: int


class GenreSchema(Schema):
    name: str
    genre_id: int


class AlbumSchema(Schema):
    album_id: int
    name: str
    artist_id: int
    album_artist_id: int
    genre_id: int
    disc_number: int


class TrackSchema(Schema):
    track_id: int
    artist_id: int
    album_id: int
    track_number: int
    name: str
    play_count: int


class TrackFilterSchema(FilterSchema):
    name: Annotated[Optional[str], FilterLookup("name__icontains")] = None
    album_id: Optional[int] = None
    artist_id: Optional[int] = None
    genre_id: Annotated[Optional[int], FilterLookup("album__genre_id")] = None


class TrackPlaySchema(Schema):
    track_id: int
    occurred_on: datetime


class TrackPlayFilterSchema(FilterSchema):
    track_id: Optional[int] = None
