# -*- coding: utf-8 -*-
""" Main Module to make the builder directly executable through cli.


This __main__ module contains function arg_parser(),
parsing command line options and
function main(), controlling the applications flow.

Command line Options are:


 --path         Full path to the base folder, containing all recipe files
                to be build.
 --image_type   Image type, in the form of types suffix,
                of the images to be build.

scrolls
"""

import os
import argparse
from singularity_autobuild.singularity_builder import Builder
from singularity_autobuild.image_recipe_tools import (
    recipe_finder,
    image_pusher,
    image_in_sregistry,
    dependency_resolver
)
from singularity_autobuild.gitlab_tools import (
    GitLabPushEventInfo,
    call_gitlab_events_api
)

from singularity_autobuild.stdout_logger import LOGGER

def arg_parser() -> argparse.Namespace:
    """ Reads command line arguments.

    :returns: Values of accepted command line arguments.
    """
    _parser = argparse.ArgumentParser(
        description="""Find all recipes, build them and push all their images to an sregistry.
        Recipes are identified by the suffix ".recipe".
        The image name will be taken from the recipe name using everything from the first character till the first "." occurrence.
        The version will be taken from the recipe name using everything from the first "." till the suffix ".recipe".
        The collection name will be taken from the recipes parent folder.
        """
    )
    _parser.add_argument('--path', type=str, help="Base path to search recipes.", required=True)
    _parser.add_argument('--image_type', type=str, help="The type of image to be build")
    return _parser.parse_args()

def main(
        search_folder: str = './',
        image_type: str = 'simg'
    ):
    """ Function to tie the functionality of this module together.

    :param search_folder: The base folder for :py:func:`image_recipe_tools.recipe_finder`
                          to search through.
    :param image_type:    The image type to be passed to :class:`singularity_builder.Builder`
                          constructor and to be created by
                          :meth:`singularity_builder.Builder.build`.
    """

    # Setup for Building
    try:
        _api_url = os.environ['GITLAB_API_STRING']
        _api_key = os.environ['GITLAB_API_TOKEN']
        _git_folder = os.environ['CI_PROJECT_DIR']
    except KeyError:
        raise EnvironmentError("GitLab API environment variables are not set.")
    # Call the event API of the GitLab instance used.
    _gitlab_response = call_gitlab_events_api(
        api_url=_api_url,
        api_key=_api_key
        )

    _file_checker = GitLabPushEventInfo(
        git_lab_response=_gitlab_response,
        local_repo=os.path.abspath(_git_folder)
        )

    _recipe_list = [recipe for recipe in recipe_finder(path=search_folder)]

    # Start Building
    LOGGER.debug('Building all %s in %s', image_type, search_folder)
    for recipe_path in dependency_resolver(
            recipe_file_paths=_recipe_list,
            recipe_base_path=search_folder
        ):
        _builder = Builder(recipe_path=recipe_path, image_type=image_type)
        _image_info = _builder.image_info()
        # Does the image already exist in the sregistry?
        if image_in_sregistry(
                collection=_image_info['collection_name'],
                version=_image_info['image_version'],
                image=_image_info['container_name']
        ):
            LOGGER.info(
                """
                Image already in SRegistry:
                collection: %s
                image:      %s
                version:    %s
                checking if its' recipe has changed.""",
                _image_info['collection_name'],
                _image_info['container_name'],
                _image_info['image_version']
                )
            # Was the recipe file modified since last push?
            # This conditional together with the last one
            # is used to skip recipes, whose corresponding
            # image was already build and pushed once.
            # Images whose recipes where changed since
            # the last pushed are however build and reuploaded.
            if not _file_checker.is_modified_file(recipe_path):
                LOGGER.info(
                    """
                    Skipping Recipe not modified since last push:
                    collection: %s
                    image:      %s
                    version:    %s""",
                    _image_info['collection_name'],
                    _image_info['container_name'],
                    _image_info['image_version']
                    )
                # Skip build and upload.
                continue
        _builder = Builder(recipe_path=recipe_path, image_type=image_type)
        _image_info = _builder.image_info()
        LOGGER.info(
            """
            Building:
            collection: %s
            image:      %s
            version:    %s""",
            _image_info['collection_name'],
            _image_info['container_name'],
            _image_info['image_version']
            )
        # Actual building process.
        try:
            _image_info = _builder.build()
        except OSError:
            LOGGER.debug(
                "File %s could not be build by Singularity.",
                recipe_path
                )
        # Load into sregistry if the recipe build into an image.
        if _builder.is_build():
            _pushed = image_pusher(
                image_path=_image_info['image_full_path'],
                collection=_image_info['collection_name'],
                version=_image_info['image_version'],
                image=_image_info['container_name']
                )
            os.remove(_image_info['image_full_path'])
            if _pushed:
                LOGGER.debug('Build and push was successful.')


# Still testing for __name__ == __main__
# to cleanly import this module during unit testing.
if __name__ == "__main__":
    ARGUMENTS = arg_parser()
    main(search_folder=ARGUMENTS.path, image_type=ARGUMENTS.image_type)
