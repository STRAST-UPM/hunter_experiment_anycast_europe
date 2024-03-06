#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# external imports
from shapely import (
    to_geojson,
    from_geojson,
    Point,
)
# internal imports


class IPModel:
    def __init__(self, ip: str, location: Point = Point()):
        self._ip = ip
        self._location = location

    @property
    def ip(self) -> str:
        return self._ip

    @ip.setter
    def ip(self, value):
        self._ip = value

    @property
    def location(self) -> Point:
        return self._location

    @location.setter
    def location(self, value):
        self._location = value

    def to_dict(self):
        if self._location is not None:
            location = to_geojson(self._location)
        else:
            location = ""
        return {
            "ip": self._ip,
            "location": location
        }

    def from_dict(self, data: dict):
        self._ip = data["ip"]
        self._location = from_geojson(data["location"])
