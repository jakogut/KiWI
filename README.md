## About
KiWI is a lightweight, graphical, curses-based terminal program for
deploying Windows installations over networks. It's recommended
that it be run in a diskless PXE system on the target machine, with
the installation sources being accessed over the network.

You can find instructions on how to do this here:
https://wiki.archlinux.org/index.php/Diskless_system

KiWI was inspired by the Archboot setup wizard.

### Requirements
python3
python-dialog
gparted
ntfsprogs
dosfstools
ms-sys
wimlib

#### Optional:
nfs-utils
nbd
sshfs

## Installation
python setup.py install
