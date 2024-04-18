#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# external imports
import os
from dotenv import load_dotenv, find_dotenv
# internal imports


load_dotenv(find_dotenv())
# PATHS CONSTANTS
__BASE_DIR = \
    (f"{os.path.dirname(os.path.dirname(os.path.abspath(__file__)))}".
     replace("/src", ""))

# src paths
__SRC_DIR = f"{__BASE_DIR}/src"

__RESOURCES_DIR = f"{__SRC_DIR}/resources"
KEYS_FILEPATH = f"{__RESOURCES_DIR}/keys.json"
AIRPORTS_FILEPATH = f"{__RESOURCES_DIR}/airports.csv"
COUNTRY_BORDERS_GEOJSON_FILEPATH = \
    f"{__RESOURCES_DIR}/UIA_Latitude_Longitude_Graticules_and_World_Countries_Boundaries.geojson"

__COUNTRIES_SETS_DIR = f"{__RESOURCES_DIR}/countries_sets"
EEE_COUNTRIES_FILEPATH = f"{__COUNTRIES_SETS_DIR}/EEE_countries.json"
ALL_COUNTRIES_FILEPATH = f"{__COUNTRIES_SETS_DIR}/all_countries.json"

__PROBES_DISTRIBUTIONS_DIR = f"{__RESOURCES_DIR}/probes_distributions"
EEE_MESH_3_FILEPATH = f"{__PROBES_DISTRIBUTIONS_DIR}/EEE_mesh_3.json"

# replication package paths
REPLICATION_PACKAGE_DIR = (
    f"{__BASE_DIR}/replication_package_europe_anycast_experiment")
TRAFFIC_LOGS_FILEPATH = f"{REPLICATION_PACKAGE_DIR}/Traffic_logs_10K.csv"
TRAFFIC_LOGS_IP_CLASSIFIED_FILEPATH = \
    f"{REPLICATION_PACKAGE_DIR}/Traffic_logs_10K_ip_classified.csv"
ANYCAST_IP_CLASSIFICATION_FILEPATH = \
    f"{REPLICATION_PACKAGE_DIR}/anycast_ip_classification.json"
ANYCAST_PII_TRAFFIC_LOGS_FILEPATH = \
    f"{REPLICATION_PACKAGE_DIR}/Anycast_PII_traffic_logs.csv"
APKS_METADATA_FILEPATH = f"{REPLICATION_PACKAGE_DIR}/apks_metadata.csv"
IT_ANNOTATION_FILEPATH = \
    f"{REPLICATION_PACKAGE_DIR}/it_annotation_results_Dec_2023.csv"
IT_ANNOTATION_AGGREGATION_FILEPATH = \
    f"{REPLICATION_PACKAGE_DIR}/it_annotation_results_Dec_2023_aggregation.csv"
TPLS_RESULTS_FILEPATH = f"{REPLICATION_PACKAGE_DIR}/TPLs_results.csv"
TPLS_MANUAL_POLICY_INFO = \
    f"{REPLICATION_PACKAGE_DIR}/TPLs_manual_policy_info.csv"
TPLS_POLICY_ANALYSIS = \
    f"{REPLICATION_PACKAGE_DIR}/TPLs_policy_analysis.csv"

PARTIAL_RESULTS_DIR = f"{REPLICATION_PACKAGE_DIR}/partial_results"

# RIPE ATLAS API URLS
__RIPE_ATLAS_API_BASE_URL = "https://atlas.ripe.net/api/v2/"
RIPE_ATLAS_PROBES_BASE_URL = __RIPE_ATLAS_API_BASE_URL + "probes/"

# API Cache IPinfo
IP_URL = str(os.getenv("CACHE_IP_URL")) or ""

# OTHERS
EARTH_RADIUS_KM = 6371
RESULTS_MODES = ["first_ip", "voting"]
