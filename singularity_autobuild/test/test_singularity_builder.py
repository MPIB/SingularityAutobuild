""" Unittests for the singularity_builder and the __main__ module.

This project is developed by using test driven design.
"""
import os
import unittest
from unittest.mock import patch
from subprocess import call

from singularity_autobuild.__main__ import arg_parser, main
from singularity_autobuild.singularity_builder import (
    Builder
    )
from singularity_autobuild.autobuild_logger import get_stdout_logger
from singularity_autobuild.test.configurator import configure_test_recipe

LOGGER = get_stdout_logger()

CONFIG = configure_test_recipe()
RECIPE_CONF = CONFIG['TEST_RECIPE']

MODULE_DIR = os.path.abspath(os.path.dirname(__file__))
COLLECTION = RECIPE_CONF['collection_name']
CONTAINER = RECIPE_CONF['container_name']
IMAGE = CONTAINER
VERSION = RECIPE_CONF['version_string']
IMAGE_TYPE = RECIPE_CONF['image_type']
RECIPE_FOLDER_PATH = RECIPE_CONF['recipe_folder_path']
RECIPE_FILE_PATH = RECIPE_CONF['recipe_file_path']
IMAGE_PATH = RECIPE_CONF['image_path']
SREGISTRY_STR = ''

class TestSingularityBuilder(unittest.TestCase):
    """Test the script used to build singularity images."""


    def test__init__(self):
        """ Test instantiation of Builder object.

        * Builder should have specified arguments
        * Builder should create specified attributes
        """

        # Object should have a default value for image type.
        _builder = Builder(recipe_path=RECIPE_FILE_PATH)
        self.assertEqual(_builder.image_type, IMAGE_TYPE)


        # Test if attributes where created in __init__ and have expected values
        _builder = Builder(
            recipe_path=RECIPE_FILE_PATH,
            image_type=IMAGE_TYPE
            )

        _expected_attributes = {
            'recipe_path': RECIPE_FILE_PATH,
            'image_type': IMAGE_TYPE,
            'build_folder': RECIPE_FOLDER_PATH,
            'version': VERSION,
            'image_name': IMAGE
        }
        for attribute in _expected_attributes:
            self.assertEqual(
                getattr(_builder, attribute),
                _expected_attributes[attribute]
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
            recipe_path=RECIPE_FILE_PATH,
            image_type=VERSION
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
            -len(VERSION):]
        self.assertEqual(
            VERSION,
            _image_suffix
            )
        # Clean up
        os.remove(_builder_response['image_full_path'])

    def test_is_build(self):
        """ Test the instance function to check if image already exists. """
        _builder = Builder(
            recipe_path=RECIPE_FILE_PATH,
            image_type=VERSION
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


class TestMain(unittest.TestCase):
    """ Test the main Function and its helpers """

    def setUp(self):
        LOGGER.debug("Set Up Main Test.")
        if os.path.isfile(IMAGE_PATH):
            LOGGER.debug("Removing leftover image.")
            os.remove(IMAGE_PATH)
        self.search_path = MODULE_DIR
        self.bad_recipe_file_path = "%s/%s" % (
            RECIPE_FOLDER_PATH,
            'bad_recipe.1.0.recipe'
        )
        if os.path.isfile(self.bad_recipe_file_path):
            os.remove(self.bad_recipe_file_path)

    def test_main(self):
        """ Test the main function that enables execution from command line. """
        LOGGER.debug(
            "Pushing test image %s/%s:%s",
            COLLECTION,
            CONTAINER,
            VERSION
            )
        main(
            search_folder=self.search_path,
            image_type='simg'
            )
        # Is the test image inside the sregistry?
        self.assertEqual(
            call([
                'sregistry',
                'search',
                "%s/%s:%s" % (COLLECTION, CONTAINER, VERSION)
                ]),
            0
        )
        # Was the local image removed after the push?
        self.assertFalse(os.path.isfile(IMAGE_PATH))

    def test_bad_recipe(self):
        """ Test if main can handle a 'bad' recipe file. """
        _bad_recipe_content = "%s\n%s\n\n%s\n%s" % (
            "Bootstrap: docker",
            "FROM: alpine",
            "%post",
            "exit 1"
        )
        LOGGER.info("Creating faulty test recipe %s.", self.bad_recipe_file_path)
        with open(self.bad_recipe_file_path, 'w') as bad_recipe:
            bad_recipe.write(_bad_recipe_content)

        try:
            main(
                search_folder=self.search_path,
                image_type='simg'
                )
        except OSError:
            self.fail("Erroneous recipe caused main() to fail.")



    def tearDown(self):
        # Clean up registry and local
        LOGGER.info("Deleting remote test image.")
        call([
            'sregistry',
            'delete',
            '-f',
            "%s/%s:%s" % (COLLECTION, CONTAINER, VERSION)
            ])
        if os.path.isfile(self.bad_recipe_file_path):
            os.remove(self.bad_recipe_file_path)

    def test_arg_parser(self):
        """ Test the function to parse command line arguments. """
        _image_type = 'simg'
        _args = ['', "--path", self.search_path, "--image_type", _image_type]
        with patch('sys.argv', _args):
            _response = arg_parser()
            self.assertEqual(_response.path, self.search_path)
            self.assertEqual(_response.image_type, _image_type)
            _response = arg_parser()
            self.assertEqual(_response.path, self.search_path)
            self.assertEqual(_response.image_type, _image_type)
