from setuptools import setup

setup(name='sbh_explorer',
      version='0.1',
      description='Tools for exploring data stored in SynBioHub',
      url='https://github.com/SD2E/sbh-explorer',
      license='MIT',
      packages=['sbh_explorer'],
      install_requires=[
          'pandas',
          'synbiohub_adapter@git+https://github.com/SD2E/synbiohub_adapter'
      ])
