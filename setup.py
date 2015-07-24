from distutils.core import setup, Extension

setup(
    name='telepathy',
    version='0.27.3',
    package_dir={'telepathy': 'src'},
    packages=['telepathy',
              'telepathy.client',
              'telepathy.server',
              'telepathy._generated'],
    install_requires=['six'],
)
