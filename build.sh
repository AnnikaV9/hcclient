#!/bin/bash
#
# Requires ldd and binutils

VERSION="1.9.0-git"

prepare() {
   if [[ "$RELEASE_VERSION" ]]
   then
     VERSION=${VERSION%-git}
     sed -i 's/-git//g' hcclient/__main__.py
   fi
}

executable() {
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
   python3 -m pip install pyinstaller staticx &&

   pyinstaller --onefile \
               --clean \
               --name hcclient-$VERSION \
               hcclient/__main__.py &&

   staticx --strip dist/hcclient-$VERSION dist/hcclient-$VERSION-static
}

wheel() {
   if ! command -v python3 &> /dev/null
   then
     echo "command 'python3' not found"
     exit 1
   fi

   python3 -m venv .venv &&
   source .venv/bin/activate &&

   python3 -m pip install poetry &&
   poetry build
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
   executable) mkdir dist && prepare && executable ;;
   wheel) mkdir dist && prepare && wheel ;;
   container) mkdir dist && prepare && container ;;
   all) mkdir dist && prepare && executable && wheel && container ;;
   *) echo "valid commands: executable, wheel, container, all"; exit 1  ;;
esac
