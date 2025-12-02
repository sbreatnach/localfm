from django.contrib.auth import authenticate
from django.http import (
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseNotFound,
)

from localfm.tracks import views as tracks_views
from localfm.sessions import views as sessions_views


SUPPORTED_ENDPOINTS = {
    "track.updateNowPlaying": tracks_views.update_now_playing,
    "track.scrobble": tracks_views.scrobble,
    "auth.getMobileSession": sessions_views.get_mobile_session,
}


def is_authenticated(request_data):
    # TODO: do the whole rigmarole of comparing api_sig with request data
    # as per https://www.last.fm/api/authspec
    return True


def process(request):
    """
    Processes all Last.fm API requests. Authenticates using the expected format
    then routes to the relevant API function
    """
    if request.method != "POST":
        return HttpResponseBadRequest()

    request_data = request.POST
    request_endpoint = request_data.get("method")
    request_process_fn = SUPPORTED_ENDPOINTS.get(request_endpoint)
    if not request_process_fn:
        return HttpResponseNotFound()

    user = authenticate(request, api_key=request_data.get("api_key"))
    if not user or not is_authenticated(request_data):
        return HttpResponseForbidden()

    request.user = user
    return request_process_fn(request)
