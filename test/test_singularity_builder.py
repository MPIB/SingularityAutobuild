""" Unittests for the singularity_builder and the __main__ module.

This project is developed by using test driven design.
"""
import logging
import os
import sys
import types
import unittest
from unittest.mock import patch
from subprocess import call

from singularity_builder.__main__ import arg_parser, main
from singularity_builder.singularity_builder import (
    Builder,
    image_pusher,
    recipe_finder
    )

from singularity_builder.sregistry_tools import image_in_sregistry

# Logging setup start
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.DEBUG)

HANDLER = logging.StreamHandler(sys.stdout)
HANDLER.setLevel(logging.DEBUG)
HANDLER.setFormatter(
    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
LOGGER.addHandler(HANDLER)
# Logging setup end


MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
COLLECTION = 'test_recipes'
CONTAINER = 'recipe_test'
VERSION = '1.0'
IMAGE_TYPE = 'simg'
RECIPE_PATH = '%s/%s/%s.%s.recipe' % (
    MODULE_DIR,
    COLLECTION,
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

class TestRecipeFinder(unittest.TestCase):
    """ Test the generator that returns directory and file information. """

    RECIPE_PARENTS_PARENT = MODULE_DIR

    def test_exceptions(self):
        """ Test if specified exceptions are raised. """
        with self.assertRaises(OSError):
            next(recipe_finder(path=os.path.abspath(__file__)))

    def test_recipe_finder(self):
        """ Test if recipes can be found and returned as expected. """
        _finder = recipe_finder(self.RECIPE_PARENTS_PARENT)
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
        LOGGER.debug("Deleting remote test image.")
        os.remove(self.image_path)
        call([
            'sregistry',
            'delete',
            '-f',
            "%s/%s:%s" % (self.collection, self.image, self.version)
            ])

class TestMain(unittest.TestCase):
    """ Test the main Function and its helpers """

    def setUp(self):
        LOGGER.debug("Set Up Main Test.")
        if os.path.isfile(IMAGE_PATH):
            LOGGER.debug("Removing leftover image.")
            os.remove(IMAGE_PATH)
        self.search_path = MODULE_DIR

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

    def tearDown(self):
        # Clean up registry
        LOGGER.debug("Deleting remote test image.")
        call([
            'sregistry',
            'delete',
            '-f',
            "%s/%s:%s" % (COLLECTION, CONTAINER, VERSION)
            ])

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

class TestImageInSRegistry(unittest.TestCase):
    """ Test the function to check, if an image already exists in the sregistry. """

    def setUp(self):
        os.environ['SREGISTRY_CLIENT'] = 'registry'
        self.builder = Builder(recipe_path=RECIPE_PATH, image_type='simg')
        _build_info = self.builder.build()
        self.collection = _build_info
        self.image_path = _build_info['image_full_path']
        self.collection = _build_info['collection_name']
        self.version = _build_info['image_version']
        self.image = _build_info['container_name']

        image_pusher(
            image_path=self.image_path,
            collection=self.collection,
            version=self.version,
            image=self.image
        )

    def test_image_in_sregistry(self):
        """ Tested function should return correct boolean for image existence. """
        self.assertTrue(image_in_sregistry(
            collection=self.collection,
            version=self.version,
            image=self.image
        ))

        call([
            'sregistry',
            'delete',
            '-f',
            "%s/%s:%s" % (self.collection, self.image, self.version)
            ])

        self.assertFalse(image_in_sregistry(
            collection=self.collection,
            version=self.version,
            image=self.image
        ))



    def tearDown(self):
        LOGGER.debug("Deleting local test image.")
        os.remove(self.image_path)
