# Contributing

All contributions are welcome as long as they are in scope of the project, which is to provide a configurable, fully featured, and cross-platform terminal client for [hack.chat](https://hack.chat/).

Please note we have a [code of conduct](CODE_OF_CONDUCT.md), please follow it in all your interactions with the project.


## Contributing Guidelines

- Keep everything in `__main__.py`
- Keep the code cross-platform
- Do not increase the version number, this will be done before releases
- Do not modify `README.md`, this will be done before releases
- If new dependencies are added, please specify them in `requirements.txt`
- If a new command is added, please add it to the help menu and completer

For major changes, please open an issue first to discuss what you would like to change.


## Building From Source

The build script [build.sh](build.sh) is provided for building hcclient from source. It can build executables, wheels, and container images.

Building the container image requires Docker or Podman. Building the executables requires binutils and ldd.

To build all distribution formats, run:

```
./build.sh all
```

To build a specific distribution format, run:

```
./build.sh <format>
```

Where `<format>` is one of `executable`, `wheel`, or `container`.