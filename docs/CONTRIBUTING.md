# Contributing

All contributions are welcome as long as they are in scope of the project, which is to provide a configurable, fully featured, and cross-platform terminal client for [hack.chat](https://hack.chat/). Pull requests that add features targetting other alternate hack.chat instances will not be entertained. Please fork the project for that.

Please note we have a [code of conduct](../docs/CODE_OF_CONDUCT.md), please follow it in all your interactions with the project.


## Contributing Guidelines

- Document functions and classes using [docstrings](https://www.python.org/dev/peps/pep-0257/)
- Keep the code cross-platform
- Do not increase the version number, this will be done before releases
- Do not modify [README.md](../docs/README.md), this will be done before releases
- If new dependencies are added, please specify them in [pyproject.toml](../pyproject.toml)
- If a new command is added, please add it to the help menu and completer

For major changes, please open an issue first to discuss what you would like to change.


## Using the repository version

To use the latest development version, clone the repository and build the project.<br />
The build script [build.sh](../scripts/build.sh) is provided for convenience for building wheels.

To build a wheel, run from the root of the project:
```bash
./scripts/build.sh
```
This will create a wheel in the `dist` directory.

Then create a virtual environment and install the wheel:
```bash
python -m venv venv
./venv/bin/pip install dist/*.whl
```

You can then run the client from the virtual environment:
```bash
./venv/bin/hcclient
```
