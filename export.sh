#!/bin/sh

mkdir dist || exit

podman build --tag hcclient \
             --output type=tar,dest=dist/hcclient.tar \
             . || exit

xz --compress \
   --keep \
   --extreme \
   --threads=8 \
   -6 \
   -v -v \
   dist/hcclient.tar
