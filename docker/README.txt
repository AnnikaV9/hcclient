This directory is for building a Docker/Podman compatible image.



Run the provided `build.sh` script from the root of the project:

    $ ./scripts/build.sh container

This will build the image and tag it as `hcclient:latest`.
An xz compressed image tarball will also be exported to the `dist` directory.



To manually build the image, first copy the required files to the `src` directory:

    $ cp -r ../{src/hcclient,requirements.txt} src/

Then build the image:

    $ docker/podman build -t hcclient .

To export the image as a compressed tarball, run from the root of the project:

    $ docker/podman save --output dist/hcclient-image.tar hcclient
    $ xz --compress \
         --keep \
         --extreme \
         --threads=0 \
         -6 \
         -v -v \
         dist/hcclient-image.tar
