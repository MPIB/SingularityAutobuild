# -*- coding: utf-8 -*-
""" Go through a directory structure, Build and upload singularity images.

The Functions and classes of this module need to be able to execute
`singularity` and `sregistry` from the terminal and
need to be executed by a user, that has an .sregistry file in the home directory.
The .sregistry file needs to enable the user to have admin and superuser access
to the sregistry-server.
For further information look at the sregistry clients documentation:
`sregistry-cli <https://singularityhub.github.io/sregistry/credentials>`_
"""

import glob
import logging
import os
import re
import subprocess
from subprocess import call
import sys
from typing import Generator

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.DEBUG)

HANDLER = logging.StreamHandler(sys.stdout)
HANDLER.setLevel(logging.DEBUG)
HANDLER.setFormatter(
    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
LOGGER.addHandler(HANDLER)

class Builder(object):
    """Build the actual Singularity image from a recipe.

    :param recipe_path: The full path to the singularity recipe
    :param image_type:  The image type to be produces. identified by used suffix.
    """

    SUBPROCESS_LOGDIR = os.path.abspath('./build_logs')

    def __init__(self, recipe_path: str, image_type: str = 'simg'):
        self.recipe_path = recipe_path
        self.image_type = image_type
        self.build_status = False
        self.build_folder = os.path.dirname(self.recipe_path)
        self.version = re.sub(r'^.*?\.(.+)\.recipe$', r'\1', self.recipe_path)
        self.image_name = os.path.basename(self.recipe_path)
        self.image_name = re.sub(r'(^.*?)\..*$', r'\1', self.image_name)

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

        if not os.path.exists(self.SUBPROCESS_LOGDIR):
            os.makedirs(self.SUBPROCESS_LOGDIR)
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

    def image_info(self) -> dict:
        """ Collects data about the image.

        :returns: Information about the build image:
                  Full Path to it, name of its parent folder
                  as collection name, version of the image and
                  name of the container at the destination.
        """

        _image_info = {}
        _image_info['image_full_path'] = "%s/%s.%s" % (
            self.build_folder,
            self.image_name,
            self.image_type)
        _image_info['collection_name'] = os.path.basename(self.build_folder)
        _image_info['image_version'] = self.version
        _image_info['container_name'] = self.image_name
        return _image_info

def recipe_finder(path: str = './') -> Generator:
    """ Find recipe files given a root search directory.

    :param path: Path of the search root.
                 The path will be made into an
                 absolute path if it is relative.
    :returns:    The absolute paths to
                 found recipes.
    """
    _search_root = os.path.abspath(path)
    if not os.path.isdir(_search_root):
        raise OSError("%s is no directory" % _search_root)

    for recipe in glob.glob('%s/**/*.recipe' % _search_root, recursive=True):
        yield os.path.abspath(recipe)

def image_pusher(
        image_path: str,
        collection: str,
        version: str,
        image: str,
        retry_threshold: int = 20) -> bool:
    """ Upload image to an sregistry.

    Calls `sregistry push` with `subprocess.Popen` to upload an existing image to an sregistry.


    :param image_path:       Path to the image file
    :param collection:       Name of the collection to upload to.
    :param version:          Version of the image.
    :param image:            Name of the image to be used by the sregistry.
    :param retry_threshold:  How often should the upload retried if it fails.
    :returns:           The success status of the upload.
    """

    # Ensure expected behavior of sregistry-cli
    os.environ["SREGISTRY_CLIENT"] = 'registry'

    for retry in range(retry_threshold):
        _process = subprocess.Popen(
            [
                'sregistry', 'push',
                "--name", "%s/%s" % (collection, image),
                "--tag", version,
                image_path
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
            )
        _process_return = _process.communicate()
        if 'Return status 201 Created' in str(_process_return[0]):
            LOGGER.info(
                """
                Upload successfull for:
                collection: %s
                image:      %s
                version:    %s
                """,
                image,
                collection,
                version
            )
            break
        elif retry == retry_threshold - 1:
            LOGGER.debug(
                """
                Upload failed for:
                collection: %s
                image:      %s
                version:    %s
                """,
                image,
                collection,
                version
            )
            return False
        else:
            LOGGER.debug('Upload failed. Retrying')
    return True