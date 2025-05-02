# © Broadcom. All Rights Reserved.
# The term "Broadcom" refers to Broadcom Inc. and/or its subsidiaries.
# SPDX-License-Identifier: MPL-2.0

# Standard library imports.
import logging
import os

# Local application imports.
import constants

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not os.path.exists(constants.LOG_PATH):
    os.makedirs(constants.LOG_PATH)
formatter = logging.Formatter(
    "%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%dT%I:%M:%S"
)
File_Handler = logging.FileHandler(
    "{}{}".format(constants.LOG_PATH, constants.LOG_FILE_NAME)
)
File_Handler.setFormatter(formatter)
logger.addHandler(File_Handler)
Stream_Handler = logging.StreamHandler()
Stream_Handler.setFormatter(formatter)
logger.addHandler(Stream_Handler)
