#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# external imports
from shapely import (
    Point,
    to_geojson
)
# internal imports


class AirportModel:
    def __init__(self,
                 iata_code: str,
                 size: str,
                 name: str,
                 location: Point,
                 country_code: str,
                 city_name: str):
        self._iata_code = iata_code
        self._size = size
        self._name = name
        self._location = location
        self._country_code = country_code
        self._city_name = city_name

    # Properties
    @property
    def iata_code(self):
        return self._iata_code

    @property
    def country_code(self):
        return self._country_code

    @property
    def city_name(self):
        return self._city_name

    @property
    def location(self):
        return self._location

    # Class particular methods

    # Model common methods
    def to_dict(self) -> dict:
        return {
            "iata_code": self._iata_code,
            "size": self._size,
            "name": self._name,
            "location": to_geojson(self._location),
            "country_code": self._country_code,
            "city_name": self._city_name,
        }
