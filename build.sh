#!/bin/bash
#
# Requires ldd and binutils

VERSION="1.3.3"

binaries() {
   python3 -m venv .venv &&
   source .venv/bin/activate &&

   pip install -r requirements.txt &&
   pip install pyinstaller staticx &&

   pyinstaller --onefile \
               --clean \
               --name hcclient-$VERSION \
               hcclient/__main__.py &&
   staticx --strip dist/hcclient-$VERSION dist/hcclient-$VERSION-static
}

container() {
   if [ -x "$(command -v podman)" ]; then
      podman build --tag hcclient . &&
      podman save --output dist/hcclient-$VERSION-image.tar hcclient
   elif [ -x "$(command -v docker)" ]; then
      docker build --tag hcclient . &&
      docker save --output dist/hcclient-$VERSION-image.tar hcclient
   else
      echo "no container runtime found"; exit 1
   fi &&

   xz --compress \
      --keep \
      --extreme \
      --threads=0 \
      -6 \
      -v -v \
      dist/hcclient-$VERSION-image.tar
}

case "$1" in
    binaries) mkdir dist && binaries ;;
    container) mkdir dist && container ;;
    all) mkdir dist && binaries && container ;;
    *) echo "commands: binaries, container, all"; exit 1  ;;
esac
