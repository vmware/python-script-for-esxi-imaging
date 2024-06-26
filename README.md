<!--
Copyright 2023-2024 Broadcom. All rights reserved.
SPDX-License-Identifier: BSD-2
-->

<!-- markdownlint-disable first-line-h1 no-inline-html -->

# Python Script for ESXi Imaging

## Table of Contents

- [Python Script for ESXi Imaging](#python-script-for-esxi-imaging)
  - [Table of Contents](#table-of-contents)
  - [Introduction](#introduction)
  - [Requirements](#requirements)
    - [System Requirements](#system-requirements)
    - [ESXi](#esxi)
    - [Operating System](#operating-system)
    - [Python](#python)
  - [Generating the ESXi ISO Image](#generating-the-esxi-iso-image)
  - [Troubleshooting](#troubleshooting)
  - [Limitations](#limitations)
  - [Known Issues](#known-issues)
  - [Contributing](#contributing)
  - [Support](#support)
  - [License](#license)

## Introduction

The Python Script for ESXi Imaging creates an ESXi ISO image with an installation script (kickstart file) from the base ISO image to automate ESXi installation and configuration for VMware vSphere Foundation (VVF) and VMware Cloud Foundation (VCF).

The Python script uses the `re-image-hosts.json` and `firstboot-scripts.txt` files to generate the required installation script.

## Requirements

### System Requirements

To install ESXi, your system must meet specific requirements. Refer the [ESXi Requirements][docs-esxi-requirements] for more details.

### ESXi

- ESXi 7.0 or later.
- The ESXi installer ISO image `VMware-VMvisor-Installer-x.x.x-XXXXXX.x86_64.iso`, where `x.x.x` is the version of ESXi you are installing, and `XXXXXX` is the build number of the installer ISO image.

### Operating System

- [VMware Photon OS][info-photon] 4.0 Rev2

  - You can use the [Photon OS sample appliance][download-sample-appliance] or use the code from the [GitHub project][gh-sample-appliance] to build the appliance.
  - The sample appliance includes all required packages, otherwise, you must install the following packages:

    ```console
    tdnf install -y \
      git \
      python3-pip \
      cdrkit
    ```

  - Ensure you have enough space to generate the ISO files.

### Python

- [Python 3.10][info-python], included by default on Photon OS 4.0 Rev2.

- The sample appliance includes all required Python packages, otherwise you must install the following packages:

  ```console
  pip install maskpass==0.3.1
  pip install psutil
  ```

## Generating the ESXi ISO Image

1. Use a Secure Shell (SSH) client to log in as the `root` user to the photon appliance at `<host_virtual_machine_fqdn>:22`.
2. Clone the repository into a directory.

   ```console
   git clone https://github.com/vmware/python-script-for-esxi-imaging.git
   cd python-script-for-esxi-imaging
   ```

3. Download the ESXi installer (ISO file) from your OEM or the [Broadcom Support Portal][kb-broadcom-downloads] and place the ISO file in the `esxi-imaging` directory.
4. Modify the [`re-image-hosts.json`][sample-json] file to update details like the ISO file name, MD5 checksum, network configuration, and installation disk.

   | Information                  | Required or Optional   | Comments                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
   | ---------------------------- | ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
   | `esxiIsoFileName`            | Required               | Specifies the filename of the ESXi installer image. Must available in the directory where the script is run.                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
   | `isoMdSum`                   | Required               | Specifies the MD5 checksum of the ESXI installer image.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
   | `AcceptEsxiLicenseAgreement` | Required               | Specify option `Yes` to accept the ESXi license agreement. By using the automation, you are accepting EULA for the ESXi                                                                                                                                                                                                                                                                                                                                                                                                                                               |
   | `dns`                        | Required for Static IP | Specifies the DNS servers for the ESXi host. Accepts up to two entries.<br/><br/>Example:<br/><br/> 1. `"dns": ["172.16.11.4","172.16.11.5"]`<br/> 2. `"dns": ["172.16.11.4"]`                                                                                                                                                                                                                                                                                                                                                                                        |
   | `dnsSuffix0`                 | Required for Static IP | Specifies the DNS suffix for the ESXi host.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
   | `macAddress`                 | Required               | Specifies the MAC address of the network card used by the ESXi host. The management network will be mapped to the specified network adapter after the ESXi installation.                                                                                                                                                                                                                                                                                                                                                                                              |
   | `hostName`                   | Required for Static IP | Specifies the hostname for the ESXi host.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
   | `clearPart`                  | Optional               | Specifies to clear any existing partitions on the disk of the ESXi host. <br/><br/>Example:<br/><br/> `"clearPart": "--alldrives --overwritevmfs"` --> Allows clearing of partitions on every drive. Refer to the sample JSON and [product documentation][vsphere8-esxi-installation] for more details.                                                                                                                                                                                                                                                               |
   | `installDisk`                | Required               | Specifies the disk to install ESXi. <br/><br/>Examples:<br/><br/> 1. `"installDisk": "local"` --> Deletes the existing VMFS partitions and installs the image on the first eligible disk found.<br/> 2.`"installDisk": "usb"` ---> Deletes the existing VMFS partitions and install the image on the USB or SD device.<br/> 3. `"installDisk": "--firstdisk=ATA --overwritevmfs"` ---> Deletes the existing VMFS partitions and install the image on the ATA disk. Refer to the sample JSON and [product documentation][vsphere8-esxi-installation] for more details. |
   | `mgmtIpv4`                   | Required               | Specifies the IPv4 address for the ESXi host. <br/><br/>Examples:<br/><br/> 1. `"mgmtIpv4": "dhcp"`<br/> 2.`"mgmtIpv4": "172.16.11.101"`                                                                                                                                                                                                                                                                                                                                                                                                                              |
   | `mgmtGateway`                | Required for Static IP | Specifies the IPv4 default gateway for the ESXi host.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
   | `mgmtVlanId`                 | Required               | Specifies the VLAN for the ESXi host management network. Used with either DHCP or a static IP address.                                                                                                                                                                                                                                                                                                                                                                                                                                                                |

5. If required, update the `firstboot-scripts.txt` file. Add the post-install commands that need to be run once the installation is completed. By default, SSH and ESXi shell are enabled. Additionally, the self-signed certificate on all ESXi hosts will be regenerated.
6. Run the following command to generate the ISO file.

   ```console
   python create-custom-iso.py -j re-image-hosts.json
   ```

   If you are using the [Photon OS sample appliance][download-sample-appliance] and logged in as the `admin` user, run the command with sudo.

   ```console
   sudo python create-custom-iso.py -j re-image-hosts.json
   ```

7. Enter and confirm the password for the ESXi root account.

The script generates an ISO file with a timestamp that includes the kickstart file after successful validation. If the optional parameter `-s` or `--suffix` is specified in the command line, the given value will be appended to the output ISO file instead of the timestamp.

You can use this ISO installer image for regular boot or UEFI boot.

You can use the [remote management applications][docs-esxi-install-remote-management-applications] to install ESXi hosts remotely.

## Troubleshooting

- If the specified MAC address in JSON does not match with the host then the installation wizard would throw an error:

  ```console
  An error has occurred while parsing the installation script. Could not open the file. no such file or directory.
  ```

  Ensure that proper MAC address is specified.

- If you encounter an error like:

  ```console
  mkisofs: command not found
  ERROR Create an ISO with the updated KS file command did not run successfully. Exiting...
  ```

  Ensure that `mkisofs` is available. If not, install the `cdrkit` package and try again.

- After the installation is complete, if the firstboot scripts are not run, please refer to `/var/log/kickstart.log`.
- To view the kickstart file's content in the generated ISO file, run the following command

  ```console
  python display-ks-content.py -i <your_generated_iso_file>
  ```
   If you are using the [Photon OS sample appliance][download-sample-appliance], run the command with sudo.
  ```console
    sudo python display-ks-content.py -i <your_generated_iso_file>
    ```

## Limitations

- Does not support upgrades; only the installation scenario is supported.

## Known Issues

- If secure boot is enabled, the commands in the `firstboot-scripts.txt` file will not be executed.

## Contributing

The project team welcomes contributions from the community. Before you start working with project, please read our
[Developer Certificate of Origin][vmware-cla-dco].

All contributions to this repository must be signed as described on that page. Your signature certifies that you wrote the patch or have the right to pass it on as an open-source patch.

For more detailed information, refer to the [contribution guidelines][gh-contributing] to get started.

This project is the work of many contributors and the project team appreciates your help!

- [Lakshmanan Shanmugam](https://github.com/slakshmanan2706), Maintainer
- [Ivaylo Ivanov](https://github.com/joisika), Collaborator
- [Ryan Johnson](https://github.com/tenthirtyam), Collaborator
- [Bhumitra Nagar](https://github.com/bhumitra), Collaborator
- [Sowjanya V](https://github.com/sowjuec), Collaborator

## Support

This Python module is not supported by VMware Support Services.

We welcome you to use the [GitHub Issues][gh-issues] to report bugs or suggest enhancements.

In order to have a good experience with our community, we recommend that you read the [contributing guidelines][gh-contributing].

When filing an issue, please check existing open, or recently closed, issues to make sure someone else hasn't already
reported the issue.

Please try to include as much information as you can. Details like these are incredibly useful:

- A reproducible test case or series of steps.
- Any modifications you've made relevant to the bug.
- Anything unusual about your environment or deployment.

## License

Copyright 2024 Broadcom. All Rights Reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

[//]: Links
[docs-esxi-install-remote-management-applications]: https://docs.vmware.com/en/VMware-vSphere/8.0/vsphere-esxi-installation/GUID-0E82A6CA-202A-4C5D-8811-53A7CF8D5CDC.html
[docs-esxi-requirements]: https://docs.vmware.com/en/VMware-vSphere/8.0/vsphere-esxi-installation/GUID-DEB8086A-306B-4239-BF76-E354679202FC.html
[download-sample-appliance]: https://broadcom.box.com/v/get-vvs-sample-appliance
[gh-contributing]: CONTRIBUTING.md
[sample-json]: re-image-hosts.json
[gh-issues]: https://github.com/vmware/
[vmware-cla-dco]: https://cla.vmware.com/dco
[gh-sample-appliance]: https://github.com/vmware-samples/validated-solutions-for-cloud-foundation/tree/main/appliance
[info-photon]: https://vmware.github.io/photon/
[info-python]: https://www.python.org
[kb-broadcom-downloads]: https://knowledge.broadcom.com/external/article?articleId=142814
[vsphere8-esxi-installation]: https://docs.vmware.com/en/VMware-vSphere/8.0/vsphere-esxi-installation/GUID-51BD0186-50BF-4D0D-8410-79F165918B16.html
