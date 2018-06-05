.. Singularity Builder documentation master file, created by
   sphinx-quickstart on Mon Mar 26 10:01:36 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Singularity Builder's documentation
===============================================

The modules of this package need to be able to execute
`singularity` and `sregistry` and need to be executed by a user,
that has an .sregistry file in the home directory.
The .sregistry file needs to enable the user to have admin and superuser access
to the sregistry-server. The builder itself also needs root privileges, since
building of singularity images requires root privileges.
For further information look at the sregistry clients documentation:
`sregistry-cli <https://singularityhub.github.io/sregistry/credentials>`_

Recipes are supposed to conform to the naming schema:

.. code::

    {containername}.{versionstring}.recipe

The name of a recipes parent folder will be used to set
the name for the collection it will be added to in the sregistry.

Regular logging in this module is done to stdout,
to be directly visible in a GitLab CI/CD jobs log.
Singularity build output is piped into a file in a
separate folder, created relative to the location of this module.
The Folder is intended to be defined as a "pipeline
artifact" in GitLab CI/CD.

Contents:

.. toctree::
   :maxdepth: 2
   :glob:

   modules/*
   tests/*





Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

