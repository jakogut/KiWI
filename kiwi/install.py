import locale
from dialog import Dialog

locale.setlocale(locale.LC_ALL, '')

import sys, os
import glob
import re
import subprocess

import logging
import logging.handlers
logger = logging.getLogger()

def detect_blockdevs():

    return devices

class Menu(object):
    def __init__(self, dialog, items, title, caller = None):
        self.d = dialog
        self.caller = caller

        self.entries = []
        self.dispatch_table = {}
        tag = 1

        self.title = title

        for entry, func in items:
            self.entries.append(tuple([str(tag), entry]))
            self.dispatch_table[str(tag)] = func
            tag += 1

    def run(self, ret=None):
        code, tag = self.d.menu(self.title, choices=self.entries)
        if code == self.d.OK: self.dispatch(tag)
        if ret: ret()

    def dispatch(self, tag):
        if tag in self.dispatch_table:
            func = self.dispatch_table[tag]
            if isinstance(func, Menu):
                func.run(ret=self.run)
            else: func()

class WindowsInstallApp(object):
    def __init__(self):
        self.d = Dialog(dialog='dialog')
        self.d.set_background_title('KiWI: Killer Windows Installer')

        networking_items = [
            ('Connect to Wireless Network', self.launch_wicd)]

        networking_submenu = Menu(self.d, networking_items, 'Network Configuration')

        partitioning_items = [
            ('Auto-Prepare (erases the ENTIRE storage drive)', self.auto_partition),
        ]

        partitioning_submenu = Menu(self.d, partitioning_items, title='Partition Drives')

        main_menu_items = [
            ('Configure Networking', networking_submenu),
            ('Prepare Storage Device', partitioning_submenu),
            ('Select Installation Source', self.select_sources),
            ('Install OS', self.install_os),
            #('Install Bootloader', self.install_bootloader),
        ]

        self.running = True
        main_menu = Menu(self.d, main_menu_items, title='Main Menu')
        while self.running: main_menu.run(ret=self.exit())

    def launch_wicd(self):
        subprocess.call('wicd-curses', shell=True)

    def detect_blockdevs(self):
        def blockdev_size(device):
            nr_sectors = open(device+'/size').read().rstrip('\n')
            sect_size = open(device+'/queue/hw_sector_size').read().rstrip('\n')

            return (float(nr_sectors)*float(sect_size))/(1024.0*1024.0*1024.0)

        dev_pattern = ['sd.*', 'mmcblk*']

        devices = []
        for device in glob.glob('/sys/block/*'):
            for pattern in dev_pattern:
                if re.compile(pattern).match(os.path.basename(device)):
                    devices.append(tuple([device, blockdev_size(device)]))

        self.d.msgbox('Detected Devices:\n\n' + '\n'.join(
            [' '.join([path, '%.2f GB' % size]) for path, size in devices]),
            width=40, height=10)

        self.devices = devices

    def auto_partition(self):
        self.detect_blockdevs()

        entries = [tuple([path, '-']) for path, _ in self.devices]
        code, tag = self.d.menu('Choose an installation drive', choices=entries)

        if code == self.d.OK: self.drive = tag

        logging.info('Beginning installation on drive {}'.format(self.drive))

    def format_partitions(self):
        if not self.drive:
            logging.error('Cannot format with unpartitioned drive')
            return

        p = subprocess.call('mkfs.ntfs -F {}' + self.drive)

    def select_sources(self):
        pass

    def install_os(self):
        pass

    def extract_wim(wimfile, imageid, target):
        p = subprocess.call('wimlib-imagex {} {} {}', wimfile, imageid, target)

    def install_bootloader(self):
        pass

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
    logger.setLevel(logging.INFO)

    fh = logging.FileHandler('install.log')
    logger.addHandler(fh)

    app = WindowsInstallApp()
