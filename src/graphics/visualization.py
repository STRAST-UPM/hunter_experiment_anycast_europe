#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# external imports
import pandas as pd
import plotly.graph_objects as go
import requests
import json
from ast import literal_eval
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
    PARTIAL_RESULTS_DIR,
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


def update_geo_layout(fig: go.Figure):
    fig.update_geos(
        visible=False,
        resolution=50,
        showcountries=True,
        countrycolor="RebeccaPurple",
        projection_type="natural earth"
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
        origin_country_filter: list[str] = None,
        destination_country_filter: list[str] = None,
        capital_aggregation: bool = False,
):
    fig = go.Figure()

    routes_results_df = pd.read_csv(filepath, sep=",")
    routes_results_df = routes_results_df.loc[
        (routes_results_df["outside_EEE"] == True)
    ]

    if origin_country_filter:
        routes_results_df = routes_results_df.loc[
            (routes_results_df["origin_country"].isin(
                origin_country_filter))
        ]

    if destination_country_filter:
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

    origins_latitudes = routes_results_df[origin_latitude].to_list()
    origins_longitudes = routes_results_df[origin_longitude].to_list()
    results_latitudes = routes_results_df["result_latitude"].to_list()
    results_longitudes = routes_results_df["result_longitude"].to_list()

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
                "color": "red",
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
                "color": "black",
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
            marker={"color": "gray"},
            name="routes",
            showlegend=False
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
ANALYSIS_MODE = RESULTS_MODES[1]
visualize_hunter_routes_results(
    f"{REPLICATION_PACKAGE_DIR}/analysis_{ANALYSIS_MODE}/"
    f"routes_results_non_suspicious_{ANALYSIS_MODE}.csv",
    #origin_country_filter=["AT"],
    destination_country_filter=["RU"],
    capital_aggregation=False
)


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
