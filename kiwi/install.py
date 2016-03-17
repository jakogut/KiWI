import locale
from dialog import Dialog

locale.setlocale(locale.LC_ALL, '')

import sys, os
import glob
import re
import subprocess
from time import sleep
import shutil

import logging
import logging.handlers

from .interface import *
from .mount import *
from .wimlib import wiminfo

logger = logging.getLogger()

class WindowsInstallApp(object):
    def __init__(self):
        self.logger = logging.getLogger(__name__)

        self.uefi = False

        self.boot_part = ''
        self.system_part = ''

        self.boot_dir = '/mnt/boot'
        self.system_dir = '/mnt/system'

        self.mbr_disk_signature = '4D34B30F'
        self.gpt_disk_signature = '572BD0E9-D39E-422C-82E6-F37157C3535D'
        self.boot_partuuid = '8d03c7bb-6b0c-4223-aaa1-f20bf521cd6e'
        self.system_partuuid = '57092450-f142-4749-b540-f2ec0a183b7b'

        self.cluster_size = 4096
        self.fs_compression = False
        self.quick_format = True

        self.d = Dialog(dialog='dialog')
        self.d.set_background_title('KiWI: Killer Windows Installer')

        self.source_dir = '/mnt/source/'

        advanced_items = [
            ('Filesystem options', MenuItem(self.fs_options)),
        ]

        advanced_submenu = Menu(self.d, advanced_items, title='Advanced Options')

        main_menu_items = [
            ('Configure Networking', MenuItem(self.configure_network)),
            ('Prepare Storage Device', MenuItem(self.auto_prepare)),
            ('Select Installation Source', MenuItem(self.prepare_source)),
            ('Install OS', MenuItem(self.install_os)),
            #('Install Bootloader', self.install_bootloader),
            ('Reboot', MenuItem(self.reboot)),
            ('---', MenuItem(separator=True)),
            ('Advanced Options', advanced_submenu),
        ]

        self.running = True
        self.main_menu = StatefulMenu(self.d, main_menu_items, title='Main Menu')
        while self.running: self.main_menu.run(ret=self.exit())

    def sync(self):
        self.d.infobox('Syncing buffered data\n\nDo NOT reboot!', width=30)
        subprocess.check_call(['sync'])

    def reboot(self):
        self.sync()
        subprocess.check_call(['reboot'])

    def fs_options(self):
        choices = [
            ('Quick Format',        '',             'quick_format'),
            ('NTFS Compression',    '',             'fs_compression'),
            ('Force GPT/EFI',       '',             'uefi'),
        ]

        code, selected = self.d.checklist('Filesystem Options', choices=[
            (choice[0], choice[1], getattr(self, choice[2])) for choice in choices])

        if code != self.d.OK: return

        for item in choices:
            tag = item[0]
            var_name = item[2]

            if tag in selected: setattr(self, var_name, True)
            else: setattr(self, var_name, False)

    def test_network(self):
        return True if subprocess.call(
            ['ping', '-c 2', '-i 0.2', '8.8.8.8'],
            stdout=subprocess.PIPE) == 0 else False

    def configure_network(self):
        if not self.test_network():
            rc = subprocess.call('nmtui', shell=True)
        else:
            self.d.msgbox('Network Configuration Successful', width=40, title='Network Status')
            self.main_menu.advance()

    def detect_blockdevs(self):
        devices = []
        p = subprocess.run(['lsblk', '-Ppd'], stdout=subprocess.PIPE)
        for line in p.stdout.decode('UTF-8').split('\n'):
            dev = {}
            for p in line.split():
                pair = p.split('=')
                dev[pair[0]] = pair[1][1:-1]

            # We don't need read-only devices
            if 'RO' not in dev or dev['RO'] == '1': continue
            devices.append(dev)

        self.d.msgbox('Detected Devices:\n\n' + '\n'.join(
            [' '.join([dev['NAME'], dev['SIZE']]) for dev in devices]))

        self.devices = devices

    def select_disk(self):
        self.detect_blockdevs()

        entries = [tuple([device['NAME'], '-']) for device in self.devices] + [('OTHER', '+')]
        code, tag = self.d.menu('Choose an installation drive', choices=entries)
        if code != self.d.OK: return

        if tag == 'OTHER':
            code, tag = self.d.inputbox('Enter a path to a block device')
            if code != self.d.OK: return

            import stat
            mode = os.stat(tag).st_mode
            if not stat.S_ISBLK(mode):
                self.d.infobox('File is not a block device.')
                sleep(3)
                return

        code, confirmation = self.d.inputbox('This will erase ALL data on %s' % tag + \
            '\n\nType \'YES\' to continue', width=40, height=15)
        if code != self.d.OK or confirmation != 'YES': return

        self.install_drive = tag
        self.logger.info('Block device {} selected for installation'.format(self.install_drive))
        return self.d.OK

    def supports_uefi(self):
        p = subprocess.Popen(['efivar', '-l'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        uefi = True if p.returncode == 0 else False
        return uefi

    def auto_prepare(self):
        self.select_disk()

        if not hasattr(self, 'install_drive'):
            return

        for dir in [self.system_dir, self.boot_dir]:
            if mountpoint(dir): unmount(dir)

        partitions = glob.glob(self.install_drive + '*')
        for part in partitions:
            logger.debug('Unmounting partition {}'.format(part))
            try: unmount(part)
            except subprocess.CalledProcessError: pass

        if self.auto_partition() != self.d.OK: return
        if self.auto_format() != self.d.OK: return

        self.main_menu.advance()

    def auto_partition(self):

        if self.uefi is False:
            self.uefi = self.supports_uefi()
        else: uefi_forced = True

        if self.uefi and not uefi_forced: self.logger.info('Detected machine booted with UEFI, using GPT')
        elif self.uefi and uefi_forced: self.logger.info('UEFI install forced, using GPT')
        else: self.logger.info('UEFI not supported, creating DOS partition table')

        partition_table = 'msdos' if not self.uefi else 'gpt'
        subprocess.check_call(['parted', '-s', self.install_drive,
                               'mklabel', partition_table])
        if self.uefi:
            subprocess.check_call(['parted', '--align', 'optimal',
                                   '-s', self.install_drive, '--',
                                   'mkpart', 'ESP', 'fat32', '0%s', '512',
                                   'mkpart', 'Windows', 'NTFS', '512', '100%',
                                   'set', '1', 'esp', 'on'])

            self.boot_part = self.install_drive + '1'
            self.system_part = self.install_drive + '2'

        else:
            subprocess.check_call(['parted', '-s', self.install_drive, '--',
                                   'mkpart', 'primary', 'NTFS', '2048s', '-1s',
                                   'set', '1', 'boot', 'on'])

            self.system_part = self.install_drive + '1'

        return self.d.OK

    def auto_format(self):
        call = ['mkfs.ntfs']

        call.append('-c')
        call.append(str(self.cluster_size))

        if self.fs_compression: call.append('-C')
        if self.quick_format: call.append('-Q')
        call.append(self.system_part)

        subprocess.check_call(call, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if self.uefi: subprocess.check_call(['mkfs.msdos', '-F32', self.boot_part],
            stdout = subprocess.PIPE, stderr=subprocess.PIPE)

        self.d.infobox('Formatting drive...')

        self.logger.info('Sucessfully partitioned installation drive')
        return self.d.OK

    def prepare_source(self):
        source_items = [
            ('Network Filesystem (NFS)', MenuItem(self.prepare_nfs_source)),
            #('Network Block Device (NBD)', MenuItem()),
            ('SCP/SFTP (SSH)', MenuItem(self.prepare_sshfs_source)),
            ('Block Device (USB, CD/DVD, etc.)', self.prepare_blk_source),
            ('---', MenuItem(separator=True)),
            ('OTHER (Path)', MenuItem(self.prepare_fs_source)),
        ]

        Menu(self.d, source_items, 'Select Installation Source', ret=None).run()

    def prepare_fs_source(self):
        code, path = self.d.inputbox('Enter a UNIX path', width=40)
        if code != self.d.OK: return
        mount(path, self.source_dir, mkdir=True, bind=True)
        self.select_source()

    def prepare_sshfs_source(self):
        code, path = self.d.inputbox('Enter an SSHFS path, in the format user@server:/', width=40)
        if code != self.d.OK: return
        code, passwd = self.d.passwordbox('Enter the password', width=40)
        if code != self.d.OK: return

        subprocess.check_call(['mkdir', '-p', self.source_dir])
        call = ['sshfs', path, self.source_dir, '-o', 'password_stdin']
        p = subprocess.Popen(call, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        p.communicate(input=passwd.encode('UTF-8'))
        self.select_source()

    def prepare_blk_source(self):
        code, path = self.d.inputbox('Enter a block device path', width=40)
        if code != self.d.OK: return
        mount(path, self.source_dir, mkdir=True)
        self.select_source()

    def prepare_nfs_source(self):
        code, path = self.d.inputbox('Enter an NFS server or share', width=40)
        if code != self.d.OK: return
        mount(path, self.source_dir, mkdir=True)
        self.select_source()

    def select_source(self):
        discovered_wims = glob.glob(self.source_dir + '**/*.wim', recursive=True)

        entries = [tuple([wim, '-']) for wim in discovered_wims]
        code, tag = self.d.menu('Choose a WIM', choices=entries)
        if code == self.d.OK: self.image_path = tag
        else: return

        entries = [
            tuple([
                image['Index'],
                # Not every WIM has 'Display Name' defined
                image.get('Display Name') or image.get('Description') + ' ' +
                image.get('Architecture')
            ]) for image in wiminfo(self.image_path)]

        code, tag = self.d.menu('Choose an image', choices=entries)
        if code == self.d.OK: self.image_index = tag
        else: return

        self.main_menu.advance()

    def install_os(self):
        self.extract_wim(self.image_path, self.image_index, self.system_part)
        self.sync()

        self.install_bootloader()
        self.main_menu.advance()

    def extract_wim(self, wimfile, imageid, target):
        r, w = os.pipe()
        process = subprocess.Popen(['wimlib-imagex', 'apply', wimfile, imageid, target],
            stdout=w, stderr=w)

        filp = os.fdopen(r)

        self.logger.info('Applying WIM...')

        while True:
            line = filp.readline()
            self.logger.debug('Discarding line from WIM STDOUT: {}'.format(line))
            if 'Creating files' in line: break

        for stage in ['Creating files', 'Extracting file data']:
            self.d.gauge_start(text=stage, width=80, percent=0)

            while(True):
                line = filp.readline()
                self.logger.debug('Wim extraction STDOUT: {}'.format(line))
                if stage not in line: continue
                pct = re.search(r'\d+%', line).group(0)[:-1]

                if pct:
                    self.d.gauge_update(int(pct))
                    if pct == '100': break

            exit_code = self.d.gauge_stop()

    def ntfs_hide(self, path):
        subprocess.check_call(['setfattr', '-h', '-v', '0x02000000',
            '-n', 'system.ntfs_attrib', path])

    def install_bootloader(self):
        from . import BCD
        mount(self.system_part, self.system_dir, mkdir=True)

        if not self.uefi:
            self.write_mbr()

            shutil.copytree(
                os.path.join(self.system_dir, 'Windows/Boot/PCAT'),
                os.path.join(self.system_dir, 'Boot'))

            shutil.copy2(
                os.path.join(self.system_dir, 'Boot/bootmgr'), self.system_dir)

            for file in ['Boot', 'bootmgr']:
                self.ntfs_hide(os.path.join(self.system_dir, file))

            BCD.write_bcd(BCD.bios_bcd, os.path.join(self.system_dir, 'Boot/BCD'))
        else:
            mount(self.boot_part, self.boot_dir, mkdir=True)
            subprocess.check_call(['sgdisk', self.install_drive,
                '-U', self.gpt_disk_signature,
                '-u 1:' + self.boot_partuuid,
                '-u 2:' + self.system_partuuid])

            for dir in ['Boot', 'Microsoft']:
                os.makedirs(os.path.join(self.boot_dir, 'EFI/' + dir))

            shutil.copytree(
                os.path.join(self.system_dir, 'Windows/Boot/EFI'),
                os.path.join(self.boot_dir, 'EFI/Microsoft/Boot'))

            shutil.copyfile(
                os.path.join(self.boot_dir, 'EFI/Microsoft/Boot/bootmgfw.efi'),
                os.path.join(self.boot_dir, 'EFI/Boot/bootx64.efi'))

            BCD.write_bcd(BCD.uefi_bcd,
                os.path.join(self.boot_dir, 'EFI/Microsoft/Boot/BCD'))

    def write_mbr(self):
        subprocess.check_call(['ms-sys', '-S', self.mbr_disk_signature, '-7', self.install_drive],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        self.logger.info('MBR written to {}'.format(self.install_drive))

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
