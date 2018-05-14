# -*- coding: utf-8 -*-
""" Main Module to make the builder directly executable.

"""

import os
import sys
import logging
import argparse
from singularity_builder.singularity_builder import (
    Builder,
    recipe_finder,
    image_pusher
)
from singularity_builder.gitlab_tools import (
    GitLabPushEventInfo,
    call_gitlab_events_api
)

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.DEBUG)

HANDLER = logging.StreamHandler(sys.stdout)
HANDLER.setLevel(logging.DEBUG)
HANDLER.setFormatter(
    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
LOGGER.addHandler(HANDLER)

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
        image_type: str = 'simg',
        test_run: bool = False
    ):
    """ Function to tie the functionality of this module together.

    :param search_folder: The base folder for :py:func:`.recipe_finder` to search through.
    :param image_type:    The image type to be passed to :class:`.Builder` constructor
                          and to be created by :meth:`.Builder.build`.
    """

    try:
        _api_url = os.environ['GITLAB_API_STRING']
        _api_key = os.environ['GITLAB_API_TOKEN']
    except KeyError:
        raise EnvironmentError("GitLab API environment variables are not set.")
    _gitlab_response = call_gitlab_events_api(
        api_url=_api_url,
        api_key=_api_key
        )
    _file_checker = GitLabPushEventInfo(
        git_lab_response=_gitlab_response,
        local_repo=os.path.abspath('./')
        )

    LOGGER.debug('Building all %s in %s', image_type, search_folder)
    for recipe_path in recipe_finder(path=search_folder):
        _builder = Builder(recipe_path=recipe_path, image_type=image_type)
        _image_info = _builder.image_info()
        # Was the recipe file modified since last push?
        if not test_run:
            if not _file_checker.is_modified_file(recipe_path):
                LOGGER.debug(
                    """
                    Skipping Recipe not modified since last push:
                    collection: %s
                    image:      %s
                    version:    %s""",
                    _image_info['collection_name'],
                    _image_info['container_name'],
                    _image_info['image_version']
                    )
                continue
        _builder = Builder(recipe_path=recipe_path, image_type=image_type)
        _image_info = _builder.image_info()
        LOGGER.debug(
            """
            Building:
            collection: %s
            image:      %s
            version:    %s""",
            _image_info['collection_name'],
            _image_info['container_name'],
            _image_info['image_version']
            )
        _image_info = _builder.build()
        _pushed = image_pusher(
            image_path=_image_info['image_full_path'],
            collection=_image_info['collection_name'],
            version=_image_info['image_version'],
            image=_image_info['container_name']
            )
        if _pushed:
            LOGGER.debug('Build and push was successful.')

        os.remove(_image_info['image_full_path'])

if __name__ == "__main__":
    ARGUMENTS = arg_parser()
    main(search_folder=ARGUMENTS.path, image_type=ARGUMENTS.image_type)
