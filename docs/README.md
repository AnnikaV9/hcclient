# hcclient <br> [![badge](https://img.shields.io/badge/Python-%E2%89%A5_3.10-blue?logo=Python&logoColor=white&labelColor=343b42)](../docs/pyproject.toml) [![badge](https://img.shields.io/pypi/v/hcclient?label=PyPI&labelColor=343b42&color=blue&logo=pypi&logoColor=white)](https://pypi.org/project/hcclient/) [![badge](https://github.com/AnnikaV9/hcclient/actions/workflows/flake8.yml/badge.svg)](https://github.com/AnnikaV9/hcclient/actions/workflows/flake8.yml) [![badge](https://github.com/AnnikaV9/hcclient/actions/workflows/poetry.yml/badge.svg)](https://github.com/AnnikaV9/hcclient/actions/workflows/poetry.yml)
A cross-platform terminal client for [hack.chat](https://hack.chat) <br><br>

![Demo](https://github.com/AnnikaV9/hcclient/assets/68383195/4e42545b-803a-495d-8a09-23240afd1354)

<br>

- [Introduction](#introduction)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Styling](#styling)
- [LaTeX Simplification](#latex-simplification)
- [Configuration](#configuration)
- [Notifications](#notifications)
- [Updatable Messages](#updatable-messages)
- [Hooks](#hooks)
- [Contributing](#contributing)

<br>

## Introduction <a name="introduction"></a>
*"hack.chat is a minimal, distraction-free, accountless, logless, disappearing chat service which is easily deployable as your own service."* - [hack.chat](https://github.com/hack-chat/main)

hcclient is a configurable and feature-rich cross-platform terminal client for connecting to [hack.chat](https://hack.chat)

> [!IMPORTANT]
> This client is written to be compatible with the official live instance. Compatibility with your own self-hosted instance or other alternate instances is not guaranteed.

<br>

## Features <a name="features"></a>
Some of the features hcclient has to offer:
- **Cross-platform:** Tested to work on Windows, Linux, macOS and Android. See [Prerequisites](#prerequisites) for more information.
- **Suggestions:** Starting your message with `@` or `/` will bring up a menu with a list of online users or commands. Cycle through them with arrow keys or continue typing to filter the suggestions even more. Suggestion aggressiveness can be set with `--suggest-aggr`.
- **Markdown:** Messages are parsed as markdown, with support for bold, italics, strikethrough, code blocks, backticks, links and spec compliant escaping. See [Styling](#styling) for more information.
- **Syntax highlighting:** Code blocks in messages are highlighted with user specified languages or language guessing.
- **LaTeX simplification:** LaTeX expressions are parsed and converted to sympy expressions, which are more readable. See [LaTeX Simplification](#latex-simplification) for more information.
- **Configuration:** Generate and load YAML/JSON configuration files with no editing required. Change configuration options from within the client with commands, modifying behaviour and colors without having to restart. See [Configuration](#configuration) for more information.
- **Desktop notifications:** Receive notifications whenever someone mentions you or sends you a whisper. Android notifications are supported when running on [Termux](https://termux.dev/). See [Notifications](#notifications) for more information.
- **Aliases:** Set aliases for messages and phrases you send often, because why wouldn't you?
- **Whisper locking:** Lock the client with a command to send only whispers, preventing accidental information leaks.
- **Ignore list:** Message blocking using tripcodes and connection hashes.
- **Proxy support:** Connect through SOCKS4, SOCKS5 or HTTP proxies. Tested to work with Tor.

<br>

## Prerequisites <a name="prerequisites"></a>
- Python >= 3.10
- Pip
- An xterm-256color terminal emulator that supports ANSI escape sequences

Notification support requires different dependencies on different platforms, see [Notifications](#notifications) for more information.

<br>

## Installation <a name="installation"></a>
Cross-platform installation:
```bash
# Install the PyPI package
pip install hcclient

# Run hcclient
hcclient --help
```
For LaTeX support, install `hcclient[latex]` instead.

On Arch Linux (and most Arch-based distributions), install the [AUR package](https://aur.archlinux.org/packages/hcclient) with makepkg or an AUR helper. <br>
This will install an isolated environment with all dependencies in `/opt/hcclient`. <br>

Alternatively, install the LaTeX enabled [AUR package](https://aur.archlinux.org/packages/hcclient-latex).

<br>

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
  --no-hooks                        ignore global hooks
  --no-parse                        log received packets as JSON
  --clear                           clear console before joining
  --is-mod                          enable moderator commands
  --no-unicode                      disable unicode UI elements
  --sheriff-badges                  show stars beside mods/admins
  --highlight-theme THEME           set highlight theme
  --no-markdown                     disable markdown formatting
  --no-linkify                      disable linkifying of urls
  --backticks-bg 0-255              set backticks background color
  --latex                           enable LaTeX simplifying
  --no-notify                       disable desktop notifications
  --prompt-string STRING            set custom prompt string
  --timestamp-format FORMAT         set timestamp format
  --suggest-aggr 0-3                set suggestion aggressiveness
  --proxy TYPE:HOST:PORT            specify proxy to use
  --ssl-no-verify                   disable SSL cert verification
```

<br>

## Styling <a name="styling"></a>
The default color scheme can be overidden with a configuration file. See [Configuration](#configuration) for more information. <br>
A list of valid colors can be viewed with `--colors`.

Syntax highlighting and markdown are enabled by default. They can be disabled with `--no-markdown` or with the `no_markdown` option. <br>
The markdown implementation supports:
- **Bold:** `**bold**`
- **Italics:** `*italics*`
- **Bold-italics:** `***bold-italics***`
- **Strikethrough:** `~~strikethrough~~`
- **Code blocks:** (With syntax highlighting and language guessing)
  ````
  ```<lang>
  <code>
  ```
  ````
- **Backticks:** `` `backticks` ``
- **Links:**
  - `[link](https://example.com)`
  - `![image](https://example.com/image.png`
  - `<https://example.com>`
  - `<mailto:user@example.com`
  - `https://example.com`
  - `example.com`
- **Escaping:** `\*escaped*` (Spec compliant)

Highlight themes can be listed with `--themes` and set with `--highlight-theme` or with the `highlight_theme` option <br>
The default theme is *monokai*.

<br>

## LaTeX Simplification <a name="latex-simplification"></a>
LaTeX simplification is disabled by default. It can be enabled with `--latex` or with the `latex` option. <br>
When enabled, LaTeX expressions will be parsed and converted to sympy expressions, which are more readable. <br>

Expressions must be enclosed in `$` or `$$` for inline and block expressions respectively.<br>

For example, the following LaTeX expression:
```
$\frac{1}{2}$
```

Will be simplified and displayed as:
```
|latex: 1/2|
```

Conversion is done using [latex2sympy2](https://github.com/OrangeX4/latex2sympy).<br>
Not all LaTeX expressions are supported of course, but it's good enough for most use cases.

<br>

## Configuration <a name="configuration"></a>
A configuration file can be generated with the provided arguments using `--gen-config` and loaded using `--load-config`. For example:

```
hcclient --gen-config
```
The above command will create *config.yml* with default options in the working directory, which can then be loaded with:
```
hcclient -c mychannel -n mynick --load-config <path_to_config.yml>
```
Generated configuration files are in YAML format by default. <br>
Alternatively, a JSON configuration file can be generated by running `--gen-config` again in the same directory. Both formats can be loaded the same way. <br>

Override defaults when generating the configuration file by specifying options:
```
hcclient --no-notify --proxy socks5:127.0.0.1:9050 --gen-config
```

hcclient searches for *config.yml* or *config.json* in the following directories by default:
- **Windows:** &nbsp;%APPDATA%/hcclient
- **Other platforms:** &nbsp;$HOME/.config/hcclient

> [!NOTE]
> The configuration file does not affect `channel` and `nickname`, which have to be specified as flags every time.

<br>

You can also configure hcclient while it's running, without having to restart it. For example:
```
> /configset no_notify true
```
The changes will be applied live and lost once you exit the client, but you can save it to the configuration file with `/save` <br>
Configuration options can be listed with `/configdump`

<br>

## Notifications <a name="notifications"></a>
Desktop notifications are enabled by default. They can be disabled with `--no-notify` or with the `no_notify` option <br>

hcclient doesn't have a built-in audio file for sound alerts, so you'll have to provide your own. <br>
Place a wave file named *tone.wav* in the default config directory and it will be played when a notification is sent.

Default config directory location:
- **Windows:** &nbsp;%APPDATA%/hcclient
- **Other platforms:** &nbsp;$HOME/.config/hcclient

On Linux, libnotify and aplay are required for notifications to work.

On Android, notifications are supported when running on [Termux](https://termux.dev/). <br>
Install the [Termux:API](https://f-droid.org/en/packages/com.termux.api/) app and termux-api package and notifications will just work.

<br>

## Updatable Messages <a name="updatable-messages"></a>
hack.chat has support for updatable messages, which allows editing previously sent messages on the official web client. This is usually used by bots to display streamed/delayed output. <br>
Since hcclient is a terminal client, editing messages that have been previously printed isn't possible.

However, `updateMessage` events are still handled, just differently.

When an updatable message is received, it will be printed as per normal but with an unique identifier. For example:
```
23:06|jEuh/s| [⧗ 84263] [user] hi
```
Here, `84263` is the message identifier.

As the sender continues to update and edit the message, hcclient will track the changes in memory. <br>
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

> [!NOTE]
> If `no_unicode` is enabled, the `⧗`, `✓` and `✗` icons will be replaced with `Updatable.ID:`, `Completed.ID:` and `Expired.ID:` respectively.

<br>

## Hooks <a name="hooks"></a>
You can tweak hcclient's behaviour by placing hooks in the default hooks directory: <br>
- **Windows:** &nbsp;%APPDATA%/hcclient/hooks
- **Other platforms:** &nbsp;$HOME/.config/hcclient/hooks

Hooks are python scripts that are run on startup. <br>

A hook should have a `HookInfo` class and a `hook()` function. <br>
The `HookInfo` class should have the following attributes:
- `name`: The name of the hook.
- `description`: (Optional) A description of the hook.
- `version`: The version of the hook, must be a valid version string.
- `compat`: (Optional) A version specifier for the client version the hook is compatible with. See the [Packaging User Guide](https://packaging.python.org/en/latest/specifications/version-specifiers/#id4) for more information.
- Any other attributes you want to add, hcclient will ignore them.

The `hook()` function should take a single argument, which is the client instance. <br>
You can modify, add or remove the instance's attributes and methods to change its behaviour.

Example hooks can be found [here](../examples/hooks).

> [!WARNING]
> Hook support is experimental. hcclient is not stable and the API is subject to change, hooks may not work after an update.

<br>

## Contributing <a name="contributing"></a>
All contributions are welcome! :D

Please read [CONTRIBUTING.md](../docs/CONTRIBUTING.md) before submitting a pull request.

**Credits to everyone [here](https://github.com/AnnikaV9/hcclient/graphs/contributors)**
