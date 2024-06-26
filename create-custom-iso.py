# Copyright 2024 Broadcom. All Rights Reserved.
# SPDX-License-Identifier: BSD-2-Clause

""" 
This module provides functions for imaging an ESXi host.

==============================================
Created by: Lakshmanan Shanmugam
Authors:    Lakshmanan Shanmugam, Sowjanya V
==============================================

Description:
Generate a single ISO image for a group of servers using the standard ESXi installation ISO image, 
an input JSON file, and a firstboot-scripts file containing post-install commands. 
The JSON file specifies the network and other details required for the installation

Example:
python create-custom-iso.py -j re-image-hosts.json
"""
import re
import hashlib
import json
import random
import string
import sys
import ipaddress
import subprocess
import argparse
import os
import psutil       
import shutil
from LogUtility import logger
import maskpass
import constants
import time

def run_subprocess_cmd(cmd,description):
    """
    This function is used to execute system commands and then return the output.
    """
    try:
        output= subprocess.run([cmd], shell=True, capture_output=True, text=True)
        if output.returncode != 0:
            logger.error(output.stderr)
            logger.error(f'{description} command did not run successfully. Exiting...')
            sys.exit()
        else:
            logger.info(f'{description} cmd ran successfully.')
            return output.stdout
    except subprocess.CalledProcessError as e:
        logger.error("Error occurred:", e)

def generate_encrypted_root_pwd():
    """
    This function is used to convert a plain text password into an encrypted one.
    """
    counter = 2
    esxi_root_pwd1= maskpass.askpass(\
        prompt="Enter the password for the ESXi root account : ", mask="*"\
        )
    esxi_root_pwd2= maskpass.askpass(\
        prompt="Re-enter the password for the ESXi root account : ", mask="*"\
        )
    while counter and esxi_root_pwd1 != esxi_root_pwd2:
        counter = counter - 1
        logger.warning ("Password does not match, re-enter correct password...")
        esxi_root_pwd1= maskpass.askpass(\
            prompt="Enter the password for the ESXi root account : ", mask="*"\
            )
        esxi_root_pwd2= maskpass.askpass(\
            prompt="Re-enter the password for the ESXi root account : ", mask="*"\
            )

    if esxi_root_pwd1 != esxi_root_pwd2:
        logger.error ("Password does not match. Exiting...")
        sys.exit()

    logger.debug ("The password entered has been verified.")
    logger.info('Generating an encrypted password for the ESXi root account using a SHA512-based password algorithm.')
    cmd_output= run_subprocess_cmd(f"openssl passwd -6 {esxi_root_pwd1}", \
                                   "Generate an encrypted password")
    return cmd_output

def case_insensitive_search_and_replace(file_path, search_word, replace_word):
    """
    This function is used to find and replace a word.
    """
    with open(file_path, 'r') as file: 
        file_contents = file.read()
        pattern = re.compile(re.escape(search_word), re.IGNORECASE)
        updated_contents = pattern.sub(replace_word, file_contents)

    with open(file_path, 'w') as file: 
        file.write(updated_contents)

def validate_ip(ip):
    """
    This function is used to check if the given ipaddress is valid.
    """
    # Regular expression pattern for IPv4 with each octet ranging from 0 to 255
    ipv4_pattern = \
        r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'

    # Check if it matches IPv4 pattern
    if re.match(ipv4_pattern, ip):
        try:
            # If it's a valid IPv4 address, parse it
            ipaddress.IPv4Address(ip)
            return True
        except ipaddress.AddressValueError:
            return False
    else:
        return False
   
def validate_mac(mac):
    """
    This function is used to check if the given macaddress is valid.
    """
    # Regular expression pattern for MAC addresses
    mac_pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'

    # Check if it matches MAC address pattern
    return bool(re.match(mac_pattern, mac))

def validate_json(json_data):
    """
    This function checks the validity of the network parameters in the provided JSON file.
    """
    error_string = False
    validate_set_dns = json_data.get('dns', None)
    validate_set_hosts = ['macAddress', 'mgmtIpv4', 'mgmtGateway', 'mgmtNetmask']
    if validate_set_dns:
        for validate_item in validate_set_dns: 
            if not validate_ip(validate_item):
                error_string = True
                logger.error(f"Invalid data is provided in JSON for the nameserver: '{validate_item}.'")

    for host_data in json_data['hosts']:
        for validate_item in validate_set_hosts: 
            if validate_item == 'macAddress':
                if not validate_mac(host_data[validate_item]):
                    error_string = True
                    logger.error(f"Invalid data is provided in JSON for '{validate_item}' for the host {host_data['hostName']}.")
            else:
                if host_data[validate_item].lower() != 'dhcp':
                    if not validate_ip(host_data[validate_item]):
                        error_string = True
                        logger.error(f"Invalid data is provided in JSON for '{validate_item}' for the host {host_data['hostName']}.")
                else:
                    break
  
    if error_string:
        logger.error("Validation of JSON for valid IP address and MAC address failed.")
        return False
    logger.info("Validation of JSON for valid IP address and MAC address is successful.")
    return True

def get_file_size(file_path):
    """
    This function retrieves the size of a file.
    """
    size_bytes = os.path.getsize(file_path)
    size_readable = convert_size(size_bytes)
    return size_bytes, size_readable

def convert_size(size_bytes):
    """
    This function is used to convert bytes to a human-readable format.
    """
    # Define suffixes for different size units
    suffixes = ['B', 'KB', 'MB', 'GB', 'TB']
    # Calculate appropriate unit and size
    index = 0
    while size_bytes >= 1024 and index < len(suffixes) - 1:
        size_bytes /= 1024
        index += 1
    # Return the formatted size
    return f"{size_bytes:.2f} {suffixes[index]}"

def enough_disk_space(path, required_space):
    """
    This function is used to check if there is enough disk space.
    """
    disk_usage = psutil.disk_usage(path)
    available_space = disk_usage.free
    return available_space >= required_space

def validate_disk_space(iso):
    """
    This function checks whether there is enough disk space to perform a copy operation.
    """
    file_path = iso
    size_bytes, size_readable = get_file_size(file_path)
    logger.debug(f"The size of '{file_path}' is {size_readable}.")
    path_to_check = "./"  # Path to the drive you want to check
    required_space_bytes = 2 * size_bytes  # double the size of the iso file
    if enough_disk_space(path_to_check, required_space_bytes):
        logger.debug(f"The required disk space is: {convert_size(required_space_bytes)}")
        logger.info(f"The directory '{os.getcwd()}' has sufficient disk space.")
        return True
    logger.error(f"There is not enough disk space in the {os.getcwd()} directory. Exiting...")
    return False

def validate_iso_chksum(iso_file_name, chksum):
    """
    This function is used to verify the checksum for the provided ISO image.
    """
    calculated_chksum = hashlib.md5(open(iso_file_name,'rb').read()).hexdigest() 
    if calculated_chksum == chksum:
        logger.info("The checksum has been matched, proceeding.")
        return True
    logger.error(f"Given checksum '{chksum}' did not match. Exiting...")
    return False

def build_custom_image(json_data, encrypted_root_pwd, iso_suffix=None):
    """
    This function is used to create an installation script and then generate an ISO image by embedding the installation script into the given ISO image.
    """
    esxi_iso_file = (json_data['esxiIsoFileName']).strip()
    isochecksum = (json_data['isoMdSum']).strip()
    dns_suffix_0 = json_data.get('dnsSuffix0')
    dns = json_data.get('dns', None)
    mnt_folder = constants.ESXI_CDROM_MOUNT_DIR
    esxi_root_pwd = encrypted_root_pwd
    esxi_eula = (json_data['AcceptEsxiLicenseAgreement']).strip()
    
    #validate esxi eula value
    if not esxi_eula == "Yes":
        logger.error("ESXi license not accepted. Please accept the ESXi license agreement by providing the option 'Yes' in the JSON file")
        sys.exit()
    esxi_eula_value = "vmaccepteula"
    #validate json before proceeding
    if not validate_json(json_data):
        sys.exit()
    #check if base ESXi ISO file exists in the current dir
    if not os.path.exists(esxi_iso_file):
        logger.error(f"The ISO file named '{esxi_iso_file}' does not exist in the '{os.getcwd()}' directory. Exiting...")
        sys.exit()
    #validate disk space before proceeding
    if not validate_disk_space(esxi_iso_file):
        sys.exit()
    #validate checksum
    if not validate_iso_chksum(esxi_iso_file,isochecksum):
        sys.exit()

    #Create random string and create folders
    RANDOM_STRING =''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    temp_folder = os.path.join('./temp/',RANDOM_STRING)
    if not os.path.exists(constants.LOG_PATH):
        os.makedirs(constants.LOG_PATH)
    if  os.path.exists(mnt_folder):
        os.rmdir(mnt_folder) 
    os.makedirs(mnt_folder)
    os.makedirs(temp_folder)
    
    # mount the ISO file, copy the contents into the temp folder and umount
    run_subprocess_cmd(f'mount -o loop {esxi_iso_file} {mnt_folder}', "Mounting ISO")
    run_subprocess_cmd(f'cp -r {mnt_folder}/* {temp_folder}', "Copying the ISO")
    run_subprocess_cmd(f'umount {mnt_folder}',"Unmounting ISO")
    os.rmdir(mnt_folder)

    #Update boot.cfg
    boot_config_file_path = os.path.join(temp_folder, 'boot.cfg')
    boot_config_file_path2 = os.path.join(temp_folder, 'efi/boot/boot.cfg')
    case_insensitive_search_and_replace(boot_config_file_path, 'kernelopt=runweasel', 'kernelopt=runweasel ks=cdrom:/KS.CFG')
    case_insensitive_search_and_replace(boot_config_file_path2, 'kernelopt=runweasel', 'kernelopt=runweasel ks=cdrom:/KS.CFG')
    case_insensitive_search_and_replace(boot_config_file_path, 'kernelopt=cdromBoot runweasel', 'kernelopt=runweasel ks=cdrom:/KS.CFG')
    case_insensitive_search_and_replace(boot_config_file_path2, 'kernelopt=cdromBoot runweasel', 'kernelopt=runweasel ks=cdrom:/KS.CFG')
    case_insensitive_search_and_replace(boot_config_file_path, 'kernelopt=runweasel cdromBoot', 'kernelopt=runweasel ks=cdrom:/KS.CFG')
    case_insensitive_search_and_replace(boot_config_file_path2, 'kernelopt=runweasel cdromBoot', 'kernelopt=runweasel ks=cdrom:/KS.CFG')
    #Create KS.CFG
    temp_path =  os.path.join(temp_folder, 'KS.CFG') 
    ks_file = open(temp_path, 'w+') 
    # Add primary info into the KS.CFG
    ks_file.write(f'{esxi_eula_value} \n')
    ks_file.write(f'rootpw --iscrypted {esxi_root_pwd}')
    ks_file.write('%include /tmp/pre_script.cfg\n')
    ks_file.write('reboot \n')
    # Add firstboot
    ks_file.write('\n%firstboot --interpreter=busybox\n')   
    # Add post installation commands from firstboot-scripts.txt
    file_path = "firstboot-scripts.txt"
    with open(file_path, "r") as file: 
        file_contents = file.read()
    for line in (file_contents):
        ks_file.write(line)
    # Add network and install media info under pre-script for each host
    ks_file.write('\n\n%pre --interpreter=busybox \n')
    for host in json_data['hosts']:
        server_mac_adress = (host['macAddress']).lower()
        clear_part = host.get('clearPart')
        install_disk = (host['installDisk']).strip()
        mgmt_ipv4 = host['mgmtIpv4']
        vlan = (host['mgmtVlanId']).strip()     
        ks_file.write(f'if esxcfg-nics -l | grep -q "{server_mac_adress}"\n')
        ks_file.write('then\n')
        if clear_part:
            logger.debug(f'The value provided for the clearPart is "{clear_part.strip()}" for the host with the MAC address {server_mac_adress}')
            ks_file.write(f'echo clearpart {clear_part.strip()} >> /tmp/pre_script.cfg\n')
        if mgmt_ipv4.lower() =='dhcp':
            network_cmd = f'network --bootproto=dhcp --vlanid={vlan} --device={server_mac_adress}'
        else:
            host_name = (host['hostName']).strip()
            mgmt_net_mask = host['mgmtNetmask']
            mgmt_gw = host['mgmtGateway']
            mgmt_hostname =".".join([host_name,dns_suffix_0] if dns_suffix_0 else [host_name])
            if dns:
                dns_string = ",".join(dns)
                network_cmd = f'network --bootproto=static --ip={mgmt_ipv4} --netmask={mgmt_net_mask} --gateway={mgmt_gw} --vlanid={vlan} --hostname={mgmt_hostname} --device={server_mac_adress} --nameserver={dns_string.strip()}'
            else:
                network_cmd = f'network --bootproto=static --ip={mgmt_ipv4} --netmask={mgmt_net_mask} --gateway={mgmt_gw} --vlanid={vlan} --hostname={mgmt_hostname} --device={server_mac_adress}'
        ks_file.write(f'echo {network_cmd} >> /tmp/pre_script.cfg \n')
        logger.debug(f'The value provided for the network is "{network_cmd}" for the host with the MAC address {server_mac_adress}')          

        allowed_install_disks = {'usb', 'local'}
        if install_disk not in allowed_install_disks and not install_disk.startswith('--'):
            raise ValueError(f"Invalid install_disk value: {install_disk}")

        disk_commands = {
            'usb': '--firstdisk=usb --overwritevmfs',
            'local': '--firstdisk=local --overwritevmfs',
        }
        if install_disk in disk_commands:
            ks_file.write(f"echo install {disk_commands[install_disk]} >> /tmp/pre_script.cfg\n")
            logger.debug(f'The value provided for the install disk is "{install_disk}"({disk_commands[install_disk]}) for the host with the MAC address {server_mac_adress}')
        else:
            ks_file.write(f"echo install {install_disk} >> /tmp/pre_script.cfg\n")
            logger.debug(f'The value provided for the install disk is "{install_disk}" for the host with the MAC address {server_mac_adress}')
        ks_file.write("fi\n")
    ks_file.close()
    #Create ISO with updated KS file and remove temp folder
    if iso_suffix:
        iso_file_name = f'{esxi_iso_file.split(".iso")[0]}-{iso_suffix}.iso'
    else:
        iso_file_name = f'{esxi_iso_file.split(".iso")[0]}-{time.strftime("%Y%m%d-%H%M")}.iso'
    cmd=f'mkisofs -relaxed-filenames  -quiet  -J -R -o {iso_file_name} -b isolinux.bin -c boot.cat -no-emul-boot -boot-load-size 4 -boot-info-table -eltorito-alt-boot -e efiboot.img -no-emul-boot {temp_folder}'
    run_subprocess_cmd(cmd,"Create an ISO with the updated KS file")
    md5_chksum=hashlib.md5(open(iso_file_name,'rb').read()).hexdigest() 
    # Delete the temp folder and all of its contents
    shutil.rmtree(temp_folder)
    shutil.rmtree("./temp")
    logger.debug(f"Temp directory '{temp_folder}' and './temp' have been deleted.")
    logger.info(f"The ESXi image '{iso_file_name}' has been created with the installation script.Its MD5 checksum is :{md5_chksum}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Script for creating an ESXi ISO file with a kickstart file from the base ESXi ISO.')
    parser.add_argument( '-j', '--json',help='Specify the input JSON file', required=True)
    parser.add_argument( '-s', '--suffix', help='Specify the suffix to be used in the output ISO file', required=False)
    args = parser.parse_args()

    rootw_pwd=generate_encrypted_root_pwd()
    with open(args.json) as file_handle: 
        json_file = json.load(file_handle)

    # Create custom ISO
    build_custom_image(json_file, rootw_pwd, args.suffix)
