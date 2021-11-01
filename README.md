# hcclient
A terminal client for connecting to [hack.chat](https://github.com/hack-chat/main) servers.



## Setup & Usage

```
git clone https://github.com/AnnikaV9/hcclient.git
cd hcclient
pip3 install -r requirements.txt
python3 hcclient --help
```



## Docker Image

From Docker Hub:

```
docker pull annikav9/hcclient
docker run --rm -it annikav9/hcclient --help
```


Building locally:

```
git clone https://github.com/AnnikaV9/hcclient.git
cd hcclient
docker build -t hcclient .
docker run --rm -it hcclient --help
```



## Colors
The default color scheme can be overidden by using arguments such as `--message-color` or `--timestamp-color`. More options can be viewed with `--help`. Colors are provided by [termcolor](https://pypi.org/project/termcolor/). Valid colors are:
- grey
- red
- green
- yellow
- blue
- magenta
- cyan
- white



## Configuration
By default, hcclient does not save to or read from any configuration file. It might be troublesome to have to type long passwords and colors every time you wish to connect. This can be solved by creating a bash script to call hcclient with your preferred arguments. Example:

*hcclient.sh*
```bash
#!/bin/bash

python3 hcclient --trip-password mypassword \
                 --message-color yellow \
                 --no-clear \
                 "$@"
```
or
```bash
#!/bin/bash
docker run --rm -it annikav9/hcclient --trip-password mypassword \
                                      --server-color red \
                                      "$@"
```
The script can then be run like:
```
./hcclient.sh -c mychannel -n mynick
```



## Todo
- Add mod/admin commands that can be enabled with flags (eg. `--is-mod`)
