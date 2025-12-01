from django.urls import path

from . import views

urlpatterns = [
    path('2.0/track.updateNowPlaying', views.update_now_playing, name="tracks.update_playing"),
]
