""" Unittests for the singularity_builder and the __main__ module.

This project is developed by using test driven design.
"""
import os
import types
import unittest
from unittest.mock import patch
from subprocess import call

from singularity_builder.singularity_builder import (
    Builder,
    image_pusher,
    recipe_finder
    )
from singularity_builder.__main__ import (
    arg_parser,
    main
)

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

class TestMain(unittest.TestCase):
    """ Test the main Function and its helpers """

    def setUp(self):
        if os.path.isfile(IMAGE_PATH):
            os.remove(IMAGE_PATH)

    def test_main(self):
        """ Test the main function that enables execution from command line. """
        main(
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
            _response = arg_parser()
            self.assertEqual(_response.path, SEARCH_PATH)
            self.assertEqual(_response.image_type, _image_type)