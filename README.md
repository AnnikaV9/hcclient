<div align="left">
<h1> hcclient <br /> <a target="_blank" href="https://github.com/AnnikaV9/carrotsh/blob/master/LICENSE" title="License"><img src="https://img.shields.io/static/v1?label=License&message=The%20Unlicense&color=blue&style=flat-square"></a></h1>
A terminal client for connecting to <a href="https://hack.chat">hack.chat</a>

<br />
<br />

<img src="https://github.com/AnnikaV9/hcclient/assets/68383195/db0f13ab-b61a-4f42-b501-2175e792c443" width="80%"></div>

<br />

## Table of Contents
- [Introduction](#introduction)
- [Features](#features)
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

hcclient is a cross-platform terminal client for connecting to [hack.chat](https://hack.chat).

**Note:** &nbsp;As this client is written to be compatible with the official live instance running at https://hack.chat, compatibility with your own self-hosted instance or other alternate instances is not guaranteed.

<br />

## Features <a name="features"></a>
- **Color theming:** &nbsp;Configured with command line flags, colors provided by termcolor.
- **Suggestions:** &nbsp;Starting your message with `@` or `/` will bring up a menu with a list of online users or commands. Cycle through them with arrow keys or continue typing to filter the suggestions even more. Outside of the menu, arrow keys cycle through message history.
- **Patched stdout:** &nbsp;Type long messages as slow as you want, received messages won't overwrite your progress.
- **Config generation:** &nbsp;Generate and load json configuration files with no editing required. Change configuration options from within the client with commands, modifying behaviour and colors without having to restart it.
- **Desktop notifications:** &nbsp;Receive notifications whenever someone mentions you or sends you a whisper. (Not supported in container mode)
- **Aliases:** &nbsp;Set aliases for messages and phrases you send often, because why wouldn't you?
- **Whisper lock:** &nbsp;Lock the client with a command to send only whispers, preventing accidental information leaks.
- **Ignore list:** &nbsp;Message blocking using tripcodes and connection hashes.
- **Send/Receive raw packets:** &nbsp;Send json packets without parsing with `/raw`, display received packets as json with `--no-parse`.
- **Moderator mode:** &nbsp;Enabled with `--is-mod`, gives you a bunch of `/` commands for moderator actions.

<br />

## Prerequisites <a name="prerequisites"></a>
For x86_64 linux, statically and dynamically linked binaries are provided with the interpreter and dependencies bundled in.

On other platforms, python >= 3.10 and pip are required. <br />

A [Docker](https://docs.docker.com/engine/) / [Podman](https://github.com/containers/podman) compatible image is provided.

<br />

## Installation <a name="installation"></a>
On all platforms:
```
# Install the pip package
pip install hcclient

# Run hcclient
hcclient --help
```
On x86_64 linux:
```
# Download the latest binary
wget -O hcclient https://github.com/AnnikaV9/hcclient/releases/download/v1.8.3/hcclient-1.8.3-linux-x86-64

# Or the statically linked binary if the above one doesn't work
wget -O hcclient https://github.com/AnnikaV9/hcclient/releases/download/v1.8.3/hcclient-1.8.3-linux-x86-64-static

# Make the binary executable
chmod +x hcclient

# Move it to somewhere in PATH
mv hcclient ~/.local/bin/

# Run hcclient
hcclient --help
```
As a container:
```
# Download the latest image
wget https://github.com/AnnikaV9/hcclient/releases/download/v1.8.3/hcclient-1.8.3-image.tar.xz

# Install the image
docker/podman load -i hcclient-1.8.3-image.tar.xz

# Run hcclient
docker/podman run --rm -it hcclient --help
```
<br />

## Usage <a name="usage"></a>
```
$ hcclient --help

usage: hcclient [-h] -c CHANNEL -n NICKNAME [-t TRIP_PASSWORD]
                [-w WEBSOCKET_ADDRESS] [-l CONFIG_FILE] [--no-config] [--gen-config]
                [--no-parse] [--clear] [--is-mod] [--no-unicode] [--no-notify]
                [--prompt-string PROMPT_STRING] [--message-color MESSAGE_COLOR]
                [--whisper-color WHISPER_COLOR] [--emote-color EMOTE_COLOR]
                [--nickname-color NICKNAME_COLOR] [--warning-color WARNING_COLOR]
                [--server-color SERVER_COLOR] [--client-color CLIENT_COLOR]
                [--timestamp-color TIMESTAMP_COLOR]
                [--mod-nickname-color MOD_NICKNAME_COLOR]
                [--admin-nickname-color ADMIN_NICKNAME_COLOR] [--version]

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
  -l CONFIG_FILE, --load-config CONFIG_FILE
                        specify a config file to load
  --no-config           disables loading of the default config file
  --gen-config          generates a config file with provided arguments
  --no-parse            log received packets without parsing
  --clear               enables clearing of the terminal
  --is-mod              enables moderator commands
  --no-unicode          disables moderator/admin icon and unicode characters
                        in the UI
  --no-notify           disables desktop notifications
  --prompt-string PROMPT_STRING
                        sets the prompt string (default: '❯ ' or '> ' if
                        --no-unicode)
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
  --version             displays the version and exits
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
A configuration file can be generated with the provided arguments using `--gen-config` and loaded using `--load-config`. For example:

```
hcclient -c mychannel -n mynick -t mypassword --no-notify --timestamp-color red --gen-config
```
The above command will create *config.json* in the working directory, which can then be loaded with:
```
hcclient -c mychannel -n mynick --load-config <path_to_config.json>
```
hcclient searches for *config.json* in the following directories by default:
- **Windows:** &nbsp;%APPDATA%/hcclient
- **Other platforms:** &nbsp;$HOME/.config/hcclient

Things to note:
- The configuration file does not affect `channel` and `nickname`, which have to be specified as flags every time.
- Command-line arguments **do not** overwrite the configuration file's options. If a configuration file is loaded, all flags except for `--channel` and `--nickname` are discarded. Run with `--no-config` if you want to override the default configuration file.

<br />

You can also configure hcclient while it's running, without having to restart it. For example:
```
> /configset no_notify true
```
The changes will be applied live and lost once you exit the client, but you can save it to the configuration file with `/save`<br />
Configuration options can be listed with `/configdump`

**Note:** &nbsp; Values set by `/configset` and the configuration file are not checked. An invalid value will crash the client.

<br />

## Known Issues <a name="issues"></a>

- Not compatible with hack.chat's new `updateMessage` implementation. You won't be able to see the output of any bots that use `updateMessage` to display delayed/streamed output.

- Some terminal emulators will have locked scrolling when hcclient is run with `--clear`. This is an issue with how the terminal emulators interact with the alternate screen `tput smcup` invokes. There's no fix for this at the moment, so run hcclient without `--clear` if you want to be able to scroll.

<br />

## Contributing <a name="contributing"></a>

All contributions are welcome! :D

**Credits to everyone [here](https://github.com/AnnikaV9/hcclient/graphs/contributors)**
