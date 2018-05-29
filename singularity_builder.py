# -*- coding: utf-8 -*-
""" Go through a directory structure, Build and upload singularity images.

The Functions and classes of this module need to be able to execute
`singularity` and `sregistry` from the terminal and
need to be executed by a user, that has an .sregistry file in the home directory.
The .sregistry file needs to enable the user to have admin and superuser access
to the sregistry-server.
For further information look at the sregistry clients documentation:
`sregistry-cli <https://singularityhub.github.io/sregistry/credentials>`_

Regular logging in this module is done to stdout,
to be directly visible in a GitLab CI/CD jobs log.
Singularity build output is piped into a file in a
separate folder, created relative to this script.
The Folder is intended to be defined as a pipeline
artifact in GitLab CI/CD.

"""

import logging
import os
from subprocess import call
import sys

from singularity_builder.image_recipe_tools import (
    get_version_from_recipe,
    get_image_name_from_recipe,
    get_collection_from_recipe_path
    )

# Set up the stdout logger.
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.DEBUG)

HANDLER = logging.StreamHandler(sys.stdout)
HANDLER.setLevel(logging.DEBUG)
HANDLER.setFormatter(
    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
LOGGER.addHandler(HANDLER)

class Builder(object):
    """ Facilitate the building of a Singularity image from a recipe.

    Images are not build automatically to first gather and
    serve information about the image to be build.
    Implementations using singularity_builder.Builder
    can therefore check if the image building would be
    redundant and skip it if needed.

    Building is done via the Builder.build() method.

    :param recipe_path: The full path to the singularity recipe
    :param image_type:  The image type to be produces. identified by used suffix.
    """

    # Directory to create files, to pipe singularity build logs into.
    SUBPROCESS_LOGDIR = '%s/%s' % (
        os.path.dirname(os.path.abspath(__file__)),
        'build_logs'
        )

    def __init__(self, recipe_path: str, image_type: str = 'simg'):
        self.recipe_path = recipe_path
        self.image_type = image_type
        self.build_status = False
        self.build_folder = os.path.dirname(self.recipe_path)
        _filename = os.path.basename(self.recipe_path)
        self.version = get_version_from_recipe()
        # Match everything till the first literal . as the image_name.
        self.image_name = get_image_name_from_recipe()
        """
        Make sure that the subprocess logdir exists.
        GitLab ci will want the directory to be there,
        if it was defined as artifact in the pipeline defintion,
        even if nothing was build.
        """
        if not os.path.exists(self.SUBPROCESS_LOGDIR):
            os.makedirs(self.SUBPROCESS_LOGDIR)

    def build(self) -> dict:
        """ Calls singularity to build the image.

        :returns: Information about the build image:
                  Full Path to it, name of its parent folder
                  as collection name, version of the image and
                  name of the container at the destination:

                  .. code-block:: python

                        {
                            'image_full_path': '/path/to/image.simg',
                            'collection_name': 'image_parent_folder',
                            'image_version':   '1.0',
                            'container_name':  'image_name'
                        }

        :raises OSError: When Singularity could not be found/executed.
        :raises AttributeError: When Singularity failed with its given parameters.
        """
        _image_info = self.image_info()

        if self.is_build():
            return _image_info

        _subprocess_logpath = "%s/%s.%s.%s.log" % (
            self.SUBPROCESS_LOGDIR,
            _image_info['collection_name'],
            _image_info['container_name'],
            _image_info['image_version']
            )

        try:
            with open(
                _subprocess_logpath,
                'w'
                ) as _subprocess_logfile:
                call(
                    [
                        "singularity",
                        "build",
                        _image_info['image_full_path'],
                        self.recipe_path
                    ],
                    stdout=_subprocess_logfile,
                    stderr=_subprocess_logfile,
                    shell=False)
            self.build_status = True
        except OSError as error:
            raise OSError("singularity build failed with %s." % error)

        return _image_info

    def is_build(self) -> bool:
        """ Checks, updates and returns current build status of the image.

        :returns: Build status of the image.
        """
        if self.build_status:
            _info = self.image_info()
            self.build_status = os.path.isfile(
                _info['image_full_path']
            )
        return self.build_status

    def image_info(self) -> dict(
            image_full_path='/FULLPATH/TO/image_name.image_type',
            collection_name='image_parent_folder',
            image_version='image_version',
            container_name='image_name'):
        """ Collects data about the image.

        The container_name key returned through the dict is
        the same as the image name. It is intended to be used to
        set the container name in the sregistry.

        :returns: Information about the build image:
                  Full Path to it, name of its parent folder
                  as collection name, version of the image and
                  name of the container at the destination.

                  .. code-block:: python

                        {
                            'image_full_path': '/FULLPATH/TO/image_name.image_type',
                            'collection_name': 'image_parent_folder',
                            'image_version':   'image_version',
                            'container_name':  'image_name'
                        }
        """

        _image_info = {}
        _image_info['image_full_path'] = "%s/%s.%s" % (
            self.build_folder,
            self.image_name,
            self.image_type
        )
        _image_info['collection_name'] = get_collection_from_recipe_path(
            _image_info['image_full_path']
        )
        _image_info['image_version'] = self.version
        _image_info['container_name'] = self.image_name
        return _image_info
