""" Module for miscellaneous modules to work with sregistry. """

from subprocess import call

def image_in_sregistry(
        collection: str,
        version: str,
        image: str
    ) -> bool:
    """ Returns true if image of version exists in collection.

    Calls sregistry search and parses its output to
    determin if a specific container is already stored
    in the sregistry.
    :param collection: The name of the images/containers collection.
    :param version:    The version of the container.
    :param image:      The name of the container.
    """

    _exit_status = call([
        'sregistry',
        'search',
        "%s/%s:%s" % (collection, image, version)
    ])

    return bool(_exit_status == 0)
