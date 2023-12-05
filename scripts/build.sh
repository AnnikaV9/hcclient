#!/bin/bash
#
# Requires ldd and binutils

VERSION="1.16.2-git"

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
     sed -i 's/-git//g' src/hcclient/__main__.py
   fi
   echo_bold " -> Setting version to $VERSION"

   if [[ "$CLEAN" ]]
   then
     echo_bold " -> Cleaning up previous builds"
     rm -rf .venv dist docker/src/hcclient docker/src/requirements.txt src/hcclient/__pycache__ *.spec build
   fi
}

executable() {
   echo_bold "==> Starting executable build"
   for cmd in ldd objdump objcopy python3
   do
     if ! command -v $cmd &> /dev/null
     then
       echo_bold " -> Error: Command '$cmd' not found"
       exit 1
     fi
   done

   echo_bold " -> Creating virtual environment and installing dependencies (FOR EXECUTABLE)"
   python3 -m venv .venv &&
   source .venv/bin/activate &&

   python3 -m pip --disable-pip-version-check --no-color --quiet install -r requirements.txt &&
   python3 -m pip --disable-pip-version-check --no-color --quiet install pyinstaller staticx &&

   echo_bold " -> Building dynamic executable"
   pyinstaller --onefile \
               --clean \
               --name hcclient-$VERSION \
               --log-level INFO \
               src/hcclient/__main__.py &&

   if [[ -z "$NO_STATIC" ]]
   then
     echo_bold " -> Creating static executable"
     staticx --loglevel INFO --strip dist/hcclient-$VERSION dist/hcclient-$VERSION-static
   fi
}

wheel() {
   echo_bold "==> Starting wheel build"
   if ! command -v python3 &> /dev/null
   then
     echo_bold " -> Error: Command 'python3' not found"
     exit 1
   fi

   echo_bold " -> Creating virtual environment and installing dependencies (FOR WHEEL)"
   python3 -m venv .venv &&
   source .venv/bin/activate &&

   python3 -m pip --disable-pip-version-check --no-color --quiet install poetry &&

   echo_bold " -> Building wheel"
   poetry --no-ansi -vv build
}

container() {
   echo_bold "==> Starting container build"
   if ! command -v xz &> /dev/null
   then
     echo_bold " -> Error: Command 'xz' not found"
     exit 1
   fi

   echo_bold " -> Building container image"
   cp -r {src/hcclient,requirements.txt} docker/src &&
   cd docker &&

   if command -v podman &> /dev/null
   then
     podman build --tag hcclient . &&
     cd .. &&
     podman save --output dist/hcclient-$VERSION-image.tar hcclient
   elif command -v docker &> /dev/null
   then
     docker build --tag hcclient . &&
     cd .. &&
     docker save --output dist/hcclient-$VERSION-image.tar hcclient
   else
     echo_bold " -> Error: No container runtime found"
     exit 1
   fi &&

   echo_bold " -> Compressing container image"
   xz --compress \
      --keep \
      --extreme \
      --threads=0 \
      -6 \
      -v -v \
      dist/hcclient-$VERSION-image.tar
}

arch() {
   echo_bold "==> Creating Arch source tarball"
   if ! command -v tar &> /dev/null
   then
     echo_bold " -> Error: Command 'tar' not found"
     exit 1
   fi

   cp LICENSE dist/LICENSE &&
   tar -czf dist/hcclient-$VERSION-arch.tar.gz -C dist hcclient-$VERSION LICENSE
   rm -f dist/LICENSE
}

case "$1" in
   executable) prepare && mkdir -p dist && executable ;;
   wheel) prepare && mkdir -p dist && wheel ;;
   container) prepare && mkdir -p dist && container ;;
   arch) prepare && mkdir -p dist && executable && arch ;;
   all) prepare && mkdir -p dist && executable && arch && wheel && container ;;
   *) echo_bold "Valid commands: executable, wheel, container, arch, all"; exit 1
esac
