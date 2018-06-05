""" Module for miscellaneous modules to work with sregistry. """

import os
import glob
import re
import subprocess
from subprocess import call
from typing import Generator
from singularity_autobuild.autobuild_logger import get_stdout_logger

LOGGER = get_stdout_logger()

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
    _folder_full_path = os.path.dirname(recipe_file_full_path)
    _out_string = os.path.basename(_folder_full_path)
    return _out_string

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

def get_dependency_from_recipe(recipe_file_full_path: str) -> dict:
    """ Reads a recipe file and returns its Bootstrap and From values.

    :returns: A dict with a key equal to the recipes Bootstrap method and
              the value of this key being the value of its From value.
    :raises: UserWarning
    """
    _bootstrap = ''
    _from = ''
    _bootstrap_regex = r'^bootstrap:\s(.*?)$'
    _from_regex = r'^from:\s(.*?)$'

    with open(recipe_file_full_path, 'r') as recipe:
        for line in recipe:
            line = line.strip()
            if re.match(_bootstrap_regex, line, re.IGNORECASE):
                _bootstrap = re.sub(_bootstrap_regex, r'\1', line, flags=re.IGNORECASE)
            if re.match(_from_regex, line, re.IGNORECASE):
                _from = re.sub(_from_regex, r'\1', line, flags=re.IGNORECASE)
            if _bootstrap and _from:
                break
    if not _bootstrap or not _from:
        raise UserWarning('Recipe at %s is invalid' % recipe_file_full_path)
    return {_bootstrap: _from}

def get_path_from_dependency(
        recipe_dependency_value: str,
        recipe_base_folder_path: str
    ) -> str:
    """ Searches the base folder for a file, that corresponse to the dependency passed.

    :param recipe_dependency_value: Value of the "From:" section from a
                                    recipe file, used by singularity
                                    to find the base image.
    :param recipe_base_folder_path: Full path of the base folder,
                                    containing all recipes.
    :returns:                       Full path to the parent recipe or
                                    an empty string '' if it is not a local
                                    dependency.
    """

    if not is_own_dependency(recipe_dependency_value):
        return ''

    _dependency_value_regex = re.compile(
        r'^(?:.*?\/)?'   # Match possible host address and ignore it
        r'(?P<collection>.+?)\/'       # Match collection
        r'(?P<container>.+?)'         # Match container/image name
        r'(?::(?P<version>.*?))?$'  # Match possible version Tag
        )
    _filename_components = re.search(_dependency_value_regex, recipe_dependency_value)
    _glob_dict = {'basepath': recipe_base_folder_path}
    _glob_dict.update(_filename_components.groupdict())

    _glob_string = ''

    # lastest tag translates to a filename without
    if 'version' in _glob_dict:
        if _glob_dict['version'] == 'latest':
            _glob_dict.pop('version')

    if "version" in _glob_dict:
        if _glob_dict != 'latest':
            _glob_string = (
                '{basepath}/**/{collection}/{container}.{version}.recipe'.format(
                    **_glob_dict)
            )
    else:
        _glob_string = (
            '{basepath}/**/{collection}/{container}.recipe'.format(
                **_glob_dict)
        )

    # Find corresponding Files
    _glob_results = glob.glob(
        _glob_string,
        recursive=True
    )
    if len(_glob_results) > 1:
        raise RuntimeError(
            (
                "The naming schema of recipe {} clashes with. "
                "They cannot both exist in one sregistry."
            ).format(', '.join(_glob_results))
        )
    if not _glob_results:
        raise RuntimeError(
            "Unresolved dependency on {}".format(
                recipe_dependency_value
            )
        )
    return _glob_results[0]

def is_own_dependency(recipe_dependency_value: str) -> bool:
    """ Returns True if the dependency links to the sregistry used to push images to.

    Needs the env variable SREGISTRY_HOSTNAME to be set.
    This variable is also needed for the .sregistry file setup.

    :param recipe_dependency_value: Value from a recipes "From:" section declaring the base Image.
    """
    _sregistry_host_name_raw = os.environ['SREGISTRY_HOSTNAME']
    _sregistry_host_name = re.sub(r'^http[s]?:\/\/(.*)$', r'\1', _sregistry_host_name_raw)
    return _sregistry_host_name in recipe_dependency_value


def dependency_resolver(recipe_file_paths: list, recipe_base_path: str) -> list:
    """ Sorts a list of recipe file paths based on their base image dependency.

    Sorts the list in a way, that all recipes with dependencies linking
    outside the local storage are sorted to the beginning.
    All other recipes that follow those recipes are sorted, that
    recipe with a child dependency, is always sorted behind its parent
    in the list.

    Since a recipe can only depend on one base image, it is sufficient,
    that this base image is in front of the child image during the building
    process.

    :param recipe_file_paths: List of paths to recipe files.
    :param recipe_base_path:  Path to the base folder containing all recipe files.
    :returns:                 List of recipe paths sorted by their dependency.
                              With Parents sorted before their children.
    """
    # Does the list of recipes make sense?
    # Does it create duplicate containers?
    recipe_list_sanity_check(recipe_file_paths=recipe_file_paths)

    _dependency_dict = {}
    for recipe in recipe_file_paths:
        dependency_drill_down(
            dependency_dict=_dependency_dict,
            recipe_path=recipe,
            recipe_base_path=recipe_base_path
        )
    _sorted_output_list = sorted(_dependency_dict, key=_dependency_dict.__getitem__)
    _dependency_dict = None
    return _sorted_output_list

def dependency_drill_down(
        dependency_dict: dict,
        recipe_path: str,
        recipe_base_path: str
    ) -> None:
    """ Recursively drills down a dependency chain.

    The dependency dict is passed as reference through all recursive functions calls.
    It functions as a cache for already known results and as the expected result.
    It is however not returned.

    Sets a dependency as 0, if it does not depend on container from
    the private sregistry. If a child of a recipe is found, this number
    is incremented by one.

    Example:

    .. code-block:: python

                            {
                                '/path/to/Parent.recipe': 0,
                                '/path/to/child.recipe': 1,
                                '/path/to/child_of_child.recipe': 2
                            }

    :param dependency_dict: Contains already known dependencies.
                            The dictionary is directly modified
                            and only passed as reference not as copy.
                            It functions both as a cache and as the final
                            result of the function.
    :param child_key:       Path to the recipe whose dependency
                            is calculated.
    """
    # Dependency value already known
    if recipe_path in dependency_dict:
        return

    # End of the dependency chain
    _this_dependency_dict = get_dependency_from_recipe(recipe_path)
    # The recipe cannot depend on a private base image if
    # the recipe is not build from a shub base image
    if 'shub' not in _this_dependency_dict:
        dependency_dict.update({recipe_path: 0})
        return

    # The recipe cannot depend on a private base image if
    # does not reference a private shub image.
    _this_dependency = _this_dependency_dict['shub']
    if not is_own_dependency(_this_dependency):
        dependency_dict.update({recipe_path: 0})
        return

    # The recipe depends on an image in the private,
    # sregistry, what is the dependency value of its parent?
    _parent_file_path = get_path_from_dependency(
        _this_dependency, recipe_base_path)
    dependency_drill_down(
        dependency_dict=dependency_dict,
        recipe_path=_parent_file_path,
        recipe_base_path=recipe_base_path
    )
    # Give this recipe the dependency of its Parent incremented by one.
    dependency_dict.update(
        {recipe_path: dependency_dict[_parent_file_path]+1}
    )
    return

def recipe_list_sanity_check(recipe_file_paths: list) -> None:
    """ Checks a list of recipe file paths for recipes creating duplicates.

    Raises an exception if at least two recipes are found in the passed list,
    that would be uploaded to the same collection, with the same name, and the same
    version.

    :param recipe_file_paths: A list of full paths to recipe files.
    :raises: RuntimeError
    """
    _uniqueness_counter = {}

    _image_full_name = ''
    _recipe_name = ''
    for recipe in recipe_file_paths:
        _recipe_name = os.path.basename(recipe)
        _image_full_name = "%s/%s:%s" % (
            get_collection_from_recipe_path(recipe),
            get_image_name_from_recipe(_recipe_name),
            get_version_from_recipe(_recipe_name)
        )
        if _image_full_name not in  _uniqueness_counter:
            _uniqueness_counter[_image_full_name] = recipe
        else:
            raise RuntimeError(
                ("The naming schema of recipe %s clashes with %s. "
                 "They cannot both exist in one sregistry.") % (
                     _uniqueness_counter[_image_full_name],
                     recipe
                     )
            )
