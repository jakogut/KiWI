from distutils.core import setup

setup(
    name = 'KiWI',
    description = 'Killer Windows Installer',
    author = 'Joseph Kogut',
    author_email = 'joseph.kogut@gmail.com',
    url = 'josephkogut.com/yaknet/kiwi.git',
    packages = ['kiwi'],
)

import shutil
import glob
import os

support_dir = '/usr/lib/kiwi/'
loader_dir = support_dir + 'loader/'

try:
    os.makedirs(support_dir, 755)
    shutil.copytree('support/loader', loader_dir)
except FileExistsError: pass

