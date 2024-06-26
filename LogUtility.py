# Copyright 2024 Broadcom. All Rights Reserved.
# SPDX-License-Identifier: BSD-2-Clause

import logging
import constants
import os

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not os.path.exists(constants.LOG_PATH):
    os.makedirs(constants.LOG_PATH)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s', datefmt="%Y-%m-%dT%I:%M:%S")
File_Handler = logging.FileHandler('{}{}'.format(constants.LOG_PATH, constants.LOG_FILE_NAME))
File_Handler.setFormatter(formatter)
logger.addHandler(File_Handler)
Stream_Handler = logging.StreamHandler()
Stream_Handler.setFormatter(formatter)
logger.addHandler(Stream_Handler)
