# Copyright 2024 Broadcom. All Rights Reserved.
# SPDX-License-Identifier: BSD-2-Clause

"""
This module provides functions for displaying the contents of the kickstart file of the specified ESXi installer ISO.

Created by: Lakshmanan Shanmugam
Authors:    Lakshmanan Shanmugam

Description:
    This script displays the contents of the kickstart file from the specified ESXi ISO image.

Usage:
    python display-ks-content.py -i <path_to_esxi_iso>

Example:
    python display-ks-content.py -i VMware-VMvisor-Installer-8.0U2-22380479.x86_64-20240610-135902.iso
"""

# Standard library imports.
import argparse
import os
import subprocess
import sys

# Local application imports.
import constants
from LogUtility import logger


def run_subprocess_cmd(cmd, description):
    """
    Executes a system command and returns the output.

    Args:
        cmd (str): The system command to execute.
        description (str): A description of the command being executed.

    Returns:
        str: The output from the command execution.
    """
    try:
        output = subprocess.run([cmd], shell=True, capture_output=True, text=True)
        if output.returncode != 0:
            logger.error(output.stderr)
            logger.error(f"{description} cmd did not run successfully, exiting...")
            sys.exit()
        else:
            logger.info(f"{description} cmd ran successfully")
            return output.stdout
    except subprocess.CalledProcessError as e:
        logger.error("Error occurred:", e)


def display_ks_file(iso_file):
    """
    Displays the kickstart file content of the specified ESXi ISO.

    Args:
        iso_path (str): The path to the ESXi ISO file.

    Returns:
        None
    """
    mnt_folder = constants.ESXI_CDROM_MOUNT_DIR
    if os.path.exists(mnt_folder):
        os.rmdir(mnt_folder)
    os.makedirs(mnt_folder)
    # Mount the ISO file, display the content, and umount.
    run_subprocess_cmd(f"mount -o loop {iso_file} {mnt_folder}", "Mounting ISO")
    KS_file = f"{mnt_folder}/KS.CFG"
    if os.path.exists(KS_file):
        with open(KS_file, "r") as file_handle:
            logger.info(
                f"===========================START OF KS FILE=======================================\n {file_handle.read()}\n===========================END OF KS FILE======================================="
            )
    else:
        logger.error("The KS.CFG file was not found in the provided ISO file.")
    run_subprocess_cmd(f"umount {mnt_folder}", "Unmounting ISO")
    os.rmdir(mnt_folder)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Script to display the kickstart file content of the specified ESXi ISO"
    )
    parser.add_argument("-i", "--iso", help="Input ISO file", required=True)
    args = parser.parse_args()
    display_ks_file(args.iso)
