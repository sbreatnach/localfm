from django.urls import path

from . import views

urlpatterns = [
    path("", views.TracksIndex.as_view(), name="index"),
]
