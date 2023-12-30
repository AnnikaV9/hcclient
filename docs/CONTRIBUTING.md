# Contributing

All contributions are welcome as long as they are in scope of the project, which is to provide a configurable, fully featured, and cross-platform terminal client for [hack.chat](https://hack.chat/). Pull requests that add features targetting other alternate hack.chat instances will not be entertained. Please fork the project for that.

Note that we have a [code of conduct](../docs/CODE_OF_CONDUCT.md), please follow it in all your interactions with the project.


## Contributing Guidelines

- Document functions and classes using [docstrings](https://www.python.org/dev/peps/pep-0257/)
- Keep the code cross-platform
- Do not increase the version number, this will be done before releases
- Do not modify [README.md](../docs/README.md), this will be done before releases
- If new dependencies are added, please specify them in [pyproject.toml](../pyproject.toml) and update the [lock file](../poetry.lock) using `poetry update`

For major changes, please open an issue first to discuss what you would like to change.


## Development Setup

hcclient is a [poetry](https://python-poetry.org/) project.<br />
Make sure you have poetry installed before continuing.

Development environment setup:
```bash
# Clone the repository
git clone https://github.com/AnnikaV9/hcclient.git

# Change the working directory
cd hcclient

# Set up the project
poetry install -E latex

# Run hcclient
poetry run hcclient --help
```

To build a wheel and source distribution:
```bash
poetry build
```
Builds will be placed in the `dist` directory.
