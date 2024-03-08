#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# external imports
from shapely import (
    box,
    Polygon,
    MultiPolygon,
    GeometryCollection
)
from shapely.geometry import shape
# internal imports
from src.utils.common_functions import (
    json_file_to_dict,
    get_country_name
)
from src.utils.constants import (
    COUNTRY_BORDERS_GEOJSON_FILEPATH
)


class MeshModel:
    def __init__(self, mesh_filepath: str):
        mesh_definition = json_file_to_dict(mesh_filepath)
        self._probes_per_section = int(mesh_definition["probes_per_section"])
        self._spacing = mesh_definition["spacing"]

        self._limit_area = Polygon()
        if "limit_area" in mesh_definition.keys():
            self.__generate_limit_area_polygon(
                mesh_definition["limit_area"]
            )
        else:
            self.__generate_worldwide_limit_area_polygon()

        if "countries" in mesh_definition.keys():
            self._country_codes = mesh_definition["countries"]
            self._country_names = [
                get_country_name(code) for code in self._country_codes
            ]
        else:
            self._country_codes = []
            self._country_names = []

        self._mesh = MultiPolygon()
        self.__generate_mesh_to_get_probes()

    # Properties access
    @property
    def probes_per_section(self):
        return self._probes_per_section

    @property
    def mesh(self):
        return self._mesh

    @property
    def country_codes(self):
        return self._country_codes

    # Class private methods
    def __generate_limit_area_polygon(self, limit_area_definition: dict):
        self._limit_area = box(
            xmin=limit_area_definition["longitude_min"],
            ymin=limit_area_definition["latitude_min"],
            xmax=limit_area_definition["longitude_max"],
            ymax=limit_area_definition["latitude_max"]
        )

    def __generate_worldwide_limit_area_polygon(self):
        self._limit_area = box(
            xmin=-180,
            ymin=-900,
            xmax=180,
            ymax=90
        )

    def __generate_mesh_to_get_probes(self):
        country_borders = self.__get_countries_borders()
        limited_area_polygons = self.__get_mesh_polygons_in_limited_area()
        intersecting_polygons = []
        for polygon in limited_area_polygons:
            if polygon.intersects(country_borders):
                intersecting_polygons.append(polygon)

        self._mesh = MultiPolygon(intersecting_polygons)

    def __get_countries_borders(self):
        countries_borders_dict = json_file_to_dict(
            COUNTRY_BORDERS_GEOJSON_FILEPATH)
        features = countries_borders_dict["features"]
        # NOTE: buffer(0) is a trick for fixing scenarios where polygons have
        # overlapping coordinates
        if self._country_codes:
            return GeometryCollection(
                [shape(feature["geometry"]).buffer(0)
                 for feature in features
                 if feature["properties"]["CNTRY_NAME"] in self._country_names]
            )
        else:
            return GeometryCollection(
                [shape(feature["geometry"]).buffer(0)
                    for feature in features]
            )

    def __get_mesh_polygons_in_limited_area(self) -> list:
        polygons = []
        x_coords, y_coords = self._limit_area.exterior.coords.xy
        x_min = min(x_coords)
        x_max = max(x_coords)
        y = min(y_coords)
        y_max = max(y_coords)
        i = -1
        while not y > y_max:
            x = x_min
            while not x > x_max:
                # components for polygon grid
                polygon = box(x, y, x + self._spacing, y + self._spacing)
                polygons.append(polygon)
                # Update x coordinate
                i = i + 1
                x = x + self._spacing
            # Update y coordinate
            y = y + self._spacing
        return polygons
