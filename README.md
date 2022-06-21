# hcclient <br /> <a target="_blank" href="https://github.com/AnnikaV9/carrotsh/blob/master/LICENSE" title="License"><img src="https://img.shields.io/static/v1?label=License&message=The%20Unlicense&color=blue&style=flat-square"></a>
A terminal client for connecting to [hack.chat](https://github.com/hack-chat/main) servers.

<br />

## Installation

```
# Clone the repository
git clone https://github.com/AnnikaV9/hcclient.git

# Change the working directory
cd hcclient

# Build the image
docker build -t annikav9/hcclient .

# Or with Podman
podman build -t annikav9/hcclient .

# Run hcclient
docker run --rm -it annikav9/hcclient --help

# Or with Podman
podman run --rm -it annikav9/hcclient --help
```

<br />

## Usage
```
$ docker run --rm -it annikav9/hcclient --help
$ podman run --rm -it annikav9/hcclient --help

usage:  [-h] -c CHANNEL -n NICKNAME [-t TRIP_PASSWORD] [-w WEBSOCKET_ADDRESS]
        [--no-parse] [--no-clear] [--is-mod] [--message-color MESSAGE_COLOR]
        [--whisper-color WHISPER_COLOR] [--emote-color EMOTE_COLOR]
        [--nickname-color NICKNAME_COLOR] [--warning-color WARNING_COLOR]
        [--server-color SERVER_COLOR] [--client-color CLIENT_COLOR]
        [--timestamp-color TIMESTAMP_COLOR] [--mod-nickname-color MOD_NICKNAME_COLOR]
        [--admin-nickname-color ADMIN_NICKNAME_COLOR]

Terminal client for connecting to hack.chat servers. Colors are provided by termcolor.

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
  --no-clear            disables terminal clearing when joining a new channel
  --is-mod              enables moderator commands
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

<br />

## Configuration
By default, hcclient does not save to or read from any configuration file. It might be troublesome to have to type long passwords and colors every time you wish to connect. This can be solved by creating a bash script to call hcclient with your preferred arguments. Examples:

*hcclient.sh*
```bash
#!/bin/bash
docker run --rm -it annikav9/hcclient --trip-password mypassword \
                                      --server-color red \
                                      "$@"
```
or
```bash
#!/bin/bash
podman run --rm -it annikav9/hcclient --trip-password mypassword \
                                      --timestamp-color green \
                                      --no-clear \
                                      "$@"
```
The script can then be run like:
```
./hcclient.sh -c mychannel -n mynick
```
