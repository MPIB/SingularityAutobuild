""" Setup script for the SingularityAutobuild Package."""
from setuptools import setup

setup(
    name='SingularityAutobuild',
    version='0.1.0',
    author='Dominique Hansen',
    author_email='Dominique.Hansen@hu-berlin.de',
    packages=['singularity_autobuild', 'singularity_autobuild.test'],
    package_data={
        "singularity_autobuild.test": [
            'test.cfg',
            'test_recipes/*.recipe'
            ]
    },
    entry_points={
        'console_scripts': [
            'singularity_autobuild = singularity_autobuild.__main__:entrypoint_run'
        ]
    },
    url='http://github.com/MPIB/SingularityAutobuild',
    license='3-clause BSD',
    description=(
        'Automatically build a collection of Singularity recipes and'
        'load the build images into your sregistry.'
    ),
    long_description=open('README.rst').read(),
    install_requires=[
        # Needed to work with the repository, that contains the recipes.
        "GitPython==3.1.34",
        # Used to convert gitlabs date strings into date objects.
        "iso8601==0.1.12",
        # Needed to get data from the gitlab api.
        "requests~=2.20",
        # Needed for python type hints.
        "typing==3.6.4"
    ]
)
