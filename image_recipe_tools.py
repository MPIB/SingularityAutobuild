""" Module for miscellaneous modules to work with sregistry. """

import os
import glob
import re
import subprocess
from subprocess import call
from typing import Generator
from singularity_builder import stdout_logger

LOGGER = stdout_logger.LOGGER

def image_in_sregistry(
        collection: str,
        version: str,
        image: str
    ) -> bool:
    """ Returns true if image of version exists in collection.

    Calls sregistry search and parses its output to
    determin if a specific container is already stored
    in the sregistry.
    :param collection: The name of the images/containers collection.
    :param version:    The version of the container.
    :param image:      The name of the container.
    """

    _exit_status = call([
        'sregistry',
        'search',
        "%s/%s:%s" % (collection, image, version)
    ])

    return bool(_exit_status == 0)

def recipe_finder(path: str = './') -> Generator:
    """ Find recipe files given a root search directory.

    Recipes need to have the suffix .recipe

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
                             Note: Sregistry showed problems with accepting
                             post requests. This parameter might become obsolete
                             when this is no longer an issue.
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

def get_collection_from_recipe_path(recipe_file_full_path: str) -> str:
    """ Returns the collection of the image to be produced by a recipe file . """
    return os.path.basename(os.path.dirname(recipe_file_full_path))

def get_version_from_recipe(recipe_file_name: str) -> str:
    """ Returns the image version contained in a recipe file name. """
    # Can we find a version part between . characters in the filename?
    if re.findall(r'\..+?\.', recipe_file_name):
        # Match everything from the first literal . to the last . as Version.
        return re.sub(r'^.*?\.(.+)\.recipe$', r'\1', recipe_file_name)
    # No version in the Filename, use 'latest' as version.
    return 'latest'

def get_image_name_from_recipe(recipe_file_name: str) -> str:
    """ Returns the image name contained in a recipe file name. """
    return re.sub(r'(^.*?)\..*$', r'\1', recipe_file_name)
