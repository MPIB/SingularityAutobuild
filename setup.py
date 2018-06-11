""" Setup script for the SingularityAutobuild Package."""
from distutils.core import setup

setup(
    name='SingularityAutobuild',
    version='0.1.0',
    author='Dominique Hansen',
    author_email='Dominique.Hansen@hu-berlin.de',
    packages=['singularity_autobuild', 'singularity_autobuild.test'],
    url='http://github.com/MPIB/SingularityAutobuild',
    license='3-clause BSD',
    description=(
        'Automatically build a collection of Singularity recipes and'
        'load the build images into your sregistry.'
    ),
    long_description=open('README.md').read(),
    install_requires=[
        # Needed to work with the repository, that contains the recipes.
        "GitPython==2.1.9",
        # Used to convert gitlabs date strings into date objects.
        "iso8601==0.1.12",
        # Needed to get data from the gitlab api.
        "requests==2.18.4",
        # Needed for python type hints.
        "typing==3.6.4"
    ],
    entry_points={
        'console_scripts': [
            'singularity_autobuild = singularity_autobuild.__main__:main'
        ]
    }
)
