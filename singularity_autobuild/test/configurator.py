""" Unifies configuration for the unittest modules. """

import os
import configparser

# TODO change all occurences of this kind
TEST_BASE_PATH = os.path.abspath(os.path.dirname(__file__))

def configure_test_recipe(conf_file: str = TEST_BASE_PATH+'/test.cfg') -> configparser.ConfigParser:
    """ Returns a ConfigParser with config values.

    :param conf_file: Path to the config file.
    """
    _path_to_conf_file = os.path.abspath(conf_file)
    _config = configparser.ConfigParser()
    print(_path_to_conf_file)
    _config.read(filenames=_path_to_conf_file)
    _config['TEST_RECIPE']['base_path'] = TEST_BASE_PATH
    return _config
