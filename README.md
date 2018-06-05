# Singularity Autobuilder

This project is intended to automate the building process of a collection of
Singularity recipes.

## Singularity

[Singularity itself must be installed](https://singularity.lbl.gov/install-linux)
to enable building of singularity images.

For information about singularity itself visit the
[GitHub-repository of singularity](https://github.com/singularityware/singularity)
or the
[official documentation of singularity](https://singularity.lbl.gov/).

## sregistry

[sregistry-cli must be installed](https://github.com/singularityhub/sregistry-cli)
to be able to interact with an sregistry.
The sregistry is able to work with local and external storage.
The default behavior for the client is to work with local storage.
To enable the client to work with an sregistry the environment variable
`SREGISTRY_CLIENT=registry` must be set.

## sregistry credentials

To authenticate the sregistry-client against an sregistry and to
set the registries hostname an sregistry secrets file is needed.
The secrets file is a json file containing the following:

``` json
{
    "registry": {
        "token": "authentication_token",
        "username": "sregistry_user",
        "base": "https://myregistry.com"
    }
}
```

The sregistry expects this file at $HOME/.sregistry.
The location can be changed by defining a different path in the
`SREGISTRY_CLIENT_SECRETS` environment variable.

For further information about the sregisty client see the
[documentation for the client](https://singularityhub.github.io/sregistry-cli/).

## Installation

TODO

## Testing

TODO

## Full Documentation

TODO