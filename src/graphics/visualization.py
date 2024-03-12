#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# external imports
import pandas as pd
import plotly.graph_objects as go
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
    RESULTS_MODES
)

MESH_FILEPATH = EEE_MESH_3_FILEPATH
ACTUAL_MODE = RESULTS_MODES[0]

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


def visualize_hunter_routes_results(filepath: str):
    fig = go.Figure()

    routes_results_df = pd.read_csv(filepath, sep=",")
    routes_results_df = routes_results_df.loc[
        routes_results_df["outside_EEE"]
    ]

    origins_latitudes = routes_results_df["origin_latitude"].to_list()
    origins_longitudes = routes_results_df["origin_longitude"].to_list()
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


visualize_hunter_routes_results(
    f"../../replication_package_europe_anycast_experiment/analysis_{ACTUAL_MODE}/routes_results_{ACTUAL_MODE}.csv"
)