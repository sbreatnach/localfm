from datetime import datetime
from typing import Annotated, Optional

from ninja import Field, FilterLookup, FilterSchema, Schema


class ArtistSchema(Schema):
    name: str
    artist_id: int = Field(alias="id")


class GenreSchema(Schema):
    name: str
    genre_id: int = Field(alias="id")


class AlbumSchema(Schema):
    album_id: int = Field(alias="id")
    name: str
    artist_id: Optional[int] = None
    album_artist_id: Optional[int] = None
    genre_id: Optional[int] = None
    disc_number: Optional[int] = None


class TrackSchema(Schema):
    track_id: int = Field(alias="id")
    artist_id: Optional[int] = None
    album_id: Optional[int] = None
    track_number: Optional[int] = None
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
