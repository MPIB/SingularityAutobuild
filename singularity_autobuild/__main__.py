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

"""

import argparse
import os
from textwrap import dedent

from singularity_autobuild.autobuild_logger import get_stdout_logger
from singularity_autobuild.gitlab_tools import (GitLabPushEventInfo,
                                                call_gitlab_events_api)
from singularity_autobuild.image_recipe_tools import (dependency_resolver,
                                                      image_in_sregistry,
                                                      image_pusher,
                                                      recipe_finder)
from singularity_autobuild.singularity_builder import Builder

LOGGER = get_stdout_logger(name='main', level='INFO')

def arg_parser() -> argparse.Namespace:
    """ Reads command line arguments.

    :returns: Values of accepted command line arguments.
    """
    _parser = argparse.ArgumentParser(
        description=dedent(
            """Find all recipes in a directory,
            build them and push all their images to an sregistry.
            Recipes are identified by the suffix ".recipe".
            The image name will be taken from the recipe name
            using everything from the first character till the first "." occurrence.
            The version will be taken from the recipe name
            using everything from the first "." till the suffix ".recipe".
            The collection name will be taken from the recipes parent folder.
            """
            )
    )
    _parser.add_argument(
        '--path',
        '-p',
        type=str,
        help="Base path to search recipes.",
        required=True
    )
    _parser.add_argument(
        '--image_type',
        '-i',
        type=str,
        help="The type of image to be build."
    )
    _parser.add_argument(
        '--build_log_dir',
        '-b',
        type=str,
        help="The directory, that should contain the build logs. Will be created if not existent."
    )
    return _parser.parse_args()

def main(
        search_folder: str,
        image_type: str = 'simg',
        build_log_dir: str = None
    ):
    """ Function to tie the functionality of this module together.

    :param search_folder: The base folder for :py:func:`image_recipe_tools.recipe_finder`
                          to search through.
    :param image_type:    The image type to be passed to :class:`singularity_builder.Builder`
                          constructor and to be created by
                          :meth:`singularity_builder.Builder.build`.
    """

    # Set up via GitLab environment variables
    # These set through GitLab CI pipeline secret variables.
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
        _builder = Builder(
            recipe_path=recipe_path,
            image_type=image_type,
            log_path=build_log_dir
        )
        _image_info = _builder.image_info()
        # Does the image already exist in the sregistry?
        if image_in_sregistry(
                collection=_image_info['collection_name'],
                version=_image_info['image_version'],
                image=_image_info['container_name']
        ):
            _log_remote_image_exists(_image_info)

            # Was the recipe file modified since last push?
            # This conditional together with the last one
            # is used to skip recipes, whose corresponding
            # image was already build and pushed once.
            # Images whose recipes where changed since
            # the last pushed are however build and reuploaded.
            if not _file_checker.is_modified_file(recipe_path):

                _log_recipe_is_unmodified(_image_info)
                # Skip build and upload.
                continue

        _log_is_building(_image_info)
        # Actual building process.
        try:
            _image_info = _builder.build()
        except OSError:
            LOGGER.info(
                "File %s could not be build by Singularity.",
                recipe_path
                )
        # Push to sregistry if the recipe was build into an image.
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

def _log_recipe_is_unmodified(_image_info):
    """ Logger message, for when the recipe is unmodified. """
    _message_header = "Skipping Recipe not modified since last push:"
    _log_message(_image_info, _message_header)

def _log_is_building(_image_info):
    """ LOG message, for when an image starts building. """
    _message_header = "Building:"
    _log_message(_image_info, _message_header)

def _log_remote_image_exists(_image_info):
    """ LOG message, for when image already exists. """
    _message_header = "Image already in SRegistry:"
    _log_message(_image_info, _message_header)

def _log_message(_image_info, _message_header):
    """ Generic log with image infos. """
    # We want all the infos to be in one block seprate from the rest of the log
    # Thats why we add a newline to the start.
    _message_header = os.linesep + _message_header
    _image_info = {
        key: _image_info[key]
        for key
        in ('collection_name', 'container_name', 'image_version')
    }
    _template_message = _message_header + dedent(
        """
        collection: {collection_name}
        image:      {container_name}
        version:    {image_version}"""
    )
    _log_message = _template_message.format(**_image_info)
    LOGGER.info(_log_message)

def entrypoint_run():
    """ Target for setup.py entrypoint.
    
    Gathers the command line arguments and calls main with the values set.
    """
    _function_arguments = {}
    _cli_arguments = arg_parser()

    if _cli_arguments.build_log_dir:
        _function_arguments['build_log_dir'] = _cli_arguments.build_log_dir

    if _cli_arguments.image_type:
        _function_arguments['image_type'] = _cli_arguments.image_type

    _function_arguments['search_folder'] = _cli_arguments.path

    main(**_function_arguments)

# Still testing for __name__ == __main__
# to cleanly import this module during unit testing.
if __name__ == "__main__":
    entrypoint_run()
    