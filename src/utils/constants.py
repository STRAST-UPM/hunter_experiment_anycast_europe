#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# external imports
import os
# internal imports

__BASE_DIR = \
    f"{os.path.dirname(os.path.dirname(os.path.abspath(__file__)))}/.."

# src folder paths
__SRC_DIR = f"{__BASE_DIR}/src"
KEYS_FILEPATH = f"{__SRC_DIR}/resources/keys.json"
