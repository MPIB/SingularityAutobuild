""" Test the functions that work with recipes and images.

"""

import unittest
import os
import types
from subprocess import call
from singularity_builder.test import test_singularity_builder
from singularity_builder.singularity_builder import (
    Builder
)
from singularity_builder.image_recipe_tools import (
    image_in_sregistry,
    recipe_finder,
    image_pusher
)

RECIPE_FILE_PATH = test_singularity_builder.RECIPE_FILE_PATH
LOGGER = test_singularity_builder.LOGGER
MODULE_DIR = test_singularity_builder.MODULE_DIR


class TestImageInSRegistry(unittest.TestCase):
    """ Test the function to check, if an image already exists in the sregistry. """

    def setUp(self):
        os.environ['SREGISTRY_CLIENT'] = 'registry'
        self.builder = Builder(recipe_path=RECIPE_FILE_PATH, image_type='simg')
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
        self.assertEqual(_recipe, RECIPE_FILE_PATH)

class TestImagePusher(unittest.TestCase):
    """ Test the function to Push an image to an sregistry. """

    def setUp(self):
        os.environ['SREGISTRY_CLIENT'] = 'registry'
        _builder = Builder(recipe_path=RECIPE_FILE_PATH, image_type='simg')
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