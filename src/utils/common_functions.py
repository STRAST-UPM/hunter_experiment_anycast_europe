#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# external imports
import os
import json
import socket
# internal imports


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
