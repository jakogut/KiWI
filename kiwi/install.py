import locale
from dialog import Dialog

locale.setlocale(locale.LC_ALL, '')

import sys, os
import glob
import re
import subprocess
from time import sleep

import logging
import logging.handlers

from .interface import *
from .mount import *

logger = logging.getLogger()

class WindowsInstallApp(object):
    def __init__(self):
        self.logger = logging.getLogger(__name__)

        self.boot_part = ''
        self.system_part = ''

        self.d = Dialog(dialog='dialog')
        self.d.set_background_title('KiWI: Killer Windows Installer')

        networking_items = [
            ('Connect to Wireless Network', self.launch_wicd)]

        networking_submenu = Menu(self.d, networking_items, 'Network Configuration')

        self.source_dir = '/mnt/source'

        source_items = [
            ('Block Device (USB, CD/DVD, etc.)', None),
            ('Network (NFS)', MenuItem(self.prepare_source)),
        ]

        source_submenu = Menu(self.d, source_items, 'Select Installation Source')

        partitioning_items = [
            ('Auto-Prepare (erases the ENTIRE storage drive)', MenuItem(self.auto_prepare)),
        ]

        partitioning_submenu = Menu(self.d, partitioning_items, title='Partition Drives')

        main_menu_items = [
            ('Configure Networking', networking_submenu),
            ('Prepare Storage Device', partitioning_submenu),
            ('Select Installation Source', source_submenu),
            ('Install OS', MenuItem(self.install_os)),
            #('Install Bootloader', self.install_bootloader),
        ]

        self.running = True
        self.main_menu = StatefulMenu(self.d, main_menu_items, title='Main Menu')
        while self.running: self.main_menu.run(ret=self.exit())

    def launch_wicd(self):
        rc = subprocess.call('wicd-curses', shell=True)
        test = subprocess.call(['ping', '-c 2', '-i 0.2', 'google.com'], stdout=subprocess.PIPE)
        if rc == 0 and test == 0: self.main_menu.advance()

    def detect_blockdevs(self):
        def blockdev_size(device):
            nr_sectors = open(device+'/size').read().rstrip('\n')
            sect_size = open(device+'/queue/hw_sector_size').read().rstrip('\n')

            return (float(nr_sectors)*float(sect_size))/(1024.0*1024.0*1024.0)

        dev_pattern = ['hd.*', 'sd.*', 'mmcblk.*']

        devices = []
        for device in glob.glob('/sys/block/*'):
            for pattern in dev_pattern:
                if re.compile(pattern).match(os.path.basename(device)):
                    devices.append(tuple([device, blockdev_size(device)]))

        self.d.msgbox('Detected Devices:\n\n' + '\n'.join(
            [' '.join([path, '%.2f GB' % size]) for path, size in devices]),
            width=40, height=10)

        self.devices = devices

    def select_disk(self):
        self.detect_blockdevs()

        entries = [tuple([path, '-']) for path, _ in self.devices] + [('OTHER', '+')]
        code, tag = self.d.menu('Choose an installation drive', choices=entries, default_item='/sys/block/sdb')
        if code != self.d.OK: return

        if tag == 'OTHER':
            code, tag = self.d.inputbox('Enter a path to a block device')
            if code != self.d.OK: return

            #if not os.path.isfile(tag):
            #    self.d.infobox('File or path does not exist.', width=40)
            #    sleep(3)
            #    return

            import stat
            mode = os.stat(tag).st_mode
            if not stat.S_ISBLK(mode):
                self.d.infobox('File is not a block device.')
                sleep(3)
                return

        confirmation = self.d.inputbox('This will erase ALL data on %s' % tag + \
            '\n\nType \'YES\' to continue', width=40, height=15)
        if confirmation[1] is not 'YES': return

        self.install_drive = tag
        self.logger.info('Block device {} selected for installation'.format(self.install_drive))

    def supports_uefi(self):
        p = subprocess.Popen(['efivar', '-l'])
        uefi = True if p.returncode == 0 else False
        return uefi

    def auto_prepare(self):
        self.auto_partition()
        self.auto_format()

    def auto_partition(self):
        self.select_disk()
        if not hasattr(self, 'install_drive'):
            return

        self.logger.info('Partitioning drive ' + self.install_drive)

        self.uefi = self.supports_uefi()
        if self.uefi: self.logger.info('Detected machine booted with UEFI, using GPT')
        else: self.logger.info('UEFI not supported, creating DOS partition table')

        partition_table = 'msdos' if not self.uefi else 'gpt'
        subprocess.check_call(['parted', '-s', self.install_drive,
                               'mklabel', partition_table])
        if self.uefi:
            subprocess.check_call(['parted', '-s', self.install_drive, '--',
                                   'mkpart', 'ESP', 'fat32', '2048s', '512',
                                   'mkpart', 'Windows', 'NTFS', '512', '-1s',
                                   'set', '1', 'esp', 'on'])

            self.boot_part = self.install_drive + '1'
            self.system_part = self.install_drive + '2'

        else:
            subprocess.check_call(['parted', '-s', self.install_drive, '--',
                                   'mkpart', 'primary', 'NTFS', '2048s', '-1s',
                                   'set', '1', 'boot', 'on'])

            self.system_part = self.install_drive + '1'

    def auto_format(self):
        cluster_size = 4096
        subprocess.check_call(['mkfs.ntfs', '-Q', '-c', str(cluster_size), self.system_part])
        if self.uefi: subprocess.check_call(['mkfs.msdos', '-F32', self.boot_part])

        self.logger.info('Sucessfully partitioned installation drive')

    def mount_partitions():
        self.system_dir = '/mnt/system'
        mount(self.system_part, self.system_dir, mkdir=True)

        if self.uefi:
            self.boot_dir = '/mnt/boot'
            mount(self.boot_part, self.boot_dir, mkdir=True)

        self.logger.info('Mounted partitions successfully')

    def get_source_uri(self):
        code, server = self.d.inputbox('Enter an NFS server', width=40)

        if code != self.d.OK: return
        self.source_uri = server

    def prepare_source(self):
        self.get_source_uri()
        mount(self.source_uri, self.source_dir, mkdir=True)

    def install_os(self):
        self.source, self.imageid, self.os_part = (self.source_dir + '/srv/nfs4/win7_x64_sp1.wim', '2', '/mnt/dst/')
        self.boot_part = '/dev/null'

        self.extract_wim(self.source, self.imageid, self.os_part)
        self.install_bootloader()

    def extract_wim(self, wimfile, imageid, target):
        r, w = os.pipe()
        process = subprocess.Popen(['wimlib-imagex', 'apply', wimfile, imageid, target],
            stdout=w, stderr=w)

        filp = os.fdopen(r)

        self.logger.info('Applying WIM...')

        while True:
            line = filp.readline()
            self.logger.info(line)
            if 'Creating files' in line: break

        for stage in ['Creating files', 'Extracting file data', 'Applying metadata to files']:
            self.logger.info(stage)

            self.d.gauge_start(text=stage, width=80, percent=0)

            while(True):
                line = filp.readline()
                if stage not in line: continue
                pct = re.search(r'\d+%', line).group(0)[:-1]

                if pct:
                    self.d.gauge_update(int(pct))
                    if pct == '100': break

            exit_code = self.d.gauge_stop()

    def install_bootloader(self):
        if not self.uefi:
            self.write_mbr()

    def write_mbr(self):
        subprocess.check_call('ms-sys', '-7', self.install_drive)

    def exit(self):
        self.running = False

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.critical('Unhandled exception', exc_info=(exc_type, exc_value, exc_traceback))

import sys
sys.excepthook = handle_exception

if __name__ == '__main__':
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    fh = logging.FileHandler('/tmp/kiwi-install.log')
    logger.addHandler(fh)

    app = WindowsInstallApp()
