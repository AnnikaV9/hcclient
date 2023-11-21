#!/bin/bash
#
# Requires ldd and binutils

VERSION="1.13.0-git"

prepare() {
   if [[ "$RELEASE_VERSION" ]]
   then
     VERSION=${VERSION%-git}
     sed -i 's/-git//g' src/hcclient/__main__.py
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
               src/hcclient/__main__.py &&

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

arch() {
   if ! command -v tar &> /dev/null
   then
     echo "command 'tar' not found"
     exit 1
   fi
   cp LICENSE dist/LICENSE &&
   tar -czvf dist/hcclient-$VERSION-arch.tar.gz -C dist hcclient-$VERSION LICENSE
}

case "$1" in
   executable) mkdir dist && prepare && executable ;;
   wheel) mkdir dist && prepare && wheel ;;
   container) mkdir dist && prepare && container ;;
   arch) mkdir dist && prepare && executable && arch ;;
   all) mkdir dist && prepare && executable && arch && wheel && container ;;
   *) echo "valid commands: executable, wheel, container, arch, all"; exit 1  ;;
esac
