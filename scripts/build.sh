#!/bin/bash

VERSION="1.18.3-git"

echo_bold() {
  if [[ "$NO_ANSI" ]]
  then
    echo -e "$1"
  else
    echo -e "\033[1m$1\033[0m"
  fi
}

prepare() {
   echo_bold "==> Running pre-build checks"
   if [[ "$RELEASE_VERSION" ]]
   then
     VERSION=${VERSION%-git}
     sed -i "s/-git//g" src/hcclient/__main__.py \
                        src/hcclient/client.py \
                        src/hcclient/config.py \
                        src/hcclient/formatter.py \
                        src/hcclient/hook.py
   fi
   echo_bold "  -> Setting version to $VERSION"

   if [[ "$CLEAN" ]]
   then
     echo_bold "  -> Cleaning up previous builds"
     rm -rf .venv dist docker/wheel/*.whl src/hcclient/__pycache__
   fi
}

build() {
   echo_bold "==> Starting wheel build"
   if ! command -v python3 &> /dev/null
   then
     echo_bold "  -> Error: Command 'python3' not found"
     exit 1
   fi

   echo_bold "  -> Creating virtual environment and installing dependencies (FOR WHEEL)"
   python3 -m venv .venv &&
   ./.venv/bin/pip --disable-pip-version-check --no-color --quiet install poetry &&

   echo_bold "  -> Building wheel"
   ./.venv/bin/poetry --no-ansi -vv build
}

main() {
   prepare &&
   build
}

main
