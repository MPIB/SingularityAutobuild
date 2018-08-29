# -*- coding: utf-8 -*-
"""Contains unittests for the gitlab_tools module.

This project is developed by using test driven design.
The gitlab_tools module is specified to work with GitLab API v3.
"""

import copy
import os
import random
import shutil
import unittest

import git
import iso8601

from singularity_autobuild.gitlab_tools import (GitLabPushEventInfo,
                                                call_gitlab_events_api)


class TestGitLabPushEventInfo(unittest.TestCase):
    """ Test the the class capable of extracting information from gitlab api data.

    The GitLabPushEventInfo is specified to work with data from
    the GitLab v3 API.

    The API returns data in json format and can be read into a dict using
    the json module.

    A mock git repository is created via gitpython in the stUp method.

    A mock GitLab response is created by ingesting data from the mock git
    repository into template python dictionaries.
    Filler and expected push dictionaries are then merged in a list.
    This creates a List, similar to what the standard library json
    would parse from a GitLab API response string.

    :cvar str BRANCH:                 The branch ingested into the expected_push data.
                                      Functionality using branch selection is not jet
                                      implemented.

    :cvar str NEWEST_PUSH_DATE:       Datestring in a format used by the GitLab API.
                                      Is supposed to be the newest push date, ingested
                                      into the mock API response.

    :cvar datetime PUSH_DATE_OBJECT:  NEWEST_PUSH_DATE parsed to a date object.

    :cvar str GIT_TEST_REPO_PATH:     Path to the mock git repository to be created.

    :cvar int FROM_COMMIT_INDEX:      List index of the first commit, that is part of the
                                      newest push from the mock API response.

    :cvar int TO_COMMIT_INDEX:        List index of the last commit, that is part of the
                                      newest push from the mock API response.

    :cvar list RESPONSE_FILLER:       Mock API Response without the expected_push data.

    :ivar dict expected_push:         Represents a single push event from a GitLab
                                      API response. It is the reference push event,
                                      that is expected to be returned as latest
                                      push event.

    :ivar list all_push_events:       List of all push data sections from the mock
                                      API response.

    :ivar list git_lab_response:      Mock api response, as expected when the read via
                                      the json.read() method.

    :ivar dict changed_files:         A dict with all files changed in the most recent push
                                      as keys and the type of change as their value.

    :ivar git.Repo repo:              A gitpython git.Repo object that handles the
                                      mock repository.
    """

    BRANCH = 'master'
    NEWEST_PUSH_DATE = "2000-04-11T11:35:15.188Z"
    PUSH_DATE_OBJECT = iso8601.parse_date(NEWEST_PUSH_DATE)
    GIT_TEST_REPO_PATH = os.path.dirname(os.path.realpath(__file__)) + '/test_repo'

    FROM_COMMIT_INDEX = 2
    TO_COMMIT_INDEX = 4

    # Part of the Response, that should be ignored when selecting the latest push.
    # i.e. filler data
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



    def setUp(self):
        """ Initiate a test git repository. """
        self.expected_push = {
            "project_id":42,
            "action_name":"pushed to",
            "created_at":self.NEWEST_PUSH_DATE,
            "author":{},
            "push_data":{
                "commit_count":5,
                "action":"pushed",
                "ref_type":"branch",
                "commit_from": "from_commit_dummy", # From commit is here
                "commit_to": "to_commit_dummy",     # To commit is here
                "ref": self.BRANCH,
                "commit_title":"did_something"
                },
            "author_username":"test"
        }
        self.all_push_events = list
        self.git_lab_response = list
        self.changed_files = {}
        self.repo = None

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
    """Test the function to call a gitlab API.

    The Functions tested here are specified to work with
    a GitLab API v3.
    """

    def test_gitlab_events_api_request(self):
        """Test the function to call a gitlab API.

        The API should return a json list filled with objects.
        """
        try:
            _api_url = os.environ['GITLAB_API_STRING']
            _api_key = os.environ['GITLAB_API_TOKEN']
        except KeyError:
            raise EnvironmentError("GitLab API environment variables are not set.")
        _api_response = call_gitlab_events_api(api_url=_api_url, api_key=_api_key)
        # First level is a list,
        self.assertIsInstance(_api_response, list)
        # filled with objects
        self.assertIsInstance(_api_response[0], dict)
