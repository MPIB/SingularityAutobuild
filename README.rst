=====================================================================
Singularity Autobuilder
=====================================================================

The Singularity Autobuilder is intended to automate the building process of a collection of
Singularity recipes. It is, as of jet, intended to be started in a GitLab CI/CD Pipeline.

Dependencies
------------

Singularity Autobuilder depends on the python packages:
 - `GitPython` to determine changes
   of recipes contained in a local git repository.
 - `iso8601` to convert date-strings from a GitLab API into date objects.
 - `requests` to make calls to the GitLab v3 API.
 - `typing` to write python3 type hints. 

It furthermore needs an installation of Singularity itself and
an installation of the Singularity Registry Client.

Singularity
~~~~~~~~~~~

To build images, **Singularity** itself needs to be installed.
It runs natively on linux and there exists an official
`linux installation guide <https://singularity.lbl.gov/install-linux>`_.

Mac OSX and Windows user need to
run Singularity in a virtualized linux environment.
There are official guides to setup a Vagrant box wit Singularity:

 - `Mac OSX Singularity Vagrant guide <https://singularity.lbl.gov/install-mac>`_
 - `Windows Singularity Vagrant guide <https://singularity.lbl.gov/install-windows>`_

Singularity itself must be run with root privileges in order to build images,
meaning that the Autobuilder needs to be run with root privileges.

For information about singularity itself visit the
`GitHub-repository of singularity <https://github.com/singularityware/singularity>`_
or the
`official documentation of singularity <https://singularity.lbl.gov/>`_.

Singularity Registry Client
~~~~~~~~~~~~~~~~~~~~~~~~~~~

To interact with an sregistry,
the **Singularity global client** has to be installed and set up as
Singularity Registry Client.

`Singularity Global Client installation and user
Guide <https://singularityhub.github.io/sregistry-cli/client-registry>`_

The client is able to work with local and external storage.
The default behavior for the client is to work with local storage.
For the client to enable its functionality to work with an sregistry,
the environment variable `SREGISTRY_CLIENT` has to be set like so:

.. code:: bash

    export SREGISTRY_CLIENT=registry

To authenticate the sregistry-client against an sregistry and to
set the registries hostname an sregistry secrets file is needed.
The secrets file is a json file containing the following:

.. code:: json

    {
        "registry": {
            "token": "authentication_token",
            "username": "sregistry_user",
            "base": "https://myregistry.com"
        }
    }

Your sregistry instance can generate this file for every user with the
correct privileges. To set up a user, that is able to push images,
first `set up a user able to administrate the sregistry
<https://singularityhub.github.io/sregistry/setup#create-accounts>`_.
Then follow the instructions given by the `credentials guide page
<https://singularityhub.github.io/sregistry/credentials.html>`_

The sregistry expects the credentials file at $HOME/.sregistry.
The location can be changed by defining a different path in the
`SREGISTRY_CLIENT_SECRETS` environment variable.

For further information about the sregisty client see:
 - `Documentation for the client <https://singularityhub.github.io/sregistry-cli/>`_
 - `Tutorial for the client working with a registry <https://singularityhub.github.io/sregistry-cli/client-registry>`_


Installation from Git Repository
--------------------------------

Clone latest stable version of the Repository:

.. code:: bash

    git clone -b v0.1.0 https://github.com/MPIB/SingularityAutobuild.git

Install with pip:

.. code:: bash

    cd SingularityAutobuild
    pip install [--user] .

Usage
-----

The Autobuild process was designed to work in a GitLab CI/CD Pipeline.
It expects several environment variables to be set. Those variables
are intended to be set by creating Secret variables in the GitLab
CI/CD settings.

Variables to be set are:

 - GITLAB_API_STRING: The GitLAb API-v3-URL for the events of the repository
   containing the recipes.
 - GITLAB_API_TOKEN: The authentication token for the GitLab API.

The autobuild process uses the GitLab API information to only build
recipes that have changed during the latest push to the repository.
The process will fail, if the variable is not set or if there is no API
to call (if the recipes in general are not hosted on a GitLab instance).

Running without GitLab CI/CD
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If the GitLab variables are set and
Singularity and the sregistry client are set up,
the autobuild process can be started through its entry-point:

.. code:: bash

    singularity_autobuild --path /path/to/recipe/base/folder --image_type IMAGE_TYPE

Running with GitLab CI/CD
~~~~~~~~~~~~~~~~~~~~~~~~~

The docker image `hansend/sregistry-builder:Autobuilder-0.1.0
<https://hub.docker.com/r/hansend/sregistry-builder/>`_
builds upon the `python:3.7-rc-stretch <https://hub.docker.com/_/python/>`_
image and has Singularity,
the sregistry client and the Autobuilder already installed.
It can be used in a GitLab CI/CD pipeline.
The container is also set up to build an .sregistry
file to identify the sregistry client against the registry.
For this to work the environment variable

 - `SREGISTRY_HOSTNAME`: Host address of the sregistry
 - `SREGISTRY_USERNAME`: Name of the sregistry user
 - `SREGISTRY_TOKEN`: Authentication token of the user,
   found in the sregistry admin interface or in the users .sregistry file.

have to be set.
The best way to set the variables is through the secret variables
in the GitLab CI/CD settings.

The following is a .gitlab-ci.yml pipeline config
that creates a `.sregistry` file in the `before_script`
section of the build_image job.

.. code:: yaml

    image:
      name: hansend/sregistry-builder:Autobuilder-0.1.0

    build_images:
      stage: deploy
    # Create the .sregistry file to authenticate the user at the sregistry.
      before_script:
       - "source /sregistry_file"
       - "echo $SREGISTRY_USERNAME"
       - "echo $SREGISTRY_FILE > ~/.sregistry"
      script:
       - singularity_autobuild --path ./recipes --image_type simg


Testing
-------

Test the main Builder Class and the \_\_main\_\_ module:

.. code:: bash

    python -m unittest -v singularity_autobuild.test.test_singularity_builder

Test the module, that provides functionality
to work with the GitLab repository.

.. code:: bash

    python -m unittest -v singularity_autobuild.test.test_gitlab_tools

Test the module, that provides functionality
to work with recipe files and created images.

.. code:: bash

    python -m unittest -v singularity_autobuild.test.test_image_recipe_tools

Full Documentation
------------------

`GiHub Pages <https://mpib.github.io/SingularityAutobuild/>`_
