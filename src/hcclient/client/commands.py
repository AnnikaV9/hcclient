# Author:    AnnikaV9
# License:   Unlicense

import re
import os
import sys
import json
import copy
import shutil
import threading
import contextlib
import subprocess

import yaml
import termcolor

from hcclient.utils.config import validate_config


class ClientCommands:
    """
    Client commands that are managed by the client, and added to the prompt session's completer
    """
    def show_help(client: object, args_string: str) -> None:
        if args_string == "":
            help_text = """
Keybindings:
  enter     send
  ctrl+n    add newline
  ctrl+u    clear line
  ctrl+l    clear buffer
  ctrl+c    clear buffer, exit on second press

Client commands:
  /help [server-based command]
    Displays this help message if no command is
    specified, otherwise displays information
    about the specified server-based command.
  /raw <json>
    Sends json directly to the server without
    parsing.
  /list
    Lists users in the channel.
  /profile <nick>
    Prints a user's details.
  /clear
    Clears the terminal.
  /wlock
    Toggles whisper lock, which will prevent
    sending any messages other than whispers.
  /nick <newnick>
    Changes your nickname.
  /ignore <nick>
    Adds a user's trip and hash to the ignore
    list.
  /unignoreall
    Clears the ignore list.
  /reconnect
    Disconnects forcefully and reconnects to
    the server.
  /set <alias> <value>
    Sets an alias. $alias will be replaced with
    the value in your messages.
  /unset <alias>
    Unsets an alias.
  /configset <option> <value>
    Sets a configuration option to a value.
    Changed values will be in effect immediately.
  /configdump
    Prints the current configuration.
  /save
    Saves the current configuration to the loaded
    configuration file. Will save aliases and
    ignored trips/hashes.
  /reprint
    Prints the last 100 lines of output, even if
    they have been cleared with /clear.
  /exec <code>
    Executes python code in the context of the
    client, similar to a browser's dev console.
  /cat <file>
    Prints the contents of a file to stdout.
    (For captcha purposes)
  /quit
    Exits the client."""
            mod_help_text = """\n
Moderator commands:
  /ban <nick> [nick2] [nick3]...
  /unban <hash> [hash2] [hash3]...
  /unbanall
  /dumb <nick> [nick2] [nick3]...
  /speak <nick> [nick2] [nick3]...
  /moveuser <nick> <channel>
  /kick <nick> [nick2] [nick3]...
  /kickasone <nick> [nick2] [nick3]...
  /overflow <nick> [nick2] [nick3]...
  /authtrip <trip> [trip2] [trip3]...
  /deauthtrip <trip> [trip2] [trip3]...
  /enablecaptcha
  /disablecaptcha
  /lockroom
  /unlockroom
  /forcecolor <nick> <color>
  /anticmd
  /uwuify <nick> [nick2] [nick3]..."""
            footer_text = "\n\nRun `/help server` to read the server help text."
            display = help_text + mod_help_text + footer_text if client.args["is_mod"] else help_text + footer_text

            if shutil.which("less") and os.name != "nt":
                display = display.replace("Keybindings", termcolor.colored("Keybindings", attrs=["bold"]))
                display = display.replace("Client commands", termcolor.colored("Client commands", attrs=["bold"]))
                display = display.replace("Moderator commands", termcolor.colored("Moderator commands", attrs=["bold"]))

                with subprocess.Popen(["less", "-R"], stdin=subprocess.PIPE, errors="backslashreplace") as pager_proc:
                    try:
                        with pager_proc.stdin as pipe:
                            pipe.write(termcolor.colored(":q to return to the chat \n", "black", "on_white", attrs=["bold"]) + display)

                    except OSError:
                        pass

                    pager_proc.wait()

            else:
                client.print_msg("{}|{}| {}".format(termcolor.colored(client.formatted_datetime(), client.args["timestamp_color"]),
                                                    termcolor.colored("CLIENT", client.args["client_color"]),
                                                    termcolor.colored(f"Help text:{display}", client.args["client_color"])))

        else:
            if args_string == "server":
                client.send({"cmd": "help"})

            else:
                client.send({"cmd": "help", "command": args_string})

    def raw(client: object, args_string: str) -> None:
        try:
            client.send(json.loads(args_string))

        except Exception as e:
            client.print_msg("{}|{}| {}".format(termcolor.colored(client.formatted_datetime(), client.args["timestamp_color"]),
                                                termcolor.colored("CLIENT", client.args["client_color"]),
                                                termcolor.colored(f"Error sending json: {e}", client.args["client_color"])))

    def list_users(client: object, args_string: str) -> None:
        client.print_msg("{}|{}| {}".format(termcolor.colored(client.formatted_datetime(), client.args["timestamp_color"]),
                                            termcolor.colored("CLIENT", client.args["client_color"]),
                                            termcolor.colored(f"Channel: {client.channel} - Users: {', '.join(client.online_users)}", client.args["client_color"])))

    def profile(client: object, args_string: str) -> None:
        target = args_string.lstrip("@")
        if target in client.online_users:
            ignored = "Yes" if target in client.online_ignored_users else "No"
            profile = f"{target}'s profile:\n" + "\n".join(f"{option}: {value}" for option, value in client.online_users_details[target].items()) + f"\nIgnored: {ignored}"
            client.print_msg("{}|{}| {}".format(termcolor.colored(client.formatted_datetime(), client.args["timestamp_color"]),
                                                termcolor.colored("CLIENT", client.args["client_color"]),
                                                termcolor.colored(profile, client.args["client_color"])))

        else:
            client.print_msg("{}|{}| {}".format(termcolor.colored(client.formatted_datetime(), client.args["timestamp_color"]),
                                                termcolor.colored("CLIENT", client.args["client_color"]),
                                                termcolor.colored(f"No such user: '{target}'", client.args["client_color"])))

    def nick(client: object, args_string: str) -> None:
        if re.match("^[A-Za-z0-9_]*$", args_string) and 0 < len(args_string) < 25:
            if client.ws.connected:
                client.send({"cmd": "changenick", "nick": args_string})

            client.nick = args_string
            client.args["nickname"] = args_string

        else:
            client.print_msg("{}|{}| {}".format(termcolor.colored(client.formatted_datetime(), client.args["timestamp_color"]),
                                                termcolor.colored("CLIENT", client.args["client_color"]),
                                                termcolor.colored("Nickname must consist of up to 24 letters, numbers, and underscores", client.args["client_color"])))

    def clear(client: object, args_string: str) -> None:
        os.system("cls" if os.name == "nt" else "clear")
        client.print_msg("{}|{}| {}".format(termcolor.colored(client.formatted_datetime(), client.args["timestamp_color"]),
                                            termcolor.colored("CLIENT", client.args["client_color"]),
                                            termcolor.colored("Console cleared, run `/reprint` to undo", client.args["client_color"])), hist=False)

    def wlock(client: object, args_string: str) -> None:
        client.whisper_lock = not client.whisper_lock
        client.print_msg("{}|{}| {}".format(termcolor.colored(client.formatted_datetime(), client.args["timestamp_color"]),
                                            termcolor.colored("CLIENT", client.args["client_color"]),
                                            termcolor.colored(f"Toggled whisper lock to {client.whisper_lock}", client.args["client_color"])))

    def ignore(client: object, args_string: str) -> None:
        target = args_string.lstrip("@")
        if target in client.online_users:
            client.online_ignored_users.append(target)
            target_trip = client.online_users_details[target]["Trip"]
            target_hash = client.online_users_details[target]["Hash"]

            if target_trip not in client.args["ignored"]["trips"] and target_trip is not None:
                client.args["ignored"]["trips"].append(target_trip)

            if target_hash not in client.args["ignored"]["hashes"]:
                client.args["ignored"]["hashes"].append(target_hash)

            return_msg = f"Ignoring trip '{target_trip}' and hash '{target_hash}'" if target_trip is not None else f"Ignoring hash '{target_hash}'"
            return_msg += ", run `/save` to persist"

            client.print_msg("{}|{}| {}".format(termcolor.colored(client.formatted_datetime(), client.args["timestamp_color"]),
                                                termcolor.colored("CLIENT", client.args["client_color"]),
                                                termcolor.colored(return_msg, client.args["client_color"])))

        else:
            client.print_msg("{}|{}| {}".format(termcolor.colored(client.formatted_datetime(), client.args["timestamp_color"]),
                                                termcolor.colored("CLIENT", client.args["client_color"]),
                                                termcolor.colored(f"No such user: '{target}'", client.args["client_color"])))

    def unignoreall(client: object, args_string: str) -> None:
        client.online_ignored_users = []
        client.args["ignored"] = {"trips": [], "hashes": []}
        client.print_msg("{}|{}| {}".format(termcolor.colored(client.formatted_datetime(), client.args["timestamp_color"]),
                                            termcolor.colored("CLIENT", client.args["client_color"]),
                                            termcolor.colored("Unignored all trips/hashes, run `/save` to persist", client.args["client_color"])))

    def reconnect(client: object, args_string: str) -> None:
        client.timed_reconnect.cancel()
        threading.Thread(target=client.reconnect_to_server, daemon=True).start()

    def set_alias(client: object, args_string: str) -> None:
        args = args_string.split(" ")
        if len(args) < 2:
            client.print_msg("{}|{}| {}".format(termcolor.colored(client.formatted_datetime(), client.args["timestamp_color"]),
                                                termcolor.colored("CLIENT", client.args["client_color"]),
                                                termcolor.colored("Alias/Value cannot be empty", client.args["client_color"])))

        else:
            client.args["aliases"][args[0]] = " ".join(args[1:])
            client.print_msg("{}|{}| {}".format(termcolor.colored(client.formatted_datetime(), client.args["timestamp_color"]),
                                                termcolor.colored("CLIENT", client.args["client_color"]),
                                                termcolor.colored(f"Set alias '{args[0]}' = '{client.args['aliases'][args[0]]}'", client.args["client_color"])))

    def unset_alias(client: object, args_string: str) -> None:
        try:
            client.args["aliases"].pop(args_string)
            client.print_msg("{}|{}| {}".format(termcolor.colored(client.formatted_datetime(), client.args["timestamp_color"]),
                                                termcolor.colored("CLIENT", client.args["client_color"]),
                                                termcolor.colored(f"Unset alias '{args_string}'", client.args["client_color"])))

        except KeyError:
            client.print_msg("{}|{}| {}".format(termcolor.colored(client.formatted_datetime(), client.args["timestamp_color"]),
                                                termcolor.colored("CLIENT", client.args["client_color"]),
                                                termcolor.colored(f"Alias '{args_string}' isn't defined", client.args["client_color"])))

    def configset(client: object, args_string: str) -> None:
        args = args_string.split(" ")
        value, option = " ".join(args[1:]), args[0].lower()

        if option in client.args and option not in ("config_file", "channel", "nickname", "aliases", "ignored"):
            match value.lower():
                case "false":
                    value = False

                case "true":
                    value = True

                case "none" | "null":
                    value = None

            if option in ("suggest_aggr", "backticks_bg"):
                with contextlib.suppress(ValueError):
                    value = int(value)

            if validate_config(option, value):
                client.args[option] = value
                client.manage_complete_list()
                client.prompt_session.completer = client.create_completer()
                client.print_msg("{}|{}| {}".format(termcolor.colored(client.formatted_datetime(), client.args["timestamp_color"]),
                                                    termcolor.colored("CLIENT", client.args["client_color"]),
                                                    termcolor.colored(f"Set configuration option '{option}' to '{value}'", client.args["client_color"])))

                if option == "latex" and value and "latex2sympy2" not in sys.modules:
                    try:
                        import latex2sympy2
                        client.formatter.latex2sympy = latex2sympy2
                        client.print_msg("{}|{}| {}".format(termcolor.colored(client.formatted_datetime(), client.args["timestamp_color"]),
                                                            termcolor.colored("CLIENT", client.args["client_color"]),
                                                            termcolor.colored("Warning: You have enabled LaTeX simplifying", client.args["client_color"])))
                        client.print_msg("{}|{}| {}".format(termcolor.colored(client.formatted_datetime(), client.args["timestamp_color"]),
                                                            termcolor.colored("CLIENT", client.args["client_color"]),
                                                            termcolor.colored("Idle memory usage will increase significantly", client.args["client_color"])))

                    except ImportError:
                        client.args["latex"] = False
                        client.print_msg("{}|{}| {}".format(termcolor.colored(client.formatted_datetime(), client.args["timestamp_color"]),
                                                            termcolor.colored("CLIENT", client.args["client_color"]),
                                                            termcolor.colored("Error enabling LaTeX simplifying, optional dependencies not installed", client.args["client_color"])))
                        client.print_msg("{}|{}| {}".format(termcolor.colored(client.formatted_datetime(), client.args["timestamp_color"]),
                                                            termcolor.colored("CLIENT", client.args["client_color"]),
                                                            termcolor.colored("Packages that provide missing dependencies: PyPI: hcclient[latex], AUR: hcclient-latex", client.args["client_color"])))

            else:
                client.print_msg("{}|{}| {}".format(termcolor.colored(client.formatted_datetime(), client.args["timestamp_color"]),
                                                    termcolor.colored("CLIENT", client.args["client_color"]),
                                                    termcolor.colored(f"Error setting configuration: Invalid value '{value}' for option '{option}'", client.args["client_color"])))

        else:
            problem = "Invalid" if option not in client.args else "Read-only"
            client.print_msg("{}|{}| {}".format(termcolor.colored(client.formatted_datetime(), client.args["timestamp_color"]),
                                                termcolor.colored("CLIENT", client.args["client_color"]),
                                                termcolor.colored(f"Error setting configuration: {problem} option '{option}'", client.args["client_color"])))

    def configdump(client: object, args_string: str) -> None:
        client.print_msg("{}|{}| {}".format(termcolor.colored(client.formatted_datetime(), client.args["timestamp_color"]),
                                            termcolor.colored("CLIENT", client.args["client_color"]),
                                            termcolor.colored("Active configuration:\n" + "\n".join(f"{option}: {value}" for option, value in client.args.items()), client.args["client_color"])))

    def save(client: object, args_string: str) -> None:
        if client.args["config_file"]:
            config = copy.deepcopy(client.args)
            for arg in ("config_file", "channel", "nickname"):
                config.pop(arg)

            try:
                with open(client.args["config_file"], "w", encoding="utf8") as config_file:
                    if client.args["config_file"].endswith(".json"):
                        json.dump(config, config_file, indent=2)

                    else:
                        yaml.dump(config, config_file, sort_keys=False, default_flow_style=False)

                    client.print_msg("{}|{}| {}".format(termcolor.colored(client.formatted_datetime(), client.args["timestamp_color"]),
                                                        termcolor.colored("CLIENT", client.args["client_color"]),
                                                        termcolor.colored(f"Configuration saved to {client.args['config_file']}", client.args["client_color"])))

            except Exception as e:
                client.print_msg("{}|{}| {}".format(termcolor.colored(client.formatted_datetime(), client.args["timestamp_color"]),
                                                    termcolor.colored("CLIENT", client.args["client_color"]),
                                                    termcolor.colored(f"Error saving configuration: {e}", client.args["client_color"])))

        else:
            client.print_msg("{}|{}| {}".format(termcolor.colored(client.formatted_datetime(), client.args["timestamp_color"]),
                                                termcolor.colored("CLIENT", client.args["client_color"]),
                                                termcolor.colored("Unable to save configuration without a loaded config file", client.args["client_color"])))
            client.print_msg("{}|{}| {}".format(termcolor.colored(client.formatted_datetime(), client.args["timestamp_color"]),
                                                termcolor.colored("CLIENT", client.args["client_color"]),
                                                termcolor.colored(f"Load a config file with `--load-config` or place `config.yml` in {client.def_config_dir}", client.args["client_color"])))

    def reprint(client: object, args_string: str) -> None:
        client.print_msg("{}|{}| {}".format(termcolor.colored(client.formatted_datetime(), client.args["timestamp_color"]),
                                            termcolor.colored("CLIENT", client.args["client_color"]),
                                            termcolor.colored(f"Re-printing {len(client.stdout_history)} messages...", client.args["client_color"])), hist=False)
        print("\n".join(client.stdout_history))

    def dev_exec(client: object, args_string: str) -> None:
        try:
            exec(args_string)

        except Exception as e:
            module = e.__class__.__module__
            full_name = e.__class__.__name__ if module is None or module == str.__class__.__module__ else f"{module}.{e.__class__.__name__}"

            client.print_msg("{}|{}| {}".format(termcolor.colored(client.formatted_datetime(), client.args["timestamp_color"]),
                                                termcolor.colored("CLIENT", client.args["client_color"]),
                                                termcolor.colored(f"Exec exception ({full_name}): {e}", client.args["client_color"])))

    def cat(client: object, args_string: str) -> None:
        try:
            with open(args_string, "r", encoding="utf8") as file:
                print(file.read())

        except Exception as e:
            client.print_msg("{}|{}| {}".format(termcolor.colored(client.formatted_datetime(), client.args["timestamp_color"]),
                                                termcolor.colored("CLIENT", client.args["client_color"]),
                                                termcolor.colored(f"Error reading file: {e}", client.args["client_color"])))

    def quit_client(client: object, args_string: str) -> None:
        raise SystemExit

    def ban(client: object, args_string: str) -> None:
        [client.send({"cmd": "ban", "nick": user.lstrip("@")}) for user in args_string.split(" ")]

    def unban(client: object, args_string: str) -> None:
        [client.send({"cmd": "unban", "hash": uhash}) for uhash in args_string.split(" ")]

    def unbanall(client: object, args_string: str) -> None:
        client.send({"cmd": "unbanall"})

    def dumb(client: object, args_string: str) -> None:
        [client.send({"cmd": "dumb", "nick": user.lstrip("@")}) for user in args_string.split(" ")]

    def speak(client: object, args_string: str) -> None:
        [client.send({"cmd": "speak", "nick": user.lstrip("@")}) for user in args_string.split(" ")]

    def moveuser(client: object, args_string: str) -> None:
        args = args_string.split(" ")
        if len(args) > 1:
            client.send({"cmd": "moveuser", "nick": args[0].lstrip("@"), "channel": args[1]})

        else:
            client.print_msg("{}|{}| {}".format(termcolor.colored(client.formatted_datetime(), client.args["timestamp_color"]),
                                                termcolor.colored("CLIENT", client.args["client_color"]),
                                                termcolor.colored("User/Channel cannot be empty", client.args["client_color"])))

    def kick(client: object, args_string: str) -> None:
        [client.send({"cmd": "kick", "nick": user.lstrip("@")}) for user in args_string.split(" ")]

    def kickasone(client: object, args_string: str) -> None:
        client.send({"cmd": "kick", "nick": [user.lstrip("@") for user in args_string.split(" ")]})

    def overflow(client: object, args_string: str) -> None:
        [client.send({"cmd": "overflow", "nick": user.lstrip("@")}) for user in args_string.split(" ")]

    def authtrip(client: object, args_string: str) -> None:
        [client.send({"cmd": "authtrip", "trip": trip}) for trip in args_string.split(" ")]

    def deauthtrip(client: object, args_string: str) -> None:
        [client.send({"cmd": "deauthtrip", "trip": trip}) for trip in args_string.split(" ")]

    def enablecaptcha(client: object, args_string: str) -> None:
        client.send({"cmd": "enablecaptcha"})

    def disablecaptcha(client: object, args_string: str) -> None:
        client.send({"cmd": "disablecaptcha"})

    def lockroom(client: object, args_string: str) -> None:
        client.send({"cmd": "lockroom"})

    def unlockroom(client: object, args_string: str) -> None:
        client.send({"cmd": "unlockroom"})

    def forcecolor(client: object, args_string: str) -> None:
        args = args_string.split(" ")
        if len(args) > 1:
            client.send({"cmd": "forcecolor", "nick": args[0].lstrip("@"), "color": args[1]})

        else:
            client.print_msg("{}|{}| {}".format(termcolor.colored(client.formatted_datetime(), client.args["timestamp_color"]),
                                                termcolor.colored("CLIENT", client.args["client_color"]),
                                                termcolor.colored("User/Color cannot be empty", client.args["client_color"])))

    def anticmd(client: object, args_string: str) -> None:
        client.send({"cmd": "anticmd"})

    def uwuify(client: object, args_string: str) -> None:
        [client.send({"cmd": "uwuify", "nick": user.lstrip("@")}) for user in args_string.split(" ")]

    client_command_map = {
        "/help": show_help,
        "/raw": raw,
        "/list": list_users,
        "/profile": profile,
        "/nick": nick,
        "/clear": clear,
        "/wlock": wlock,
        "/ignore": ignore,
        "/unignoreall": unignoreall,
        "/reconnect": reconnect,
        "/set": set_alias,
        "/unset": unset_alias,
        "/configset": configset,
        "/configdump": configdump,
        "/save": save,
        "/reprint": reprint,
        "/exec": dev_exec,
        "/cat": cat,
        "/quit": quit_client
    }

    mod_command_map = {
        "/ban": ban,
        "/unban": unban,
        "/unbanall": unbanall,
        "/dumb": dumb,
        "/speak": speak,
        "/moveuser": moveuser,
        "/kick": kick,
        "/kickasone": kickasone,
        "/overflow": overflow,
        "/authtrip": authtrip,
        "/deauthtrip": deauthtrip,
        "/enablecaptcha": enablecaptcha,
        "/disablecaptcha": disablecaptcha,
        "/lockroom": lockroom,
        "/unlockroom": unlockroom,
        "/forcecolor": forcecolor,
        "/anticmd": anticmd,
        "/uwuify": uwuify
    }

    server_commands = ("/whisper", "/reply", "/me", "/stats")
