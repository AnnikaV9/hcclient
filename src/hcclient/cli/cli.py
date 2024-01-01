# Author:    AnnikaV9
# License:   Unlicense

import sys
import argparse

import termcolor
import pygments.styles

from hcclient import meta
from hcclient.client.client import Client
from hcclient.utils.hook import load_hooks
from hcclient.utils.config import default_config, initialize_config


def main():
    """
    Entry point
    Parses cli arguments, loads config file, and runs the client
    """
    parser = argparse.ArgumentParser(description=meta.desc,
                                     add_help=False,
                                     formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=45))

    command_group = parser.add_argument_group("commands")
    required_group = parser.add_argument_group("required arguments")
    optional_group = parser.add_argument_group("optional arguments")

    command_group.add_argument("-h", "--help", help="display this help message", action="help")
    command_group.add_argument("-v", "--version", help="display version information", action="version", version=f"hcclient {meta.vers}")
    command_group.add_argument("--gen-config", help="generate config file", action="store_true")
    command_group.add_argument("--defaults", help="display default config values", action="store_true")
    command_group.add_argument("--colors", help="display valid color values", action="store_true")
    command_group.add_argument("--themes", help="display valid highlight themes", action="store_true")
    command_group.set_defaults(gen_config=False, colors=False)

    required_group.add_argument("-c", "--channel", help="set channel to join", metavar="CHANNEL")
    required_group.add_argument("-n", "--nickname", help="set nickname to use", metavar="NICKNAME")

    optional_group.add_argument("-p", "--password", help="specify tripcode password", dest="trip_password", metavar="PASSWORD", default=argparse.SUPPRESS)
    optional_group.add_argument("-t", "--trip-password", help=argparse.SUPPRESS, dest="trip_password", default=argparse.SUPPRESS)  # deprecated
    optional_group.add_argument("-w", "--websocket", help="specify alternate websocket", dest="websocket_address", metavar="ADDRESS", default=argparse.SUPPRESS)
    optional_group.add_argument("--websocket-address", help=argparse.SUPPRESS, dest="websocket_address", default=argparse.SUPPRESS)  # deprecated
    optional_group.add_argument("-l", "--load-config", help="specify config file to load", dest="config_file", metavar="FILE", default=None)
    optional_group.add_argument("--no-config", help="ignore global config file", action="store_true", default=False)
    optional_group.add_argument("--no-hooks", help="ignore global hooks", action="store_true", default=False)
    optional_group.add_argument("--no-parse", help="log received packets as JSON", action="store_true", default=argparse.SUPPRESS)
    optional_group.add_argument("--clear", help="clear console before joining", action="store_true", default=argparse.SUPPRESS)
    optional_group.add_argument("--is-mod", help="enable moderator commands", action="store_true", default=argparse.SUPPRESS)
    optional_group.add_argument("--no-unicode", help="disable unicode UI elements", action="store_true", default=argparse.SUPPRESS)
    optional_group.add_argument("--sheriff-badges", help="show stars beside mods/admins", action="store_true", default=argparse.SUPPRESS)
    optional_group.add_argument("--no-highlight", help=argparse.SUPPRESS, action="store_true", default=False)  # deprecated, doesn't do anything
    optional_group.add_argument("--highlight-theme", help="set highlight theme", metavar="THEME", default=argparse.SUPPRESS)
    optional_group.add_argument("--no-markdown", help="disable markdown formatting", action="store_true", default=argparse.SUPPRESS)
    optional_group.add_argument("--no-linkify", help="disable linkifying of urls", action="store_true", default=argparse.SUPPRESS)
    optional_group.add_argument("--backticks-bg", help="set backticks background color", type=int, metavar="0-255", default=argparse.SUPPRESS)
    optional_group.add_argument("--latex", help="enable LaTeX simplifying", action="store_true", default=argparse.SUPPRESS)
    optional_group.add_argument("--no-notify", help="disable desktop notifications", action="store_true", default=argparse.SUPPRESS)
    optional_group.add_argument("--prompt-string", help="set custom prompt string", metavar="STRING", default=argparse.SUPPRESS)
    optional_group.add_argument("--timestamp-format", help="set timestamp format", metavar="FORMAT", default=argparse.SUPPRESS)
    optional_group.add_argument("--suggest-aggr", help="set suggestion aggressiveness", type=int, metavar="0-3", default=argparse.SUPPRESS)
    optional_group.add_argument("--proxy", help="specify proxy to use", metavar="TYPE:HOST:PORT", default=argparse.SUPPRESS)
    optional_group.add_argument("--ssl-no-verify", help="disable SSL cert verification", action="store_true", default=argparse.SUPPRESS)

    args = parser.parse_args()

    del args.no_highlight  # deprecated

    if args.colors:
        print("Valid colors:\n" + "\n".join(f" - {color}" for color in termcolor.COLORS))
        sys.exit(0)

    if args.defaults:
        print("Default configuration:\n" + "\n".join(f" - {option}: {value}" for option, value in default_config.items()))
        sys.exit(0)

    if args.themes:
        print("Valid themes:\n" + "\n".join(f" - {theme}" for theme in pygments.styles.get_all_styles()))
        sys.exit(0)

    hook = not args.no_hooks
    del args.no_hooks  # we dont want to pass this to the client

    client = Client(initialize_config(args, parser))

    if hook:
        client = load_hooks(client)

    client.run(meta.vers)
