#!/bin/sh

mkdir dist &&

podman build --tag hcclient . &&
podman save --output dist/hcclient.tar &&


xz --compress \
   --keep \
   --extreme \
   --threads=8 \
   -6 \
   -v -v \
   dist/hcclient.tar
