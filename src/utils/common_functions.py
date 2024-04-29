#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# external imports
import os
import json
import socket
import math
from shapely import (
    Point
)
import requests
import pandas as pd
# internal imports
from src.utils.constants import (
    EARTH_RADIUS_KM,
    AIRPORTS_FILEPATH,
    ALL_COUNTRIES_FILEPATH,
    IP_URL
)


# Files treatment
def create_directory_structure(path: str) -> None:
    # Remove files from path, only directories
    if path[-1] != "/":
        path = "/".join(path.split("/")[:-1])
    if path == "":
        return
    if not os.path.exists(path):
        os.makedirs(path)


def json_file_to_dict(file_path: str) -> dict:
    create_directory_structure(file_path)
    with open(file_path) as file:
        raw_json = file.read()

    return json.loads(raw_json)


def json_file_to_list(file_path: str) -> list:
    create_directory_structure(file_path)
    with open(file_path) as file:
        raw_json = file.read()

    return json.loads(raw_json)


def dict_to_json_file(dict: dict, file_path: str, sort_keys: bool = False):
    create_directory_structure(file_path)
    file = open(file_path, "w")
    file.write(json.dumps(dict, indent=4, sort_keys=sort_keys))
    file.close()


def list_to_json_file(dict: list, file_path: str):
    create_directory_structure(file_path)
    file = open(file_path, "w")
    file.write(json.dumps(dict, indent=4))
    file.close()


def get_list_files_in_path(path: str) -> list:
    files_in_path = \
        [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
    return files_in_path


def get_list_folders_in_path(path: str) -> list[str]:
    dirs_in_path = \
        [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
    return dirs_in_path


# Conditions check
def check_ip(ip: str):
    try:
        addr = socket.inet_pton(socket.AF_INET6, ip)
    except socket.error:  # not a valid IPv6 address
        try:
            addr = socket.inet_pton(socket.AF_INET, ip)
        except socket.error:  # not a valid IPv4 address either
            return False
    return True


# Geo calculations
def distance_dictionaries(a: dict, b: dict) -> float:
    lat1 = a["latitude"]
    lat2 = b["latitude"]
    lon1 = a["longitude"]
    lon2 = b["longitude"]

    # Convert latitude and longitude to
    # spherical coordinates in radians.
    degrees_to_radians = math.pi / 180.0

    # phi = 90 - latitude
    phi1 = (90.0 - lat1) * degrees_to_radians
    phi2 = (90.0 - lat2) * degrees_to_radians

    # theta = longitude
    theta1 = lon1 * degrees_to_radians
    theta2 = lon2 * degrees_to_radians

    # Compute spherical distance from spherical coordinates.

    # For two locations in spherical coordinates
    # (1, theta, phi) and (1, theta, phi)
    # cosine( arc length ) =
    #    sin phi sin phi' cos(theta-theta') + cos phi cos phi'
    # distance = rho * arc length

    cos = (math.sin(phi1) * math.sin(phi2) * math.cos(theta1 - theta2) +
           math.cos(phi1) * math.cos(phi2))
    if abs(cos - 1.0) < 0.000000000000001:
        arc = 0.0
    else:
        arc = math.acos(cos)

    # Remember to multiply arc by the radius of the earth
    # in your favorite set of units to get length.
    return arc * EARTH_RADIUS_KM


def convert_km_radius_to_degrees(km_radius: float) -> float:
    degree = km_radius * (360 / (2 * EARTH_RADIUS_KM * math.pi))
    return degree


def get_nearest_airport_to_point(point: Point) -> dict:
    airports_df = pd.read_csv(AIRPORTS_FILEPATH, sep="\t")
    airports_df.drop(["pop",
                      "heuristic",
                      "1", "2", "3"], axis=1, inplace=True)

    airports_df["distance"] = airports_df["lat long"].apply(
        lambda airport_location: distance_dictionaries(
            a={
                "latitude": point.y,
                "longitude": point.x
            },
            b={
                "latitude": float(airport_location.split(" ")[0]),
                "longitude": float(airport_location.split(" ")[1])
            }
        )
    )

    return airports_df[
        airports_df["distance"] == airports_df["distance"].min()
        ].to_dict("records")[0]


def get_country_name(country_code: str) -> str:
    all_countries_list = json_file_to_dict(ALL_COUNTRIES_FILEPATH)
    for country in all_countries_list:
        if country["alpha-2"] == country_code:
            return country["name"]


def get_ip_details_via_cache(ip_address: str) -> dict:
    url = f"{IP_URL}/{ip_address}"
    print(url)
    details = json.loads(requests.get(url=url).json()["details"])
    return details


def get_ip_country_via_cache(ip_address: str) -> str:
    ip_details = get_ip_details_via_cache(ip_address)
    if "bogon" in ip_details.keys():
        return "bogon"
    else:
        return ip_details["country"]
