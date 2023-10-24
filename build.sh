#!/bin/bash
#
# Requires ldd and binutils

VERSION="1.7.3-git"

binaries() {
   for cmd in ldd objdump objcopy python3
   do
     if ! command -v $cmd &> /dev/null
     then
       echo "command '$cmd' not found"
       exit 1
     fi
   done

   python3 -m venv .venv &&
   source .venv/bin/activate &&

   python3 -m pip install -r requirements.txt &&
   python3 -m pip install pyinstaller staticx build hatchling &&

   python3 -m build &&

   pyinstaller --onefile \
               --clean \
               --name hcclient-$VERSION \
               hcclient/__main__.py &&

   staticx --strip dist/hcclient-$VERSION dist/hcclient-$VERSION-static
}

container() {
   if ! command -v xz &> /dev/null
   then
     echo "command 'xz' not found"
     exit 1
   fi

   if command -v podman &> /dev/null
   then
     podman build --tag hcclient . &&
     podman save --output dist/hcclient-$VERSION-image.tar hcclient
   elif command -v docker &> /dev/null
   then
     docker build --tag hcclient . &&
     docker save --output dist/hcclient-$VERSION-image.tar hcclient
   else
     echo "no container runtime found"
     exit 1
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
