from django.db import models


class Artist(models.Model):
    name = models.CharField(max_length=256)


class Genre(models.Model):
    name = models.CharField(max_length=256)


class Album(models.Model):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    name = models.CharField(max_length=2048)


class Track(models.Model):
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name="tracks")
    album = models.ForeignKey(
        Album, on_delete=models.CASCADE, related_name="tracks", null=True
    )
    track_number = models.PositiveIntegerField(default=0)
    name = models.CharField(max_length=2048)


class AlbumGenre(models.Model):
    album = models.ForeignKey(Album, on_delete=models.CASCADE)
    genre = models.ForeignKey(Genre, on_delete=models.CASCADE)
