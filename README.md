## About
KiWI is a lightweight, graphical, curses-based terminal program for
deploying Windows installations over networks. It's recommended
that it be run in a diskless PXE system on the target machine, with
the installation sources being accessed over the network.

You can find instructions on how to do this here:
https://wiki.archlinux.org/index.php/Diskless_system

KiWI was inspired by the Archboot setup wizard.

## Why?

The standard Windows setup is based on Windows PE. It's slow to boot, slow to install, has relatively high requirements for its given task, and it's intentionally crippled in some areas. Namely, the standard Windows installer will not deploy an image to anything but a fixed storage device, and installation sources must be located on the media. Furthermore, certain setup options are unable to be changed by the user, such as custom partitioning options, and filesystem options.

Windows Deployment Services removes some of these limitations, and imposes some of its own. It allows for Windows setup to be network booted, but this functionality requires Windows Server, and the setup is still PE based. Configuration can also be tricky.

Conversely, KiWI is easy to setup, fast to boot (~15 seconds with PXELINUX over GbE with a BTRFS formatted NBD root), fast to install (2-5 minutes, depending on RAM capacity, processor, installation source and target IO throughput), and easily configurable.

KiWI can find and install from bare WIMs available over NFS, SMB, SCP, block devices, or local paths. KiWI supports installing Windows in both MBR/BIOS and GPT/UEFI configurations.

## Limitations
As described in kiwi/BCD.py, the Boot Configuration Data (BCD) store is a mostly undocumented binary file. The way KiWI currently makes Windows deployments bootable is by using a BCD store that was created by Windows, then changing the disk signature of the new install to match the premade BCD. In the future, this should be replaced with a custom BCD creation tool.

### Requirements
* python3
* python-dialog
* parted
* gptfdisk
* ntfsprogs
* ntfs-3g
* dosfstools
* ms-sys
* wimlib

#### Optional:
* nfs-utils
* nbd
* sshfs

## Installation
python setup.py install

## Usage
python -m kiwi.install

## Screenshots
![Main Menu](/screenshots/menu.png?raw=true)
![Sources](/screenshots/sources.png?raw=true)
![Sources](/screenshots/editions.png?raw=true)
![Sources](/screenshots/extraction.png?raw=true)
