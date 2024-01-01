# Author:    AnnikaV9
# License:   Unlicense

import os
import sys
import json
import argparse

import yaml
import termcolor
import pygments.styles


default_config = {
    "trip_password": "",
    "websocket_address": "wss://hack.chat/chat-ws",
    "no_parse": False,
    "clear": False,
    "is_mod": False,
    "no_unicode": False,
    "sheriff_badges": False,
    "highlight_theme": "monokai",
    "no_markdown": False,
    "no_linkify": False,
    "backticks_bg": 238,
    "latex": False,
    "no_notify": False,
    "prompt_string": "default",
    "timestamp_format": "%H:%M",
    "suggest_aggr": 1,
    "proxy": False,
    "ssl_no_verify": False,
    "config_file": None,
    "message_color": "white",
    "whisper_color": "green",
    "emote_color": "green",
    "nickname_color": "blue",
    "self_nickname_color": "magenta",
    "warning_color": "yellow",
    "server_color": "green",
    "client_color": "green",
    "timestamp_color": "white",
    "mod_nickname_color": "cyan",
    "admin_nickname_color": "red",
    "ignored": {"trips": [], "hashes": []},
    "aliases": {},
}


def generate_config(config: dict) -> None:
    """
    Generates a config file from the specified arguments
    """
    config.pop("config_file")

    try:
        if not os.path.isfile("config.yml"):
            with open("config.yml", "x", encoding="utf8") as config_file:
                yaml.dump(config, config_file, sort_keys=False, default_flow_style=False)
                print("Configuration written to config.yml")

        else:
            with open("config.json", "x", encoding="utf8") as config_file:
                json.dump(config, config_file, indent=2)
                print("Configuration written to config.json")

    except Exception as e:
        sys.exit(f"{sys.argv[0]}: error: {e}")


def load_config(filepath: str) -> dict:
    """
    Loads a config file from the specified path
    """
    try:
        with open(filepath, "r", encoding="utf8") as config_file:
            if filepath.endswith(".json"):
                config = json.load(config_file)

            else:
                config = yaml.safe_load(config_file)

            unknown_args = []
            for option in config:
                if option not in ("trip_password", "websocket_address", "no_parse",
                                  "clear", "is_mod", "no_unicode", "no_markdown",
                                  "highlight_theme", "no_notify", "prompt_string",
                                  "timestamp_format", "message_color", "whisper_color",
                                  "emote_color", "nickname_color", "self_nickname_color",
                                  "warning_color", "server_color", "client_color",
                                  "timestamp_color", "mod_nickname_color", "suggest_aggr",
                                  "admin_nickname_color", "ignored", "aliases", "proxy", "latex",
                                  "backticks_bg", "ssl_no_verify", "no_linkify", "sheriff_badges",
                                  "no_highlight",  # deprecated
                                  ):
                    unknown_args.append(option)

            if len(unknown_args) > 0:
                raise ValueError(f"{filepath}: unknown option(s): {', '.join(unknown_args)}")

            return config

    except Exception as e:
        sys.exit(f"{sys.argv[0]}: error: {e}")


def initialize_config(args: argparse.Namespace, parser: argparse.ArgumentParser) -> dict:
    """
    Initializes the configuration and returns a dictionary
    """
    config = default_config
    args_dict = vars(args)

    if args.gen_config:
        for arg, value in args_dict.items():
            if arg in config:
                config[arg] = value

        config["aliases"] = {"example": "example"}
        config["ignored"] = {"trips": ["example"], "hashes": ["example"]}
        generate_config(config)
        sys.exit(0)

    if not args.channel or not args.nickname:
        parser.print_usage()
        sys.exit(f"{sys.argv[0]}: error: the following arguments are required: -c/--channel, -n/--nickname")

    if args.config_file:
        file_config = load_config(args.config_file)
        for option, value in file_config.items():
            config[option] = value

        for arg, value in args_dict.items():
            if arg in config:
                config[arg] = value

        config["nickname"] = args.nickname
        config["channel"] = args.channel
        config["config_file"] = args.config_file
        for option, value in config.items():
            if not validate_config(option, value):
                sys.exit(f"{sys.argv[0]}: error: invalid configuration value for option '{option}'")

    else:
        loaded_config = False

        if not args.no_config:
            def_config_dir = os.path.join(os.getenv("APPDATA"), "hcclient") if os.name == "nt" else os.path.join(os.getenv("HOME"), ".config", "hcclient")
            file_options = ("config.yml", "config.json")

            for config_file in file_options:
                if os.path.isfile(os.path.join(def_config_dir, config_file)):
                    def_config_file = os.path.join(def_config_dir, config_file)
                    file_config = load_config(def_config_file)
                    for option, value in file_config.items():
                        config[option] = value

                    for arg, value in args_dict.items():
                        if arg in config:
                            config[arg] = value

                    config["nickname"] = args.nickname
                    config["channel"] = args.channel
                    config["config_file"] = def_config_file
                    for option, value in config.items():
                        if not validate_config(option, value):
                            sys.exit(f"{sys.argv[0]}: error: invalid configuration value for option '{option}'")

                    loaded_config = True
                    break

        if not loaded_config:
            for arg, value in args_dict.items():
                if arg in config:
                    config[arg] = value

            config["nickname"] = args.nickname
            config["channel"] = args.channel
            for option, value in config.items():
                if not validate_config(option, value):
                    sys.exit(f"{sys.argv[0]}: error: invalid configuration value for option '{option}'")

    return config


def validate_config(option: str, value: str) -> bool:
    """
    Validates a configuration option and its value
    Returns True if valid, False if not
    """
    passed = True

    if option in ("timestamp_color", "client_color", "server_color", "nickname_color",
                  "self_nickname_color", "mod_nickname_color", "admin_nickname_color",
                  "message_color", "emote_color", "whisper_color", "warning_color"):
        passed = value in termcolor.COLORS

    elif option in ("no_unicode", "no_notify", "no_parse", "clear", "is_mod", "no_markdown",
                    "latex", "ssl_no_verify", "no_linkify", "sheriff_badges"):
        passed = isinstance(value, bool)

    elif option in ("websocket_address", "trip_password", "prompt_string", "timestamp_format"):
        passed = isinstance(value, str)

    elif option in ("aliases", "ignored"):
        if not isinstance(value, dict):
            passed = False

        else:
            match option:
                case "aliases":
                    for alias, replacement in value.items():
                        if not isinstance(alias, str) or not isinstance(replacement, str):
                            passed = False

                case "ignored":
                    if "trips" not in value or "hashes" not in value:
                        passed = False

                    if not isinstance(value["trips"], list) or not isinstance(value["hashes"], list):
                        passed = False

    elif option in ("suggest_aggr", "backticks_bg"):
        if not isinstance(value, int):
            passed = False

        else:
            match option:
                case "suggest_aggr":
                    passed = value in range(4)

                case "backticks_bg":
                    passed = value in range(256)

    elif option == "proxy":
        if value and not isinstance(value, str):
            passed = False

    elif option == "highlight_theme":
        passed = value in pygments.styles.get_all_styles()

    return passed
