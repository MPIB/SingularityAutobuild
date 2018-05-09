""" Go through a directory structure, Build and upload singularity images.

The Functions and classes of this module need to be able to execute
`singularity` and `sregistry` from the terminal and
need to be executed by a user, that has an .sregistry file in the home directory.
The .sregistry file needs to enable the user to have admin and superuser access
to the sregistry-server.
For further information look at the sregistry clients documentation:
`sregistry-cli <https://singularityhub.github.io/sregistry/credentials>`_

"""

import argparse
import glob
import json
import logging
import os
import re
import subprocess
from subprocess import call
import sys
from typing import Generator, Optional

import git
import iso8601
import requests

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

    LOGDIR = os.path.abspath('./build_logs')

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

        if not os.path.exists(self.LOGDIR):
            os.makedirs(self.LOGDIR)
        _logpath = "%s/%s.%s.%s.log" % (
            self.LOGDIR,
            _image_info['collection_name'],
            _image_info['container_name'],
            _image_info['image_version']
            )

        try:
            with open(
                _logpath,
                'w'
                ) as _logfile:
                call(
                    [
                        "singularity",
                        "build",
                        _image_info['image_full_path'],
                        self.recipe_path
                    ],
                    stdout=_logfile,
                    stderr=_logfile,
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

class GitLabPushEventInfo(object):
    """ Toolset and object to work with the GitLab API V3

    Methods expect an already parsed API response
    containing the events of a project.
    The API used, should deliver a json list, filled with
    json objects.

    The __init__ takes a parsed Gitlab response and
    the returned object is able to determine if a given file
    was modified during the commits of the last push.

    Example API-call that delivers expected response:
     * :code:`GET {base_url}/api/v3/projects/{project_id}/events`

    :param git_lab_response: A list of gitlab events obtained from a
                             GitLab v3 API.
    :param local_repo:       The path to the local git repo to work with.
    """

    PUSH_DATE_KEY = "created_at"


    def __init__(self, git_lab_response: list, local_repo: str):
        _latest_push = self.get_latest_push(git_lab_response)
        _from_commit_sha = _latest_push["push_data"]["commit_from"]
        _to_commit_sha = _latest_push["push_data"]["commit_to"]
        local_repo = os.path.abspath(local_repo)
        # Test if Repo actually exists and is a directory
        if not os.path.isdir(local_repo):
            if not os.path.exists(local_repo):
                raise ValueError("%s does not exist." % local_repo)
            raise ValueError("%s is not a directory." % local_repo)
        self.repo = git.Repo(path=local_repo)
        self.from_commit = self.repo.commit(_from_commit_sha)
        self.to_commit = self.repo.commit(_to_commit_sha)
        local_repo = os.path.abspath(local_repo)
        self.changed_files = self.get_changed_files(
            self.repo,
            _from_commit_sha,
            _to_commit_sha
            )
        _second_to_last_commits = self.from_commit.parents



    def is_modified_file(self, file_path: str) -> bool:
        """ Gives truth value for a files modification status.

        Cross references objects dictionary of files,
        modified within commits pushed during the latest push,
        with the input file path.

        :returns: Truth value for for a files modification status.
        """
        _is_modified = bool(
            file_path in [file_path for file_path in self.changed_files]
            )
        if _is_modified:
            _change_type = self.changed_files[file_path]
            _is_modified = re.findall(r'[AMR].*', _change_type)
        return _is_modified

    @classmethod
    def get_changed_files(
            cls,
            repo: git.Repo,
            begin_sha: str,
            end_sha: str
        ) -> dict:
        """ Return the files changed in a range of commits and their change type.

        The dictionary of changed files is supposed to contain all files
        changed in all commits between begin and end. This includes begin
        and end commit. To get the files changed in the begin commit a diff
        between the commit before the begin commit  and the end commit has to be
        performed.

        :param repo:        Repository object to work with.
        :param begin_sha:   The hexsha of the first commit of the
                            intervall. Has to be an earlier
                            commit than end_sha.
        :param end_sha:     The hexsha of the last commit of the
                            intervall. Has to be a later commit than
                            begin_sha.
        :returns:           Dictionary with all changed files
                            as keys and their change type as values.
        """
        _changed_files = {}
        _diff_begin_commit = repo.commit(begin_sha)
        _diff_end_commit = repo.commit(end_sha)

        if _diff_begin_commit.committed_datetime > _diff_end_commit.committed_datetime:
            raise ValueError("Begin commit happened before the end commit")
        # Begin is the first commit
        if not _diff_begin_commit.parents:
            # Since its the first commit files can only have been added.
            for file in _diff_begin_commit:
                _changed_files[os.path.abspath(file)] = 'A'
            # git.Commit.parents returns a tuple
            # so we expect to work with a tuple.
            _diff_begin_commit = (_diff_begin_commit)
        else:
            # Set the beginning to a commit earlier.
            # (or commits {plural} if original commit is a merge)
            _diff_begin_commit = _diff_begin_commit.parents

        for commit in _diff_begin_commit:
            for file in commit.diff(_diff_end_commit):
                _changed_files[os.path.abspath(file.a_path)] = file.change_type

        return _changed_files



    @classmethod
    def get_latest_push(cls, git_lab_response: list) -> Optional[dict]:
        """ Get the latest push data from a GitLab response.

        Uses extract_push_data to make sure to work only with
        push data.

        :param git_lab_response: A list of dictionaries.
                                 The dictionary is expected to conform to
                                 a GitLab API V3 response containing the
                                 events of a project.
        :returns: A dictionary corresponding to the json object
        """
        git_lab_response = cls.extract_push_data(git_lab_response)
        _push_dates = []

        if bool(git_lab_response) is False:
            return None

        # Extract the dates into a List
        for push in git_lab_response:
            _push_dates.append(
                iso8601.parse_date(
                    push[cls.PUSH_DATE_KEY]
                )
            )
        # Get latest date.
        _latest_date = max(_push_dates)
        # Get latest dates index.
        _latest_push_index = _push_dates.index(_latest_date)

        # Connect Push event and date with the dates index.
        return git_lab_response[_latest_push_index]



    @classmethod
    def extract_push_data(cls, git_lab_response: list) -> list:
        """ Filter gitlab response for push events.

        :returns: A list of push event dictionaries.
        """

        _response_list = []

        # A push event should have the Key push_data
        # The corresponding value should be a dictionary
        # The dictionary should have a key called action with
        # the value pushed.
        for event in git_lab_response:
            if "push_data" in event:
                if event["push_data"]["action"] == "pushed":
                    _response_list.append(event)

        return _response_list

def gitlab_events_api_request(api_url: str, api_key: str) -> list:
    """ Call a gitlab API and return its response as list.

    :params api_url: The full url for the api request.
    :params api_key: The key for the API.
    :returns:        The API response.
    """
    _header = {"PRIVATE-TOKEN": api_key}
    _response = requests.get(api_url, headers=_header)
    return json.loads(_response.text)


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
    _gitlab_response = gitlab_events_api_request(
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


if __name__ == '__main__':
    ARGUMENTS = arg_parser()
    main(search_folder=ARGUMENTS.path, image_type=ARGUMENTS.image_type)
