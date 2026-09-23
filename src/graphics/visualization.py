#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# external imports
import io
import pandas as pd
import plotly.graph_objects as go
import requests
import json
import numpy as np
from PIL import Image
from shapely import (
    Point,
    from_geojson
)

# internal imports
from src.models.mesh_model import MeshModel
from src.utils.common_functions import (
    json_file_to_dict
)
from src.utils.constants import (
    EEE_MESH_3_FILEPATH,
    IP_URL,
    RESULTS_MODES,
    REPLICATION_PACKAGE_DIR
)

MESH_FILEPATH = EEE_MESH_3_FILEPATH

def add_mesh_geo_trace(fig: go.Figure):
    mesh = MeshModel(mesh_filepath=MESH_FILEPATH)
    for polygon in list(mesh.mesh.geoms):
        polygon_longitudes, polygon_latitudes = polygon.exterior.coords.xy
        fig.add_trace(
            go.Scattergeo(
                lon=polygon_longitudes.tolist(),
                lat=polygon_latitudes.tolist(),
                mode="lines",
                marker={"color": "green"},
                name="mesh",
                showlegend=False
            )
        )


def add_hunter_result_geo_trace(
        fig: go.Figure,
        origin: Point,
        destination: Point):

    fig.add_trace(
        go.Scattergeo(
            lon=[origin.x],
            lat=[origin.y],
            mode="markers",
            marker={
                # "size": 10,
                "color": "red",
                "symbol": "circle"
            },
            name="origins",
            showlegend=False
        )
    )

    fig.add_trace(
        go.Scattergeo(
            lon=[destination.x],
            lat=[destination.y],
            mode="markers",
            marker={
                "size": 10,
                "color": "black",
                "symbol": "x"
            },
            name="destinations",
            showlegend=False
        )
    )

    fig.add_trace(
        go.Scattergeo(
            lon=[origin.x, destination.x],
            lat=[origin.y, destination.y],
            mode="lines",
            marker={"color": "gray"},
            name="routes",
            showlegend=False
        )
    )


def add_result_trace(fig: go.Figure, filename: str):
    pass


def update_geo_layout(fig: go.Figure, fitbounds: bool = False):
    fig.update_geos(
        visible=False,
        resolution=50,
        showcountries=True,
        countrycolor="RebeccaPurple",
        projection_type="natural earth",
        fitbounds="locations" if fitbounds else False
    )


def visualize_hunter_result(filepath: str):
    fig = go.Figure()

    # Mesh trace
    # add_mesh_geo_trace(fig)

    # Hunter results trace
    hunter_info = json_file_to_dict(filepath)
    for result in hunter_info["hunter_results"]:
        if result["location_result"]["country"] == "Indeterminate":
            continue
        destination_location = from_geojson(
            result["location_result"]["airports_intersection"][0]["location"])

        origin_id = result["origin_id"]
        origin_location = [
            from_geojson(origin["location"])
            for origin in hunter_info["measurements"]["origin"]
            if origin["probe_id"] == origin_id
        ][0]

        add_hunter_result_geo_trace(
            fig=fig,
            origin=origin_location,
            destination=destination_location
        )

    # Layout
    update_geo_layout(fig)
    fig.show()


def visualize_hunter_routes_results(
        filepath: str,
        only_out_of_EEE: bool = False,
        origin_country_filter: list[str] = None,
        destination_country_filter: list[str] = None,
        capital_aggregation: bool = False,
):
    fig = go.Figure()

    routes_results_df = pd.read_csv(filepath, sep=",")
    # Filters application
    if only_out_of_EEE:
        routes_results_df = routes_results_df.loc[
            (routes_results_df["outside_EEE"] == only_out_of_EEE)
        ]

    if origin_country_filter and origin_country_filter != []:
        routes_results_df = routes_results_df.loc[
            (routes_results_df["origin_country"].isin(
                origin_country_filter))
        ]

    if destination_country_filter and destination_country_filter != []:
        routes_results_df = routes_results_df.loc[
            (routes_results_df["result_country"].isin(
                destination_country_filter))
        ]

    if capital_aggregation:
        origin_latitude = "capital_origin_latitude"
        origin_longitude = "capital_origin_longitude"
    else:
        origin_latitude = "origin_latitude"
        origin_longitude = "origin_longitude"

    routes_unique_df = routes_results_df[[
        origin_latitude, origin_longitude,
        "result_latitude", "result_longitude",
        "result_country"
    ]].drop_duplicates()

    destination_countries_list = routes_unique_df[
        "result_country"].unique().tolist()

    for destination_country in destination_countries_list:
        origins_latitudes = routes_unique_df.loc[
            routes_unique_df["result_country"] == destination_country
        ][origin_latitude].to_list()
        origins_longitudes = routes_unique_df.loc[
            routes_unique_df["result_country"] == destination_country
            ][origin_longitude].to_list()
        results_latitudes = routes_unique_df.loc[
            routes_unique_df["result_country"] == destination_country
            ]["result_latitude"].to_list()
        results_longitudes = routes_unique_df.loc[
            routes_unique_df["result_country"] == destination_country
            ]["result_longitude"].to_list()

        routes_latitudes = [
            item for sublist in zip(origins_latitudes, results_latitudes)
            for item in sublist
        ]
        routes_longitudes = [
            item for sublist in zip(origins_longitudes, results_longitudes)
            for item in sublist
        ]

        fig.add_trace(
            go.Scattergeo(
                lon=origins_longitudes,
                lat=origins_latitudes,
                mode="markers",
                marker={
                    # "size": 10,
                    "color": "black",
                    "symbol": "circle"
                },
                name="origins",
                showlegend=False
            )
        )

        fig.add_trace(
            go.Scattergeo(
                lon=results_longitudes,
                lat=results_latitudes,
                mode="markers",
                marker={
                    # "size": 10,
                    "color": "red",
                    "symbol": "x"
                },
                name="destinations",
                showlegend=False
            )
        )

        fig.add_trace(
            go.Scattergeo(
                lon=routes_longitudes,
                lat=routes_latitudes,
                mode="lines",
                opacity=0.7,
                marker={"color": country_colors[destination_country]},
                name=f"routes_{destination_country}",
                showlegend=True
            )
        )

    # Layout
    update_geo_layout(fig)
    fig.show()


def get_ip_location_via_cache(ip_address: str):
    url = f"{IP_URL}/{ip_address}"
    details = json.loads(requests.get(url=url).json()["details"])
    anycast = False
    if "bogon" in details.keys():
        print("IS BOGON")
        return 0, 0, False

    if "anycast" in details.keys():
        anycast = details["anycast"]

    return details["longitude"], details["latitude"], anycast


def visualize_complete_route(route_locations: list):
    fig = go.Figure()
    longitudes = [
        coords[0]
        for coords in route_locations
    ]
    latitudes = [
        coords[1]
        for coords in route_locations
    ]

    ip_address_list = [
        coords[2]
        for coords in route_locations
    ]

    fig.add_trace(
        go.Scattergeo(
            lon=longitudes,
            lat=latitudes,
            mode="markers+lines",
            marker={
                "color": "black",
                "symbol": "circle"
            },
            hovertext=ip_address_list,
            name="routes",
            showlegend=False
        )
    )

    # Layout
    update_geo_layout(fig)
    fig.show()


# Show one country results
# Countries
# ['AT', 'BE', 'BG', 'CY', 'CZ', 'DE', 'DK', 'EE', 'ES', 'FI', 'FR', 'GR',
# 'HR', 'HU', 'IE', 'IS', 'IT', 'LT', 'LU', 'LV', 'MT', 'NL', 'NO', 'PL',
# 'PT', 'RO', 'SE', 'SI', 'SK', 'LI']
# country_colors = {
#     "US": "gray",
#     "GB": "green",
#     "RU": "red",
#     "RS": "blue",
#     "UA": "yellow",
#     "CH": "purple"
# }
# ANALYSIS_MODE = RESULTS_MODES[1]
# visualize_hunter_routes_results(
#     f"{REPLICATION_PACKAGE_DIR}/analysis_{ANALYSIS_MODE}/"
#     f"routes_results_non_suspicious_{ANALYSIS_MODE}.csv",
#     only_out_of_EEE=True,
#     origin_country_filter=[],
#     destination_country_filter=["RS", "RU", "UA"],
#     capital_aggregation=False
# )


# Show suspicious routes
#suspicious_routes_df = pd.read_csv(
#    f"{PARTIAL_RESULTS_DIR}/voting/suspicious_results_voting.csv")
#suspicious_routes_df = suspicious_routes_df.loc[
#    (suspicious_routes_df["origin_country"] == "ES")
#]
#for index, row in suspicious_routes_df.iterrows():
#    route = literal_eval(row["route"])
#    locations = [(row["origin_longitude"], row["origin_latitude"], "origin")]
#    for hop in route[1:]:
#        if len(hop) == 0:
#            continue
#
#        longitude, latitude, is_anycast = get_ip_location_via_cache(hop[0])
#        if is_anycast or (latitude == 0 and longitude == 0):
#            pass
#        else:
#            locations.append(
#                (longitude, latitude, hop[0]))
#    print(locations)
#
#    visualize_complete_route(locations)


# Renders a probe PNG to measure the true content aspect ratio, since it
# depends on the map projection's distortion and can't be computed analytically
def _measure_content_aspect_ratio(fig: go.Figure, probe_size: int = 800) -> float:
    png_bytes = fig.to_image(format="png", width=probe_size, height=probe_size)
    pixels = np.array(Image.open(io.BytesIO(png_bytes)).convert("RGB"))
    background = pixels[0, 0]
    content_mask = np.any(pixels != background, axis=-1)
    content_rows = np.nonzero(np.any(content_mask, axis=1))[0]
    content_cols = np.nonzero(np.any(content_mask, axis=0))[0]
    content_width = content_cols[-1] - content_cols[0] + 1
    content_height = content_rows[-1] - content_rows[0] + 1
    return content_width / content_height


# Create an image with the grid over the world map in order to vizualize the mesh
def visualize_probes_selection_grid(output_filepath: str = "mesh_grid.svg"):
    fig = go.Figure()
    add_mesh_geo_trace(fig)
    update_geo_layout(fig, fitbounds=True)
    fig.update_layout(margin={"l": 0, "r": 0, "t": 0, "b": 0})

    aspect_ratio = _measure_content_aspect_ratio(fig)
    image_width = 1000
    image_height = round(image_width / aspect_ratio)

    fig.write_image(output_filepath, width=image_width, height=image_height)
