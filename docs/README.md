<div align="left">
<h1> hcclient <br /> <a target="_blank" href="https://github.com/AnnikaV9/carrotsh/blob/master/LICENSE" title="License"><img src="https://img.shields.io/static/v1?label=License&message=The%20Unlicense&color=blue&"></a> <a target="_blank" href="https://pypi.org/project/hcclient" title="PyPI"><img src="https://img.shields.io/pypi/v/hcclient?label=PyPI&color=blue"></a> </h1>
A cross-platform terminal client for <a href="https://hack.chat">hack.chat</a>

<br />
<br />

![Demo](https://github.com/AnnikaV9/hcclient/assets/68383195/0945c900-362e-4c7a-9b85-c85e62ce9e96)

<br />

- [Introduction](#introduction)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Styling](#styling)
- [Configuration](#configuration)
- [Notifications](#notifications)
- [Updatable Messages](#updatable-messages)
- [Contributing](#contributing)

<br />

## Introduction <a name="introduction"></a>
*"hack.chat is a minimal, distraction-free, accountless, logless, disappearing chat service which is easily deployable as your own service."* - [hack.chat](https://github.com/hack-chat/main)

hcclient is a configurable and feature-rich cross-platform terminal client for connecting to [hack.chat](https://hack.chat), with markdown and syntax highlighting.

**Note:** This client is written to be compatible with the official live instance running at https://hack.chat. Compatibility with your own self-hosted instance or other alternate instances is not guaranteed.

<br />

## Features <a name="features"></a>
Some of the features hcclient has to offer:
- **Cross-platform:** Tested to work on Windows, Linux, macOS and Android. See [Prerequisites](#prerequisites) for more information.
- **Suggestions:** Starting your message with `@` or `/` will bring up a menu with a list of online users or commands. Cycle through them with arrow keys or continue typing to filter the suggestions even more. Suggestion aggressiveness can be set with `--suggest-aggr`.
- **Markdown:** Messages are parsed as markdown, with support for bold, italics, strikethrough, code blocks, links and images.
- **Syntax highlighting:** Code blocks in messages are highlighted with user specified languages or language guessing. See [Styling](#styling) for more information.
- **Configuration:** Generate and load YAML/JSON configuration files with no editing required. Change configuration options from within the client with commands, modifying behaviour and colors without having to restart. See [Configuration](#configuration) for more information.
- **Desktop notifications:** Receive notifications whenever someone mentions you or sends you a whisper. Android notifications are supported when running on [Termux](https://termux.dev/). See [Notifications](#notifications) for more information.
- **Aliases:** Set aliases for messages and phrases you send often, because why wouldn't you?
- **Whisper locking:** Lock the client with a command to send only whispers, preventing accidental information leaks.
- **Ignore list:** Message blocking using tripcodes and connection hashes.
- **Proxy support:** Connect through SOCKS4, SOCKS5 or HTTP proxies. Tested to work with Tor.

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
wget -O hcclient https://github.com/AnnikaV9/hcclient/releases/download/v1.16.0/hcclient-1.16.0-linux-x86-64

# Or the statically linked binary if the above one doesn't work
wget -O hcclient https://github.com/AnnikaV9/hcclient/releases/download/v1.16.0/hcclient-1.16.0-linux-x86-64-static

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
wget https://github.com/AnnikaV9/hcclient/releases/download/v1.16.0/hcclient-1.16.0-image.tar.xz

# Install the image
docker/podman load -i hcclient-1.16.0-image.tar.xz

# Run hcclient
docker/podman run --rm -it hcclient --help
```
<br />

## Usage <a name="usage"></a>
```
$ hcclient --help

usage: hcclient [-h] [-v] [--gen-config] [--defaults] [--colors]
                [--themes] [-c CHANNEL] [-n NICKNAME] [-p PASSWORD]
                [-w ADDRESS] [-l FILE] [--no-config] [--no-parse]
                [--clear] [--is-mod] [--no-unicode]
                [--highlight-theme THEME] [--no-markdown] [--no-notify]
                [--prompt-string STRING] [--timestamp-format FORMAT]
                [--suggest-aggr 0-3] [--proxy TYPE:HOST:PORT]

terminal client for hack.chat

commands:
  -h, --help                        display this help message
  -v, --version                     display version information
  --gen-config                      generate config file
  --defaults                        display default config values
  --colors                          display valid color values
  --themes                          display valid highlight themes

required arguments:
  -c CHANNEL, --channel CHANNEL     set channel to join
  -n NICKNAME, --nickname NICKNAME  set nickname to use

optional arguments:
  -p PASSWORD, --password PASSWORD  specify tripcode password
  -w ADDRESS, --websocket ADDRESS   specify alternate websocket
  -l FILE, --load-config FILE       specify config file to load
  --no-config                       ignore global config file
  --no-parse                        log received packets as JSON
  --clear                           clear console before joining
  --is-mod                          enable moderator commands
  --no-unicode                      disable unicode UI elements
  --highlight-theme THEME           set highlight theme
  --no-markdown                     disable markdown formatting
  --no-notify                       disable desktop notifications
  --prompt-string STRING            set custom prompt string
  --timestamp-format FORMAT         set timestamp format
  --suggest-aggr 0-3                set suggestion aggressiveness
  --proxy TYPE:HOST:PORT            specify proxy to use
```

<br />

## Styling <a name="styling"></a>
The default color scheme can be overidden with a configuration file. See [Configuration](#configuration) for more information.<br />
A list of valid colors can be viewed with `--colors`.

Syntax highlighting and markdown are enabled by default. They can be disabled with `--no-markdown` or `/configset no_markdown true`<br />
The markdown implementation supports bold, italics, strikethrough, code blocks, links and images.

Highlight themes can be listed with `--themes` and set with `--highlight-theme <theme_name>` or `/configset highlight_theme <theme_name>`<br />
The default theme is *monokai*.

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
- ~~Command-line arguments **do not** override the configuration file's options. If a configuration file is loaded, all flags except for `--channel` and `--nickname` are discarded. Run with `--no-config` if you want to override the default configuration file.~~
  Command-line arguments now **do** override the configuration file's options.

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

**Note:** Notifications are not supported in container mode.

<br />

## Updatable Messages <a name="updatable-messages"></a>

hack.chat has support for updatable messages, which allows editing previously sent messages on the official web client. This is usually used by bots to display streamed/delayed output.<br />
Since hcclient is a terminal client, editing messages that have been previously printed isn't possible.

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

**Note:** If `no_unicode` is enabled, the `⧗`, `✓` and `✗` icons will be replaced with `Updatable.ID:`, `Completed.ID:` and `Expired.ID:` respectively.


<br />

## Contributing <a name="contributing"></a>

All contributions are welcome! :D

Please read [CONTRIBUTING.md](../docs/CONTRIBUTING.md) before submitting a pull request.

**Credits to everyone [here](https://github.com/AnnikaV9/hcclient/graphs/contributors)**
