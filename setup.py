from setuptools import setup

setup(
    name = 'KiWI',
    description = 'Killer Windows Installer - An alternative to WDS',
    license = 'MIT',
    version = '1',
    author = 'Joseph Kogut',
    author_email = 'joseph.kogut@gmail.com',
    url = 'http://github.com/jakogut/kiwi.git',
    packages = ['kiwi'],
    install_requires = [
        'pythondialog >= 3.3.0'
    ]
)
