from django.views.generic import TemplateView
from ninja import Query
from ninja.pagination import paginate

from localfm.app import v1_api

from .models import Album, Artist, Genre, Track, TrackPlay
from .payloads import (
    AlbumSchema,
    ArtistSchema,
    GenreSchema,
    TrackFilterSchema,
    TrackPlaySchema,
    TrackSchema,
)


def update_now_playing(request):
    pass


def scrobble(request):
    pass


class TracksIndex(TemplateView):
    template_name = "index.html"

    def get_context_data(self, **kwargs):
        context = super(TracksIndex, self).get_context_data(**kwargs)
        context["track_plays"] = TrackPlay.objects.all().select_related("track__album", "track__artist").order_by("-occurred_on")[:30]
        return context


@v1_api.get("artists", response=list[ArtistSchema])
@paginate
def list_artists(request):
    return Artist.objects.all().order_by("name")


@v1_api.get("albums", response=list[AlbumSchema])
@paginate
def list_albums(request):
    return Album.objects.all().order_by("album_artist__name", "artist__name", "name")


@v1_api.get("genres", response=list[GenreSchema])
@paginate
def list_albums(request):
    return Genre.objects.all().order_by("name")


@v1_api.get("tracks", response=list[TrackSchema])
@paginate
def list_tracks(request, filters: Query[TrackFilterSchema]):
    tracks = Track.objects.all().order_by(
        "album__genre__name", "artist__name", "album__name", "name"
    )
    tracks = filters.filter(tracks)
    return tracks


@v1_api.get("track-plays", response=list[TrackPlaySchema])
@paginate
def list_track_plays(request):
    return TrackPlay.objects.all().order_by("-occurred_on")
