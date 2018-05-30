# -*- coding: utf-8 -*-
""" Tools to work with the Gitlab v3 API.


"""
import os
import json
import re
from typing import  Optional

import git
import iso8601
import requests

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

def call_gitlab_events_api(api_url: str, api_key: str) -> list:
    """ Call a gitlab API and return its response as list.

    :params api_url: The full url for the api request.
    :params api_key: The key for the API.
    :returns:        The API response.
    """
    _header = {"PRIVATE-TOKEN": api_key}
    _response = requests.get(api_url, headers=_header)
    return json.loads(_response.text)
