# external imports
from shapely import (
    from_geojson,
    Point,
)
import pandas as pd
# internal imports
from src.models.ip_model import IPModel
from src.models.airport_model import AirportModel
from src.utils.common_functions import (
    json_file_to_dict,
    dict_to_json_file,
    get_list_files_in_path,
    distance_dictionaries
)
from src.utils.constants import (
    REPLICATION_PACKAGE_DIR
)

EXPERIMENT_RESULTS_FOLDER = \
    f"{REPLICATION_PACKAGE_DIR}/experiment_results_first_ip"
NEW_RESULTS_FOLDER = f"{REPLICATION_PACKAGE_DIR}/experiment_results_voting"


def get_nearest_airport_to_point(point: Point) -> dict:
    airports_df = pd.read_csv("../src/resources/airports.csv", sep="\t")
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


def save_new_results(data_to_save: dict, filename: str):
    dict_to_json_file(
        data_to_save, f"{NEW_RESULTS_FOLDER}/{filename}")


for filename in get_list_files_in_path(EXPERIMENT_RESULTS_FOLDER):
    result_first_ip = json_file_to_dict(
        f"{EXPERIMENT_RESULTS_FOLDER}/{filename}")

    for result in result_first_ip["hunter_results"]:
        if len(result["ips_previous_to_target"]) <= 1:
            continue

        # Get the ips_previous_to_target
        ips_previous_to_target = [
            IPModel(
                ip=ip_previous_to_target["ip"],
                location=from_geojson(ip_previous_to_target["location"])
            )
            for ip_previous_to_target in result["ips_previous_to_target"]
        ]

        # If same location for every IP do not need to calculate nothing
        clean_locations = []
        [clean_locations.append(ip.location)
         for ip in ips_previous_to_target
         if ip.location not in clean_locations]

        if len(clean_locations) <= 1:
            continue

        # If more than one location get airports
        airports_raw = [
            get_nearest_airport_to_point(ip.location)
            for ip in ips_previous_to_target
        ]

        airports_list = [
            AirportModel(
                iata_code=airport_raw["#IATA"],
                size=airport_raw["size"],
                name=airport_raw["name"],
                # Longitude and Latitude for the point
                location=Point(airport_raw["lat long"].split(" ")[1],
                               airport_raw["lat long"].split(" ")[0]),
                country_code=airport_raw["country_code"],
                city_name=airport_raw["city"],
            ).to_dict()
            for airport_raw in airports_raw
        ]

        # Calculate country result
        airports_countries = []
        [
            airports_countries.append(airport["country_code"])
            for airport in airports_list
        ]

        airports_countries_count = {
            country_code: airports_countries.count(country_code)
            for country_code in airports_countries
        }

        country_result = "Indeterminate"
        for country_code in airports_countries_count.keys():
            if (airports_countries_count[country_code] >
                    len(airports_countries)/2):
                country_result = country_code

        # Calculate city result
        airports_cities = []
        [
            airports_cities.append(airport["city_name"])
            for airport in airports_list
        ]

        airports_cities_count = {
            city_name: airports_cities.count(city_name)
            for city_name in airports_cities
        }

        city_result = "Indeterminate"
        for city_name in airports_cities_count.keys():
            if (airports_cities_count[city_name] >
                    len(airports_countries)/2):
                city_result = city_name

        # Update result with the new calculations
        result["location_result"]["airports_intersection"] = airports_list
        result["location_result"]["airports_countries"] = airports_countries
        result["location_result"]["airports_cities"] = airports_cities
        result["location_result"]["country"] = country_result
        result["location_result"]["city"] = city_result
        if city_result == "Indeterminate" or country_result == "Indeterminate":
            result["location_result"]["centroid"] = ""
            result["location_result"]["nearest_airport"] = False

        print(filename)
        print(country_result, airports_countries)
        print(city_result, airports_cities)

    save_new_results(result_first_ip, filename)
