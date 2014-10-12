from distutils.core import setup, Extension

setup(
    name='telepathy',
    version='0.27.3',
    package_dir={'telepathy': 'src'},
    packages=['telepathy', 'telepathy._generated'],
)