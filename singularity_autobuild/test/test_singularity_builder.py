""" Unittests for the singularity_builder and the __main__ module.

This project is developed by using test driven design.
"""
import os
import unittest
from unittest.mock import patch
from subprocess import call

from singularity_autobuild.test import test_image_recipe_tools 
from singularity_autobuild.__main__ import arg_parser, main
from singularity_autobuild.singularity_builder import (
    Builder
    )
from singularity_autobuild.stdout_logger import LOGGER

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
COLLECTION = 'test_recipes'
CONTAINER = 'recipe_test'
VERSION = '1.0'
IMAGE_TYPE = 'simg'
RECIPE_FOLDER_PATH = '%s/%s' % (
    MODULE_DIR,
    COLLECTION,
)
RECIPE_FILE_PATH = '%s/%s.%s.recipe' % (
    RECIPE_FOLDER_PATH,
    CONTAINER,
    VERSION
)
IMAGE_PATH = "%s/%s/%s.%s" % (
    MODULE_DIR,
    COLLECTION,
    CONTAINER,
    IMAGE_TYPE
)
SREGISTRY_STR = ''

class TestSingularityBuilder(unittest.TestCase):
    """Test the script used to build singularity images."""

    ATTRIBUTES = {}
    ATTRIBUTES['image_name'] = CONTAINER
    ATTRIBUTES['version'] = VERSION
    # The Builder should only work with absolute paths.
    ATTRIBUTES['build_folder'] = MODULE_DIR+'/test_recipes'
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
        # Using functionality from the TestImagePusher class,
        # since the expected outcome is the same.
        push_test = test_image_recipe_tools.TestImagePusher(methodName='runTest')
        push_test.collection = COLLECTION
        push_test.version = VERSION
        push_test.image = CONTAINER
        push_test.test_image_pusher()
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
        # Clean up registry
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