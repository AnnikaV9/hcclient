<div align="center">
<h1> hcclient <br /> <a target="_blank" href="https://github.com/AnnikaV9/carrotsh/blob/master/LICENSE" title="License"><img src="https://img.shields.io/static/v1?label=License&message=The%20Unlicense&color=blue&style=flat-square"></a></h1>
A terminal client for connecting to <a href="https://hack.chat">hack.chat</a>

<br />
<br />

<img src="https://github.com/AnnikaV9/hcclient/assets/68383195/b0c692ed-2cc4-4bb9-a3cf-73d82039bdf3" width="70%"></div>

<br />

## Table of Contents
- [Introduction](#introduction)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Colors](#colors)
- [Configuration](#configuration)
- [Known Issues](#issues)
- [Contributing](#contributing)

<br />

## Introduction <a name="introduction"></a>
*"hack.chat is a minimal, distraction-free, accountless, logless, disappearing chat service which is easily deployable as your own service."* - [hack.chat](https://github.com/hack-chat/main)

hcclient is a configurable terminal client for connecting to [hack.chat](https://hack.chat). It's written in python, and run as a container. The Alpine docker image is used due to its minimal size.

As this client is written to be compatible with the official live instance running at https://hack.chat, compatibility with your own self-hosted instance or other alternate instances is not guaranteed.

<br />

## Prerequisites <a name="prerequisites"></a>
Either [Docker](https://docs.docker.com/engine/) or [Podman](https://github.com/containers/podman) is recommended. The container image is built with hcclient's dependencies.  
<br />
You *can* run the client directly without using a container, however:
- This requires python >= 3.10 and pip. <br />
- You'll have to install pip dependencies locally or in a virtual environment.<br />
- The `tput` command (provided by ncurses) is an optionally dependency that allows saving and restoring terminal contents.

<br />

## Installation <a name="installation"></a>

```
# Clone the repository
git clone https://github.com/AnnikaV9/hcclient.git

# Change the working directory
cd hcclient

# Build the image
docker/podman build -t hcclient .

# Run hcclient
docker/podman run --rm -it hcclient --help
```

<br />

## Usage <a name="usage"></a>
```
$ docker/podman run --rm -it hcclient --help

usage:  [-h] -c CHANNEL -n NICKNAME [-t TRIP_PASSWORD] [-w WEBSOCKET_ADDRESS]
        [--no-parse] [--no-clear] [--is-mod] [--no-icon]
        [--message-color MESSAGE_COLOR] [--whisper-color WHISPER_COLOR]
        [--emote-color EMOTE_COLOR] [--nickname-color NICKNAME_COLOR]
        [--warning-color WARNING_COLOR] [--server-color SERVER_COLOR]
        [--client-color CLIENT_COLOR] [--timestamp-color TIMESTAMP_COLOR]
        [--mod-nickname-color MOD_NICKNAME_COLOR]
        [--admin-nickname-color ADMIN_NICKNAME_COLOR]

Terminal client for connecting to hack.chat servers. Colors are provided by
termcolor.

options:
  -h, --help            show this help message and exit

required arguments:
  -c CHANNEL, --channel CHANNEL
                        specify the channel to join
  -n NICKNAME, --nickname NICKNAME
                        specify the nickname to use

optional arguments:
  -t TRIP_PASSWORD, --trip-password TRIP_PASSWORD
                        specify a tripcode password to use when joining
  -w WEBSOCKET_ADDRESS, --websocket-address WEBSOCKET_ADDRESS
                        specify the websocket address to connect to (default:
                        wss://hack-chat/chat-ws)
  --no-parse            log received packets without parsing
  --no-clear            disables clearing of the terminal
  --is-mod              enables moderator commands
  --no-icon             disables moderator/admin icon
  --message-color MESSAGE_COLOR
                        sets the message color (default: white)
  --whisper-color WHISPER_COLOR
                        sets the whisper color (default: green)
  --emote-color EMOTE_COLOR
                        sets the emote color (default: green)
  --nickname-color NICKNAME_COLOR
                        sets the nickname color (default: white)
  --warning-color WARNING_COLOR
                        sets the warning color (default: yellow)
  --server-color SERVER_COLOR
                        sets the server color (default: green)
  --client-color CLIENT_COLOR
                        sets the client color (default: green)
  --timestamp-color TIMESTAMP_COLOR
                        sets the timestamp color (default: white)
  --mod-nickname-color MOD_NICKNAME_COLOR
                        sets the moderator nickname color (default: cyan)
  --admin-nickname-color ADMIN_NICKNAME_COLOR
                        sets the admin nickname color (default: red)
```

<br />

## Colors <a name="colors"></a>
The default color scheme can be overidden by using arguments such as `--message-color` or `--timestamp-color`. More options can be viewed with `--help`. Colors are provided by [termcolor](https://pypi.org/project/termcolor/). Valid colors are:
- grey
- red
- green
- yellow
- blue
- magenta
- cyan
- white

<br />

## Configuration <a name="configuration"></a>
hcclient does not save to or read from any configuration file. It might be troublesome to have to type long passwords and colors every time you wish to connect. You can create a shell script to act as a profile and call hcclient with your preferred arguments. For example:

*profile1.sh*
```bash
#!/bin/bash
docker run --rm -it hcclient --trip-password mypassword \
                             --server-color red \
                             "$@"
```
or
```bash
#!/bin/bash
podman run --rm -it hcclient --trip-password mypassword \
                             --timestamp-color green \
                             --no-clear \
                             "$@"
```
The profile can then be used like:
```
bash profile1.sh -c mychannel -n mynick
```

<br />

## Known Issues <a name="issues"></a>

- Not compatible with hack.chat's new `updateMessage` implementation. You won't be able to see the output of any bots that use `updateMessage` to display delayed/streamed output.

- Some terminal emulators will have locked scrolling when hcclient is run without `--no-clear`. This is an issue with how the terminal emulators interact with the alternate screen `tput smcup` invokes. To fix this, run with `--no-clear`.

<br />

## Contributing <a name="contributing"></a>

All contributions are welcome! :D

**Credits to everyone [here](https://github.com/AnnikaV9/hcclient/graphs/contributors)**
