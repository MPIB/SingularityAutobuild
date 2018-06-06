""" Test the functions that work with recipes and images.

"""

import unittest
import os
import types
import re
from subprocess import call
from singularity_autobuild.autobuild_logger import get_stdout_logger
from singularity_autobuild.singularity_builder import (
    Builder
)
from singularity_autobuild.test.configurator import configure_test_recipe
from singularity_autobuild.image_recipe_tools import (
    get_image_name_from_recipe,
    get_version_from_recipe,
    get_collection_from_recipe_path,
    image_in_sregistry,
    recipe_finder,
    image_pusher,
    dependency_resolver,
    dependency_drill_down,
    get_dependency_from_recipe,
    recipe_list_sanity_check,
    get_path_from_dependency,
    is_own_dependency
)

LOGGER = get_stdout_logger()

RECIPE_CONF = configure_test_recipe()['TEST_RECIPE']

RECIPE_FILE_PATH = RECIPE_CONF['recipe_file_path']
COLLECTION = RECIPE_CONF['collection_name']
MODULE_DIR = os.path.abspath(os.path.dirname(__file__))


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

    RECIPE_GRANDPARENT_FOLDER = MODULE_DIR

    def test_exceptions(self):
        """ Test if specified exceptions are raised. """
        with self.assertRaises(OSError):
            next(recipe_finder(path=os.path.abspath(__file__)))

    def test_recipe_finder(self):
        """ Test if recipes can be found and returned as expected. """
        _finder = recipe_finder(self.RECIPE_GRANDPARENT_FOLDER)
        self.assertIsInstance(_finder, types.GeneratorType)
        _recipe = next(_finder)
        self.assertEqual(_recipe, RECIPE_FILE_PATH)

class TestImagePusher(unittest.TestCase):
    """ Test the function to Push an image to an sregistry. """

    image_path = ''
    collection = ''
    version = ''
    image = ''

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

class TestInfoFromRecipe(unittest.TestCase):
    """Test the functions to return collection, image version and name given a recipe."""

    TEST_IMAGE_NAME = 'test_recipe'
    TEST_VERSIONED_RECIPE_NAME = TEST_IMAGE_NAME+'.%s.recipe'
    TEST_RECIPE_NAME = TEST_IMAGE_NAME+'.recipe'

    def test_get_coll_from_recipe_path(self):
        """Test the function to return the collection name given a recipes full path."""
        _test_collection_name = 'collection_test'
        _test_collection_full_path = '/test/' + _test_collection_name
        _recipe_file_name = self.TEST_VERSIONED_RECIPE_NAME % '1.0'
        _recipe_path = '%s/%s' % (
            _test_collection_full_path,
            _recipe_file_name
        )
        self.assertEqual(
            _test_collection_name,
            get_collection_from_recipe_path(
                recipe_file_full_path=_recipe_path
            )
        )


    def test_get_version_from_recipe(self):
        """Test the function to return image version given a recipe name."""
        _recipe_version = '1.0'
        _recipe_with_version = self.TEST_VERSIONED_RECIPE_NAME % (_recipe_version)
        _recipe_latest = self.TEST_RECIPE_NAME

        self.assertEqual(
            _recipe_version,
            get_version_from_recipe(recipe_file_name=_recipe_with_version)
        )
        self.assertEqual(
            'latest',
            get_version_from_recipe(recipe_file_name=_recipe_latest)
        )

    def test_get_image_name_from_recipe(self):
        """Test the function to return image name given a recipe name."""
        _recipe_file_name = self.TEST_VERSIONED_RECIPE_NAME % "1.0"
        _image_name = self.TEST_IMAGE_NAME

        self.assertEqual(
            _image_name,
            get_image_name_from_recipe(recipe_file_name=_recipe_file_name)
            )

class TestDependencyResolver(unittest.TestCase):
    """ Test the function, that sorts a list of recipe files on their dependencies. """

    def setUp(self):
        self.main_recipe = RECIPE_FILE_PATH
        # Recipe containing folder
        _recipe_folder_path = os.path.dirname(self.main_recipe)
        # Just its filename
        _recipe_file_name = os.path.basename(self.main_recipe)
        # Name of the image it creates
        _image_name = get_image_name_from_recipe(_recipe_file_name)
        # Version of the image it creates
        _image_version = get_version_from_recipe(_recipe_file_name)
        # Collection of the image it creates
        _collection = get_collection_from_recipe_path(self.main_recipe)
        # The Base folder for all recipes
        self.recipe_base_folder_path = os.path.dirname(
            os.path.dirname(RECIPE_FILE_PATH)
        )

        _sregistry_host_name_raw = os.environ['SREGISTRY_HOSTNAME']
        # Strip protocol part from the hostname
        _host_name = re.sub(r'^http[s]?:\/\/(.*)$', r'\1', _sregistry_host_name_raw)

        _child_version = float(1.0)
        _child_name = "test_dependency"
        self.child_dependency_file = "%s/%s.%s.recipe" % (
            _recipe_folder_path,
            _child_name,
            str(_child_version)
        )
        self.child_dependency = "%s/%s/%s:%s" % (
            _host_name,
            _collection,
            _image_name,
            _image_version
        )
        self.child_of_child_dependency_file = "%s/%s.%s.recipe" %(
            _recipe_folder_path,
            _child_name,
            str(_child_version+0.1)
        )
        self.child_of_child_dependency = "%s/%s/%s:%s" % (
            _host_name,
            _collection,
            _child_name,
            _child_version
        )
        # Set up mock recipes.
        # One that depends on the main recipe and
        # one that depends on the first.
        self.dependency_files = {
            self.child_dependency_file:
            "BOOTSTRAP: shub\nFROM: %s" % self.child_dependency,
            self.child_of_child_dependency_file:
            "BOOTSTRAP: shub\nFROM: %s" % self.child_of_child_dependency
        }

        # Create mock recipes.
        for filename in self.dependency_files:
            with open(filename, 'w') as file:
                file.write(self.dependency_files[filename])

    def test_get_dependency_from_recipe(self):
        """ Test the function, that reads the dependency from a recipes header. """
        _test_dependency = get_dependency_from_recipe(self.main_recipe)
        if 'shub' in _test_dependency:
            self.fail(msg='Dependency was read wrong')
        _test_dependency = get_dependency_from_recipe(self.child_dependency_file)
        self.assertIn('shub', _test_dependency)
        self.assertEqual(_test_dependency['shub'], self.child_dependency)

    def test_get_path_from_dependency(self):
        """ Test the function to get the recipe path from a dependency. """
        # Test for parent of first child
        _expected_file_path = self.main_recipe
        _test_file_path = get_path_from_dependency(
            recipe_dependency_value=self.child_dependency,
            recipe_base_folder_path=self.recipe_base_folder_path
        )
        self.assertEqual(_expected_file_path, _test_file_path)
        # Test for parent of child of child
        _expected_file_path = self.child_dependency_file
        _test_file_path = get_path_from_dependency(
            recipe_dependency_value=self.child_of_child_dependency,
            recipe_base_folder_path=self.recipe_base_folder_path
        )
        self.assertEqual(_expected_file_path, _test_file_path)

    def test_is_own_dependency(self):
        """ Test the function that checks if dependency is to a private sregistry."""
        self.assertFalse(is_own_dependency("collection/container:version"))
        self.assertTrue(is_own_dependency)

    def test_recipe_list_sanity_check(self):
        """ Test the function that finds recipes that would create images with the same name. """
        _sane_list = [
            "/path/to/project/collection/recipe_name.1.0.recipe",
            "/path/to/project/collection_two/recipe_name.1.0.recipe"
        ]
        _not_sane_list = [
            "/path/to/project/collection/recipe_name.1.0.recipe",
            "/path/to/project/subfolder/collection/recipe_name.1.0.recipe"
        ]

        try:
            self.assertIsNone(recipe_list_sanity_check(_sane_list))
        except RuntimeError:
            self.fail(msg="%s should not fail on a sane list." % str(recipe_list_sanity_check))

        with self.assertRaises(RuntimeError):
            recipe_list_sanity_check(recipe_file_paths=_not_sane_list)

    def test_dependency_resolver(self):
        """ Test the function that orders a list on recipe dependencies. """
        _unordered_recipe_list = [
            self.child_of_child_dependency_file,
            self.main_recipe,
            self.child_dependency_file
        ]
        _ordered_recipe_list = [
            self.main_recipe,
            self.child_dependency_file,
            self.child_of_child_dependency_file
        ]
        _test_list = dependency_resolver(
            recipe_file_paths=_unordered_recipe_list,
            recipe_base_path=self.recipe_base_folder_path)

        self.assertEqual(_test_list, _ordered_recipe_list)

    def test_dependency_drill_down(self):
        """ Test the function that follows a single dependency chain. """
        _expected_dict = {
            self.main_recipe: 0,
            self.child_dependency_file: 1,
            self.child_of_child_dependency_file: 2
        }
        # Set up dict without any work done.
        _test_dependency_dict = {
        }
        dependency_drill_down(
            dependency_dict=_test_dependency_dict,
            recipe_path=self.child_of_child_dependency_file,
            recipe_base_path=self.recipe_base_folder_path
        )
        # Test function for dict without any work done.
        self.assertEqual(
            _expected_dict,
            _test_dependency_dict
        )
        # Set up dict with some work done.
        _test_dependency_dict = {
            self.main_recipe: 0,
            self.child_dependency_file: 1,
        }
        dependency_drill_down(
            dependency_dict=_test_dependency_dict,
            recipe_path=self.child_of_child_dependency_file,
            recipe_base_path=self.recipe_base_folder_path
        )
        # Test function for dict with some work done.
        self.assertEqual(
            _expected_dict,
            _test_dependency_dict
        )


    def tearDown(self):
        for filename in self.dependency_files:
            os.remove(filename)
