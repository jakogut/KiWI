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
    subprocess.check_call(['umount', path], stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE)

def mount(src, dst, options='', **kwargs):
    if kwargs.get('mkdir'): subprocess.check_call(['mkdir', '-p', dst])

    if mountpoint(dst):
        logger.warning('Destination %s is already a mountpoint' % dst)
        if kwargs.get('force'): unmount(dst)
        else: return

    call = ['mount', src, dst]

    if kwargs.get('type'): call += ['-t', type]

    if kwargs.get('bind'): options += ',bind'
    if kwargs.get('ro'):   options += ',ro'

    if options:
        call.append('-o')
        call.append(options)

    subprocess.check_call(call, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)

