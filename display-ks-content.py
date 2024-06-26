# Copyright 2024 Broadcom. All Rights Reserved.
# SPDX-License-Identifier: BSD-2-Clause

"""
This module provides functions for displaying the contents of the kickstart file of the specified ESXi installer ISO.

==============================================
Created by: Lakshmanan Shanmugam
Authors:    Lakshmanan Shanmugam
==============================================

Description:
Display the kickstart file content of the specified ESXi ISO

Example:
python display-ks-content.py -i VMware-VMvisor-Installer-8.0U2-22380479.x86_64-20240610-135902.iso
"""

import sys
import subprocess
import argparse
import os
from LogUtility import logger
import constants

def run_subprocess_cmd(cmd, description):
    """
    This function is used to execute system commands and return the output.
    """
    try:
        output = subprocess.run(
            [cmd], shell=True, capture_output=True, text=True)
        if output.returncode != 0:
            logger.error(output.stderr)
            logger.error(
                f'{description} cmd did not run successfully, exiting...')
            sys.exit()
        else:
            logger.info(f'{description} cmd ran successfully')
            return output.stdout
    except subprocess.CalledProcessError as e:
        logger.error("Error occurred:", e)

def display_ks_file(iso_file):
    """
    This function is used to display the kickstart file content of the specified ESXi ISO.
    """
    mnt_folder = constants.ESXI_CDROM_MOUNT_DIR
    if os.path.exists(mnt_folder):
        os.rmdir(mnt_folder)
    os.makedirs(mnt_folder)
    # mount the ISO file, display the content and umount
    run_subprocess_cmd(f'mount -o loop {iso_file} {mnt_folder}', "Mounting ISO")
    KS_file = f"{mnt_folder}/KS.CFG"
    if (os.path.exists(KS_file)):
        with open(KS_file, 'r') as file_handle:
            logger.info(f"===========================START OF KS FILE=======================================\n {file_handle.read()}\n===========================END OF KS FILE=======================================")
    else:
        logger.error("The KS.CFG file was not found in the provided ISO file.")
    run_subprocess_cmd(f'umount {mnt_folder}', "Unmounting ISO")
    os.rmdir(mnt_folder)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Script to display the kickstart file content of the specified ESXi ISO')
    parser.add_argument('-i', '--iso', help='Input ISO file', required=True)
    args = parser.parse_args()
    display_ks_file(args.iso)

