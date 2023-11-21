# Contributing

All contributions are welcome as long as they are in scope of the project, which is to provide a configurable, fully featured, and cross-platform terminal client for [hack.chat](https://hack.chat/). Pull requests that add features targetting other alternate hack.chat instances will not be entertained. Please fork the project for that.

Please note we have a [code of conduct](../docs/CODE_OF_CONDUCT.md), please follow it in all your interactions with the project.


## Contributing Guidelines

- Keep all code in [\_\_main.py__](../src/hcclient/__main__.py)
- Document functions and classes using [docstrings](https://www.python.org/dev/peps/pep-0257/)
- Keep the code cross-platform
- Do not increase the version number, this will be done before releases
- Do not modify [README.md](../docs/README.md), this will be done before releases
- If new dependencies are added, please specify them in [requirements.txt](../requirements.txt) and [pyproject.toml](../pyproject.toml)
- If a new command is added, please add it to the help menu and completer

For major changes, please open an issue first to discuss what you would like to change.


## Building From Source

The build script [build.sh](../scripts/build.sh) is provided for building hcclient from source. It can build executables, wheels, and container images.

Building the container image requires Docker or Podman. Building the executables requires binutils and ldd.

To build all distribution formats, run:

```
./scripts/build.sh all
```

To build a specific distribution format, run:

```
./scripts/build.sh <format>
```

Where `<format>` is one of `executable`, `wheel`, `container` and `arch`.

Builds will be placed in the `dist` directory.