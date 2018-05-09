"""Contains unittests for the singularity_builder module.

This project is developed by using test driven design.
"""
import copy
import os
import random
import shutil
import types
import unittest
from unittest.mock import patch
from subprocess import call

import git
import iso8601

import singularity_builder.singularity_builder as singularity_builder
from singularity_builder.singularity_builder import (Builder,
                                                     GitLabPushEventInfo,
                                                     gitlab_events_api_request,
                                                     image_pusher,
                                                     recipe_finder)

COLLECTION = 'test_recipes'
CONTAINER = 'recipe_test'
VERSION = '1.0'
RECIPE_PATH = os.path.abspath('./test/%s/%s.%s.recipe' % (COLLECTION, CONTAINER, VERSION))
IMAGE_PATH = os.path.abspath('./test/test_recipes/recipe_test.simg')
SEARCH_PATH = os.path.abspath('./test')
SREGISTRY_STR = ''

class TestSingularityBuilder(unittest.TestCase):
    """Test the script used to build singularity images."""

    ATTRIBUTES = {}
    ATTRIBUTES['image_name'] = CONTAINER
    ATTRIBUTES['version'] = VERSION
    # The Builder should only work with absolute paths.
    ATTRIBUTES['build_folder'] = os.path.abspath('./test/test_recipes')
    ATTRIBUTES['recipe_path'] = "%s/%s.%s.recipe" % (
        ATTRIBUTES['build_folder'],
        ATTRIBUTES['image_name'],
        ATTRIBUTES['version']
        )
    ATTRIBUTES['image_type'] = 'simg'

    def test__init__(self):
        """ Test instantiation of Builder object.

        * Builder should have specified arguments
        * Builder should create specified attributes
        """

        # Object should have a default value for image type.
        _builder = Builder(recipe_path=self.ATTRIBUTES['recipe_path'])
        self.assertEqual(_builder.image_type, self.ATTRIBUTES['image_type'])


        # Test if attributes where created in __init__ and have expected values
        _builder = Builder(
            recipe_path=self.ATTRIBUTES['recipe_path'],
            image_type=self.ATTRIBUTES['image_type']
            )
        for attribute in self.ATTRIBUTES:
            self.assertEqual(
                getattr(_builder, attribute),
                self.ATTRIBUTES[attribute]
                )

    def test__init__exception(self):
        """ Tests exceptions thrown at instantiation. """
        # Recipe path should be set.
        self.assertRaises(AttributeError, callableObj=Builder)

    def test_build(self):
        """ Test building of the image.

         * If return values of build() are as expected.
         * If image File exists at the location specified in the build() return value.
         * If the file has the expected file extension.
        """
        # What is the return value of the build function?
        _builder = Builder(
            recipe_path=self.ATTRIBUTES['recipe_path'],
            image_type=self.ATTRIBUTES['image_type']
            )
        _response_keys = ['image_full_path', 'collection_name', 'image_version', 'container_name']
        _builder_response = _builder.build()
        for key in _response_keys:
            self.assertIn(key, _builder_response)
        # Is the image at the specified location?
        # _message to make unittest error more verbose.
        _message = ["Image exists.", "Image does not exist."]
        self.assertEqual(
            _message[0],
            _message[0] if os.path.isfile(_builder_response['image_full_path'])
            else _message[1]
            )
        # Is the image of the specified type?
        # i.e. does the full path end correctly.
        _image_suffix = _builder_response['image_full_path'][
            -len(self.ATTRIBUTES['image_type']):]
        self.assertEqual(
            self.ATTRIBUTES['image_type'],
            _image_suffix
            )
        # Clean up
        os.remove(_builder_response['image_full_path'])

    def test_is_build(self):
        """ Test the instance function to check if image already exists. """
        _builder = Builder(
            recipe_path=self.ATTRIBUTES['recipe_path'],
            image_type=self.ATTRIBUTES['image_type']
            )
        # Not Build yet
        self.assertFalse(_builder.is_build())
        self.assertEqual(_builder.build_status, _builder.is_build())
        _builder_response = _builder.build()
        # Build
        self.assertTrue(_builder.is_build())
        self.assertEqual(_builder.build_status, _builder.is_build())
        os.remove(_builder_response['image_full_path'])
        # Build removed
        self.assertFalse(_builder.is_build())
        self.assertEqual(_builder.build_status, _builder.is_build())




class TestRecipeFinder(unittest.TestCase):
    """ Test the generator that returns directory and file information. """

    RECIPE_PARENT_PARENT = os.path.abspath('./test')

    def test_exceptions(self):
        """ Test if specified exceptions are raised. """
        with self.assertRaises(OSError):
            next(recipe_finder(path=os.path.abspath(__file__)))

    def test_recipe_finder(self):
        """ Test if recipes can be found and returned as expected. """
        _finder = recipe_finder(self.RECIPE_PARENT_PARENT)
        self.assertIsInstance(_finder, types.GeneratorType)
        _recipe = next(_finder)
        self.assertEqual(_recipe, RECIPE_PATH)

class TestImagePusher(unittest.TestCase):
    """ Test the function to Push an image to an sregistry. """

    def setUp(self):
        os.environ['SREGISTRY_CLIENT'] = 'registry'
        _builder = Builder(recipe_path=RECIPE_PATH, image_type='simg')
        _build_info = _builder.build()
        self.image_path = _build_info['image_full_path']
        self.collection = _build_info['collection_name']
        self.version = _build_info['image_version']
        self.image = _build_info['container_name']



    def test_image_pusher(self):
        """ Test the image upload function. """
        self.assertTrue(
            image_pusher(
                image_path=self.image_path,
                collection=self.collection,
                version=self.version,
                image=self.image
                )
        )
        # Does the image exist inside the sregistry?
        self.assertNotEqual(
            call([
                'sregistry',
                'search',
                "%s/%s:%s" % (self.collection, self.image, self.version)
                ]),
            1
        )

    def tearDown(self):
        print(self.image_path)
        os.remove(self.image_path)
        call([
            'sregistry',
            'delete',
            '-f',
            "%s/%s:%s" % (self.collection, self.image, self.version)
            ])

class TestGitLabPushEventInfo(unittest.TestCase):
    """ Test the the class containing gitlab functions. """

    BRANCH = 'master'
    NEWEST_PUSH_DATE = "2000-04-11T11:35:15.188Z"
    PUSH_DATE_OBJECT = iso8601.parse_date(NEWEST_PUSH_DATE)
    GIT_TEST_REPO_PATH = os.path.abspath('test_repo')

    FROM_COMMIT_INDEX = 2
    TO_COMMIT_INDEX = 4

    # Part of the Response, that should be ignored when selecting the latest push.
    RESPONSE_FILLER = [
        {
            "project_id":42,
            "action_name":"pushed to",
            "created_at":"1999-02-11T11:35:15.188Z",
            "author":{},
            "push_data":{
                "commit_count":2,
                "action":"pushed",
                "ref_type":"branch",
                "commit_from":"from_commit",
                "commit_to":"to_commit",
                "ref":"branch_name",
                "commit_title":"did_something"
                },
            "author_username":"test"
        },
        {
            "project_id":"some_id",
            "author_username":"test"
        }
    ]

    expected_push = {
        "project_id":42,
        "action_name":"pushed to",
        "created_at":NEWEST_PUSH_DATE,
        "author":{},
        "push_data":{
            "commit_count":5,
            "action":"pushed",
            "ref_type":"branch",
            "commit_from": "from_commit_dummy",
            "commit_to": "to_commit_dummy",
            "ref": BRANCH,
            "commit_title":"did_something"
            },
        "author_username":"test"
    }
    all_push_events = []
    git_lab_response = []
    changed_files = {}
    repo = git.Repo()


    def setUp(self):
        """ Initiate a test git repository. """

        ## Cleanup beforehand
        if os.path.isdir(self.GIT_TEST_REPO_PATH):
            shutil.rmtree(self.GIT_TEST_REPO_PATH)

        if os.path.isfile(self.GIT_TEST_REPO_PATH):
            os.remove(self.GIT_TEST_REPO_PATH)

        # Set up Repo
        os.mkdir(self.GIT_TEST_REPO_PATH)
        # odbt is set because default value did not work with create_head
        _repo = git.Repo.init(path=self.GIT_TEST_REPO_PATH, odbt=git.GitDB)

        # Create some files and do some commits
        _file_to_commit = ""
        for commit in range(0, 5):
            _file_to_commit = "%s/%s" % (
                self.GIT_TEST_REPO_PATH, str(commit)
            )
            # Create and fill file with some content.
            with open(_file_to_commit, 'w') as _file:
                _file.write(
                    str(
                        random.randint(0, 1000000000000000000)
                        )
                    )

            _repo.index.add([_file_to_commit])
            _repo.index.commit("Made %s commit." % commit)

        # make a new branch
        _branch_name = 'test_branch'
        _master = _repo.head.reference
        # Create Branch
        _branch = _repo.create_head(_branch_name)
        # Switch to
        _repo.head.reference = _branch
        # Commit to
        open(self.GIT_TEST_REPO_PATH + '/' + _branch_name, 'wb').close()
        _repo.index.add([_branch_name])
        _repo.index.commit(_branch_name)
        # Switch back
        _repo.head.reference = _master


        ## Set up the mock GitLab API response to work with.
        # Get the hashes of the commits that define content of the mock push.
        _from_commit = _repo.head.log_entry(self.FROM_COMMIT_INDEX).newhexsha
        _to_commit = _repo.head.log_entry(self.TO_COMMIT_INDEX).newhexsha

         # Define the dictionary containing changed filenames
        _from_commit_objects = _repo.commit(_from_commit).parents
        for _from_commit_object in _from_commit_objects:
            for _commit_file in _from_commit_object.diff(_repo.commit(_to_commit)):
                _filepath = os.path.abspath(_commit_file.a_path)
                self.changed_files[_filepath] = _commit_file.change_type

       # Make a copy of the class constant
        self.expected_push["push_data"]["commit_from"] = _from_commit
        self.expected_push["push_data"]["commit_to"] = _to_commit

        # Make a copy of the class constant
        self.git_lab_response = copy.deepcopy(self.RESPONSE_FILLER)
        self.all_push_events = [self.expected_push, self.git_lab_response[0]]
        self.git_lab_response.append(self.expected_push)

        self.repo = _repo

    def test_extract_push_data(self):
        """ Test the function to filter out push events from a json file. """

        _result_list = GitLabPushEventInfo.extract_push_data(
            git_lab_response=self.git_lab_response
        )

        # Is the result a subset of the expected?
        for result in _result_list:
            self.assertTrue(result in self.all_push_events)

        # Is the expected also subset of the result, i.e. are they the same?
        for result in self.all_push_events:
            self.assertTrue(result in _result_list)

    def test_is_modified_file(self):
        """ Test the function to check if a file was modified since the last push. """
        # Get full path of all repo files
        _all_files_set = set()
        for root, _, files in  os.walk(self.GIT_TEST_REPO_PATH):
            for file in files:
                _all_files_set.add(
                    os.path.abspath(os.path.join(
                        root, file
                    ))
                )

        # Get names of all changed files.
        _changed_fileset = set(
            [key for key in self.changed_files]
        )
        _unchanged_fileset = list(_all_files_set - _changed_fileset)
        _object = GitLabPushEventInfo(
            git_lab_response=self.git_lab_response,
            local_repo=self.GIT_TEST_REPO_PATH
        )
        # Test  if all changed files are categorized correctly
        for _file in _changed_fileset:
            self.assertTrue(_object.is_modified_file(
                file_path=_file
            ))
        # Test  if all unchanged files are categorized correctly
        for _file in _unchanged_fileset:
            self.assertFalse(
                _object.is_modified_file(file_path=_file)
                )

    def  test_get_modified_files(self):
        """ Test the function, that returns all modified files between two commits. """
        _expected_filedict = self.changed_files
        _test_filelist = GitLabPushEventInfo.get_changed_files(
            self.repo,
            self.expected_push["push_data"]["commit_from"],
            self.expected_push["push_data"]["commit_to"]
        )
        self.assertEqual(_expected_filedict, _test_filelist)

    def test_get_latest_push(self):
        """ Test the function to get last push date.(not the most recent) """

        _test_push_date = GitLabPushEventInfo.get_latest_push(
            git_lab_response=self.all_push_events
            )
        _expected_value = self.expected_push
        self.assertEqual(_test_push_date, _expected_value)

    def test_instantiation(self):
        """ Test the constructor of the class. """
        _expected_from_commit_sha = self.expected_push["push_data"]["commit_from"]
        _expected_to_commit_sha = self.expected_push["push_data"]["commit_to"]
        _test_object = GitLabPushEventInfo(
            git_lab_response=self.git_lab_response,
            local_repo=self.GIT_TEST_REPO_PATH
        )
        _test_from_commit_sha = _test_object.from_commit.hexsha
        _test_to_commit_sha = _test_object.to_commit.hexsha

        self.assertEqual(_expected_from_commit_sha, _test_from_commit_sha)
        self.assertEqual(_expected_to_commit_sha, _test_to_commit_sha)

    def tearDown(self):
        """ Clean up test git repo. """

        if os.path.isdir(self.GIT_TEST_REPO_PATH):
            shutil.rmtree(self.GIT_TEST_REPO_PATH)

        if os.path.isfile(self.GIT_TEST_REPO_PATH):
            os.remove(self.GIT_TEST_REPO_PATH)

class TestGitlabAPIRequest(unittest.TestCase):
    """Test the function to call a gitlab API."""

    def test_gitlab_events_api_request(self):
        """Test the function to call a gitlab API."""
        try:
            _api_url = os.environ['GITLAB_API_STRING']
            _api_key = os.environ['GITLAB_API_TOKEN']
        except KeyError:
            raise EnvironmentError("GitLab API environment variables are not set.")
        _api_response = gitlab_events_api_request(api_url=_api_url, api_key=_api_key)
        self.assertIsInstance(_api_response, list)
        self.assertIsInstance(_api_response[0], dict)

class TestMain(unittest.TestCase):
    """ Test the main Function and its helpers """

    def setUp(self):
        if os.path.isfile(IMAGE_PATH):
            os.remove(IMAGE_PATH)

    def test_main(self):
        """ Test the main function that enables execution from command line. """
        singularity_builder.main(
            search_folder=SEARCH_PATH,
            image_type='simg', test_run=True
            )
        # Is the test image inside the sregistry?
        self.assertNotEqual(
            call([
                'sregistry',
                'search',
                "%s/%s:%s" % (COLLECTION, CONTAINER, VERSION)
                ]),
            1
        )
        # Was the local image removed after the push?
        self.assertFalse(os.path.isfile(IMAGE_PATH))
        # Clean up registry
        call([
            'sregistry',
            'delete',
            '-f',
            "%s/%s:%s" % (COLLECTION, CONTAINER, VERSION)
        ])

    def test_arg_parser(self):
        """ Test the function to parse command line arguments. """
        _image_type = 'simg'
        _args = ['', "--path", SEARCH_PATH, "--image_type", _image_type]
        with patch('sys.argv', _args):
            _response = singularity_builder.arg_parser()
            self.assertEqual(_response.path, SEARCH_PATH)
            self.assertEqual(_response.image_type, _image_type)
