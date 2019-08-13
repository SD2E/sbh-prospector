from setuptools import setup

setup(name='sbh_prospector',
      version='0.1',
      description='Tools for exploring data stored in SynBioHub',
      url='https://github.com/SD2E/sbh-prospector',
      license='MIT',
      packages=['sbh_prospector'],
      install_requires=[
          'pandas',
          'synbiohub_adapter@git+https://github.com/SD2E/synbiohub_adapter'
      ])
