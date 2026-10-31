from django.urls import path

from . import views

urlpatterns = [
    path("styles/tabs.css", views.StyledTabsIndex.as_view(), name="styled_tabs"),
    path("", views.TracksIndex.as_view(), name="index"),
]
