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

# providers classification paths
PROVIDERS_CLASSIFICATION_DIR = \
    f"{REPLICATION_PACKAGE_DIR}/providers_classification"
ANYCAST_DESTINATIONS_FILEPATH = \
    f"{PROVIDERS_CLASSIFICATION_DIR}/anycast_destinations.csv"
ANYCAST_PROVIDER_CLASSIFICATION_FILEPATH = \
    f"{PROVIDERS_CLASSIFICATION_DIR}/anycast_provider_classification.csv"
ANYCAST_EDGE_HEADERS_CHECK_FILEPATH = \
    f"{PROVIDERS_CLASSIFICATION_DIR}/anycast_edge_headers_check.csv"
ANYCAST_SCENARIOS_FILEPATH = \
    f"{PROVIDERS_CLASSIFICATION_DIR}/anycast_scenarios.csv"
ANYCAST_EDGE_HEADERS_CALIBRATION_FILEPATH = \
    f"{PROVIDERS_CLASSIFICATION_DIR}/anycast_edge_headers_calibration.csv"
PROVIDERS_SOURCES_DIR = f"{PROVIDERS_CLASSIFICATION_DIR}/sources"
ASN_DB_FILEPATH = f"{PROVIDERS_SOURCES_DIR}/ipasn.dat"
IP_RANGES_HISTORY_DIR = f"{PROVIDERS_SOURCES_DIR}/ip_ranges_history"
# Hunter results used by the providers classification (same mode as the analysis notebook)
HUNTER_ANALYSIS_MODE = "voting"
ROUTES_FREQUENCY_NON_SUSPICIOUS_FILEPATH = (
    f"{REPLICATION_PACKAGE_DIR}/analysis_{HUNTER_ANALYSIS_MODE}/"
    f"routes_frequency_non_suspicious_{HUNTER_ANALYSIS_MODE}.csv")
ANYCAST_HUNTER_PAIR_DESTINATIONS_FILEPATH = \
    f"{PROVIDERS_CLASSIFICATION_DIR}/anycast_hunter_pair_destinations.csv"
ANYCAST_HUNTER_IP_DESTINATIONS_FILEPATH = \
    f"{PROVIDERS_CLASSIFICATION_DIR}/anycast_hunter_ip_destinations.csv"
ANYCAST_SCENARIOS_HUNTER_CROSS_FILEPATH = \
    f"{PROVIDERS_CLASSIFICATION_DIR}/anycast_scenarios_hunter_cross.csv"
ANYCAST_SCENARIOS_HUNTER_SUMMARY_FILEPATH = \
    f"{PROVIDERS_CLASSIFICATION_DIR}/anycast_scenarios_hunter_summary.csv"

# RIPE ATLAS API URLS
__RIPE_ATLAS_API_BASE_URL = "https://atlas.ripe.net/api/v2/"
RIPE_ATLAS_PROBES_BASE_URL = __RIPE_ATLAS_API_BASE_URL + "probes/"

# API Cache IPinfo
IP_URL = str(os.getenv("CACHE_IP_URL")) or ""

# OTHERS
EARTH_RADIUS_KM = 6371
RESULTS_MODES = ["first_ip", "voting"]
