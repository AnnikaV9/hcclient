<div align="left">
<h1> hcclient <br /> <a target="_blank" href="https://github.com/AnnikaV9/carrotsh/blob/master/LICENSE" title="License"><img src="https://img.shields.io/static/v1?label=License&message=The%20Unlicense&color=blue&"></a> <a target="_blank" href="https://pypi.org/project/hcclient" title="PyPI"><img src="https://img.shields.io/pypi/v/hcclient?label=PyPI&color=blue"></a> </h1>
A cross-platform terminal client for <a href="https://hack.chat">hack.chat</a>

<br />
<br />

![Showcase GIF](https://github.com/AnnikaV9/hcclient/assets/68383195/fa7b28da-d24b-4267-9258-9de6ece0f2f6)

<br />

## Table of Contents
- [Introduction](#introduction)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Colors](#colors)
- [Configuration](#configuration)
- [Notifications](#notifications)
- [Updatable Messages](#updatable-messages)
- [Contributing](#contributing)

<br />

## Introduction <a name="introduction"></a>
*"hack.chat is a minimal, distraction-free, accountless, logless, disappearing chat service which is easily deployable as your own service."* - [hack.chat](https://github.com/hack-chat/main)

hcclient is a configurable and feature-rich cross-platform terminal client for connecting to [hack.chat](https://hack.chat).

**Note:** &nbsp;This client is written to be compatible with the official live instance running at https://hack.chat. Compatibility with your own self-hosted instance or other alternate instances is not guaranteed.

<br />

## Features <a name="features"></a>
Some of the features hcclient has to offer:
- **Cross-platform:** &nbsp;Tested to work on Windows, Linux, macOS and Android. See [Prerequisites](#prerequisites) for more information.
- **Suggestions:** &nbsp;Starting your message with `@` or `/` will bring up a menu with a list of online users or commands. Cycle through them with arrow keys or continue typing to filter the suggestions even more. Suggestion aggressiveness can be set with `--suggest-aggr`.
- **Configuration:** &nbsp;Generate and load YAML/JSON configuration files with no editing required. Change configuration options from within the client with commands, modifying behaviour and colors without having to restart. See [Configuration](#configuration) for more information.
- **Desktop notifications:** &nbsp;Receive notifications whenever someone mentions you or sends you a whisper. Android notifications are supported when running on [Termux](https://termux.dev/). See [Notifications](#notifications) for more information.
- **Aliases:** &nbsp;Set aliases for messages and phrases you send often, because why wouldn't you?
- **Whisper locking:** &nbsp;Lock the client with a command to send only whispers, preventing accidental information leaks.
- **Ignore list:** &nbsp;Message blocking using tripcodes and connection hashes.
- **Proxy support:** &nbsp;Connect through SOCKS4, SOCKS5 or HTTP proxies. Tested to work with Tor.

<br />

## Prerequisites <a name="prerequisites"></a>
The main requirement for any platform is a terminal emulator that supports ANSI escape sequences.

For x86_64 Linux, statically and dynamically linked binaries are provided with the interpreter and dependencies bundled in.

On other platforms, python >= 3.10 and pip are required. <br />

A [Docker](https://docs.docker.com/engine/) / [Podman](https://github.com/containers/podman) compatible image is provided.

<br />

## Installation <a name="installation"></a>
On all platforms:
```bash
# Install the pip package
pip install hcclient

# Run hcclient
hcclient --help
```
On Arch Linux, install the [source AUR package](https://aur.archlinux.org/packages/hcclient) or [binary AUR package](https://aur.archlinux.org/packages/hcclient-bin) with makepkg or an AUR helper.<br />
On other x86_64 Linux distributions:
```bash
# Download the latest binary
wget -O hcclient https://github.com/AnnikaV9/hcclient/releases/download/v1.14.1/hcclient-1.14.1-linux-x86-64

# Or the statically linked binary if the above one doesn't work
wget -O hcclient https://github.com/AnnikaV9/hcclient/releases/download/v1.14.1/hcclient-1.14.1-linux-x86-64-static

# Make the binary executable
chmod +x hcclient

# Move it to somewhere in PATH
mv hcclient $HOME/.local/bin/

# Run hcclient
hcclient --help
```
As a container:
```bash
# Download the latest image
wget https://github.com/AnnikaV9/hcclient/releases/download/v1.14.1/hcclient-1.14.1-image.tar.xz

# Install the image
docker/podman load -i hcclient-1.14.1-image.tar.xz

# Run hcclient
docker/podman run --rm -it hcclient --help
```
<br />

## Usage <a name="usage"></a>
```
$ hcclient --help

usage: hcclient [-h] [--gen-config] [--colors] [--version] [-c CHANNEL]
                [-n NICKNAME] [-t TRIP_PASSWORD] [-w WEBSOCKET_ADDRESS]
                [-l CONFIG_FILE] [--no-config] [--no-parse] [--clear]
                [--is-mod] [--no-unicode] [--no-notify]
                [--prompt-string PROMPT_STRING] [--suggest-aggr {0,1,2,3}]
                [--proxy PROXY]

terminal client for connecting to hack.chat

commands:
  -h, --help            display this help message
  --gen-config          generate a config file with provided arguments
  --colors              display a list of valid colors
  --version             display version information

required arguments:
  -c CHANNEL, --channel CHANNEL
                        specify the channel to join
  -n NICKNAME, --nickname NICKNAME
                        specify the nickname to use

optional arguments:
  -t TRIP_PASSWORD, --trip-password TRIP_PASSWORD
                        specify a tripcode password to use when joining
  -w WEBSOCKET_ADDRESS, --websocket-address WEBSOCKET_ADDRESS
                        specify the websocket address to connect to
                        (default: wss://hack-chat/chat-ws)
  -l CONFIG_FILE, --load-config CONFIG_FILE
                        specify a config file to load
  --no-config           disable loading of the default config file
  --no-parse            log received packets without parsing
  --clear               clear the terminal before joining
  --is-mod              enable moderator commands
  --no-unicode          disable unicode characters in ui elements
  --no-notify           disable desktop notifications
  --prompt-string PROMPT_STRING
                        set the prompt string (default: '❯ ' or '> ' if
                        --no-unicode)
  --timestamp-format TIMESTAMP_FORMAT
                        set the timestamp format (default: %H:%M)
  --suggest-aggr {0,1,2,3}
                        set the suggestion aggressiveness (default: 1)
  --proxy PROXY         specify a proxy to use (format: TYPE:HOST:PORT)
                        (default: None)
```

<br />

## Colors <a name="colors"></a>
The default color scheme can be overidden with a configuration file. See [Configuration](#configuration) for more information.<br />
A list of valid colors can be viewed with `--colors`.

```
$ hcclient --colors

Valid colors:
black
grey
red
green
yellow
blue
magenta
cyan
light_grey
dark_grey
light_red
light_green
light_yellow
light_blue
light_magenta
light_cyan
white
```

<br />

## Configuration <a name="configuration"></a>
A configuration file can be generated with the provided arguments using `--gen-config` and loaded using `--load-config`. For example:

```
hcclient --gen-config
```
The above command will create *config.yml* with default options in the working directory, which can then be loaded with:
```
hcclient -c mychannel -n mynick --load-config <path_to_config.yml>
```
Generated configuration files are in YAML format by default.<br />
Alternatively, a JSON configuration file can be generated by running `--gen-config` again in the same directory. Both formats can be loaded the same way.<br />

Override defaults when generating the configuration file by specifying options:
```
hcclient --no-notify --proxy socks5:127.0.0.1:9050 --gen-config
```

hcclient searches for *config.yml* or *config.json* in the following directories by default:
- **Windows:** &nbsp;%APPDATA%/hcclient
- **Other platforms:** &nbsp;$HOME/.config/hcclient

Things to note:
- The configuration file does not affect `channel` and `nickname`, which have to be specified as flags every time.
- Command-line arguments **do not** override the configuration file's options. If a configuration file is loaded, all flags except for `--channel` and `--nickname` are discarded. Run with `--no-config` if you want to override the default configuration file.

<br />

You can also configure hcclient while it's running, without having to restart it. For example:
```
> /configset no_notify true
```
The changes will be applied live and lost once you exit the client, but you can save it to the configuration file with `/save`<br />
Configuration options can be listed with `/configdump`

<br />

## Notifications <a name="notifications"></a>

Desktop notifications are enabled by default. They can be disabled with `--no-notify` or `/configset no_notify true`<br />

hcclient doesn't have a built-in audio file for sound alerts, so you'll have to provide your own.<br />
Place a wave file named *tone.wav* in the default config directory and it will be played when a notification is sent.

Default config directory location:
- **Windows:** &nbsp;%APPDATA%/hcclient
- **Other platforms:** &nbsp;$HOME/.config/hcclient

On Linux, libnotify and aplay are required for notifications to work.

On Android, notifications are supported when running on [Termux](https://termux.dev/).<br />
Install the [Termux:API](https://f-droid.org/en/packages/com.termux.api/) app and termux-api package and notifications will just work.

**Note:** &nbsp; Notifications are not supported in container mode.

<br />

## Updatable Messages <a name="updatable-messages"></a>

hack.chat has support for updatable messages, which allows editing previously sent messages on the official web client. This is usually used by bots to display streamed/delayed output.<br />
Since hcclient is a terminal client, editing messages that have been previously printed isn't possible.<br />
However, `updateMessage` events are still handled, just differently.

When an updatable message is received, it will be printed as per normal but with an unique identifier. For example:
```
23:06|jEuh/s| [⧗ 84263] [user] hi
```
Here, `84263` is the message identifier.

As the sender continues to update and edit the message, hcclient will track the changes in memory.<br />
Once the sender sends the `complete` status, the message will be printed again with the same identifier and all changes applied:
```
23:06|jEuh/s| [⧗ 84263] [user] hi
...
...
...
23:08|jEuh/s| [✓ 84263] [user] hi guys!
```
It's displayed as a new message, but it's actually the previous message, edited.

If no `complete` status is received in 3 minutes, the message will expire. All changes applied so far will be printed like normal, but with the `✗` icon instead.

**Note:** &nbsp; If `no_unicode` is enabled, the `⧗`, `✓` and `✗` icons will be replaced with `Updatable.ID:`, `Completed.ID:` and `Expired.ID:` respectively.


<br />

## Contributing <a name="contributing"></a>

All contributions are welcome! :D

Please read [CONTRIBUTING.md](../docs/CONTRIBUTING.md) before submitting a pull request.

**Credits to everyone [here](https://github.com/AnnikaV9/hcclient/graphs/contributors)**
