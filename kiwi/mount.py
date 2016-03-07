import logging
logger = logging.getLogger()

import subprocess

def mountpoint(path):
    try:
        subprocess.check_call(['mountpoint', path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        return False

    return True

def unmount(path):
    subprocess.check_call(['umount', path])

def mount(src, dst, mkdir=False, force=False):
    if mkdir: subprocess.check_call(['mkdir', '-p', dst])

    if mountpoint(dst):
        logger.warning('Destination %s is already a mountpoint' % dst)
        if force: unmount(dst)
        else: return

    subprocess.check_call(['mount', src, dst])

