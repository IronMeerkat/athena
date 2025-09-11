from django.contrib.gis.db import models
from django.contrib.gis.geos import Point
from typing import Tuple


class Location(models.Model):
    name = models.CharField(max_length=255)
    radius = models.FloatField()

    coordinates = models.PointField(srid=4326)

    def is_in_radius(self, coordinates: Point | Tuple[float, float]) -> bool:
        if isinstance(coordinates, tuple):
            coordinates = Point(coordinates[0], coordinates[1], srid=4326)

        return self.coordinates.distance(coordinates) <= self.radius


class TimeFrame(models.Model):
    day_of_week = models.IntegerField()
    start = models.DateTimeField()
    end = models.DateTimeField()


class Policy(models.Model):

    blocked_urls = models.JSONField(default=list, blank=True)
    blocked_apps = models.JSONField(default=list, blank=True)
    block_shorts = models.BooleanField(default=False)

    whitelisted_urls = models.JSONField(default=list, blank=True)
    whitelisted_apps = models.JSONField(default=list, blank=True)


class Schedule(models.Model):
    time_frames = models.ManyToManyField(TimeFrame, related_name="schedules")
    locations = models.ManyToManyField(Location, related_name="schedules")

    policy = models.ForeignKey(Policy, on_delete=models.CASCADE, related_name="schedules")