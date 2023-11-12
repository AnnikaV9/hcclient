#!/usr/bin/python3
#
# Author:    AnnikaV9
# License:   Unlicense
# Version:   1.11.0-git

import json
import threading
import ssl
import websocket
import sys
import re
import os
import subprocess
import copy
import argparse
import colorama
import datetime
import termcolor
import shutil
import prompt_toolkit
import notifypy
import yaml

class Client:
    """
    The main client class
    """
    def __init__(self, args: dict, bindings: prompt_toolkit.key_binding.KeyBindings) -> None:
        """
        Initializes the client and environment, sets up variables and threads
        """
        colorama.init()
        self.bindings = bindings

        self.args = args
        self.nick = self.args["nickname"]
        self.online_users = []
        self.online_users_details = {}
        self.online_ignored_users = []

        self.client_command_list = [
            "/help", "/raw", "/list", "/nick", "/clear", "/profile",
            "/wlock", "/ignore", "/unignoreall", "/reconnect",
            "/set", "/unset", "/configset", "/configdump", "/save", "/quit"
        ]
        self.server_command_list = [
            "/whisper", "/reply", "/me", "/stats",
        ]
        self.mod_command_list = [
            "/ban", "/unban", "/unbanall", "/dumb", "/speak", "/moveuser",
            "/kick", "/kickasone", "/overflow", "/authtrip", "/deauthtrip",
            "/enablecaptcha", "/disablecaptcha", "/lockroom", "/unlockroom",
            "/forcecolor", "/anticmd", "/uwuify"
        ]

        self.auto_complete_list = []
        self.manage_complete_list()

        self.term_content_saved = False
        self.manage_term_contents()

        self.def_config_dir = os.path.join(os.getenv("APPDATA"), "hcclient") if os.name == "nt" else os.path.join(os.getenv("HOME"), ".config", "hcclient")

        self.ws = websocket.WebSocket(sslopt={"cert_reqs": ssl.CERT_NONE})
        self.reconnecting = False

        self.whisper_lock = False
        self.prompt_session = prompt_toolkit.PromptSession(reserve_space_for_menu=4)

        self.input_lock = threading.Event()
        self.ping_event = threading.Event()
        self.thread_ping = threading.Thread(target=self.ping_thread, daemon=True)
        self.thread_recv = threading.Thread(target=self.recv_thread, daemon=True)

    def connect_to_server(self) -> None:
        """
        Connects to the websocket server and send the join packet
        Uses a proxy if specified
        """
        if not self.reconnecting:
            connect_status = "Connecting to {} ...".format(self.args["websocket_address"]) if not self.args["proxy"] else "Connecting to {} through proxy {} ...".format(self.args["websocket_address"], self.args["proxy"])

            self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                              termcolor.colored("CLIENT", self.args["client_color"]),
                                              termcolor.colored(connect_status, self.args["client_color"])),
                                              bypass_lock=True)

        if self.args["proxy"]:
            self.ws.connect(self.args["websocket_address"], http_proxy_host=self.args["proxy"].split(":")[1], http_proxy_port=self.args["proxy"].split(":")[2], proxy_type=self.args["proxy"].split(":")[0].lower())

        else:
            self.ws.connect(self.args["websocket_address"])

        self.ws.send(json.dumps({
            "cmd": "join",
            "channel": self.args["channel"],
            "nick": "{}#{}".format(self.nick, self.args["trip_password"])
        }))
        self.reconnecting = False

    def validate_config(option: str, value: str) -> bool:
        """
        Validates a configuration option and its value
        Returns True if valid, False if not
        """
        if option in ("timestamp_color", "client_color", "server_color", "nickname_color",
                      "self_nickname_color", "mod_nickname_color", "admin_nickname_color",
                      "message_color", "emote_color", "whisper_color", "warning_color"):
            if value not in termcolor.COLORS:
                return False

        elif option in ("no_unicode", "no_notify", "no_parse", "clear", "is_mod"):
            if not isinstance(value, bool):
                return False

        elif option in ("websocket_address", "trip_password", "prompt_string"):
            if not isinstance(value, str):
                return False

        elif option in ("aliases", "ignored"):
            if not isinstance(value, dict):
                return False

            elif option == "aliases":
                for alias, replacement in value.items():
                    if not isinstance(alias, str) or not isinstance(replacement, str):
                        return False

            elif option == "ignored":
                if "trips" not in value or "hashes" not in value:
                    return False

                elif not isinstance(value["trips"], list) or not isinstance(value["hashes"], list):
                    return False

        elif option == "proxy":
            if value and not isinstance(value, str):
                return False

        return True

    def manage_term_contents(self) -> None:
        """
        Use tput to save the terminal's contents if tput is available and --clear is specified
        """
        if self.args["clear"]:
            if shutil.which("tput"):
                os.system("tput smcup")
                self.term_content_saved = True

            else:
                try:
                    input("Warning! The 'tput' command was not found in your path.\nThis means that the terminal's contents will not be saved.\nExit and re-run without --clear as a workaround.\nPress enter to continue and clear the terminal anyway.")

                except (KeyboardInterrupt, EOFError):
                    sys.exit(0)

            os.system("cls" if os.name=="nt" else "clear")

    def print_msg(self, message: str, bypass_lock: bool=False) -> None:
        """
        Prints a message to the terminal if the input lock is set, otherwise waits
        """
        if not bypass_lock and not self.input_lock.is_set():
            self.input_lock.wait()

        print(message)

    def send(self, packet: str) -> None:
        """
        Sends a packet to the server if connected, otherwise prints an error
        """
        if self.ws.connected:
            self.ws.send(packet)

        else:
            self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                              termcolor.colored("CLIENT", self.args["client_color"]),
                                              termcolor.colored("Can't send packet, not connected to server. Run /reconnect", self.args["client_color"])),
                                              bypass_lock=True)

    def manage_complete_list(self) -> None:
        """
        Adds commands to the auto-complete list based on the user's permissions
        """
        self.auto_complete_list.clear()

        self.auto_complete_list.extend(self.client_command_list)
        self.auto_complete_list.extend(self.server_command_list)
        if self.args["is_mod"]:
            self.auto_complete_list.extend(self.mod_command_list)

        for prefix in ("", "/whisper ", "/profile ", "/ignore "):
            for user in self.online_users:
                self.auto_complete_list.append("{}@{}".format(prefix, user))

    def recv_thread(self) -> None:
        """
        Receives packets from the server and handles them
        """
        try:
            if not self.ws.connected:
                self.connect_to_server()

            while self.ws.connected:
                received = json.loads(self.ws.recv())
                packet_receive_time = datetime.datetime.now().strftime("%H:%M")

                if self.args["no_parse"]:
                    self.print_msg("\n{}|{}".format(packet_receive_time, received))

                match received["cmd"]:
                    case "onlineSet":
                        for nick in received["nicks"]:
                            self.online_users.append(nick)

                        for user_details in received["users"]:
                            self.online_users_details[user_details["nick"]] = {"Trip": user_details["trip"], "Type": user_details["uType"], "Hash": user_details["hash"]}

                            if self.online_users_details[user_details["nick"]]["Trip"] in self.args["ignored"]["trips"]:
                                self.online_ignored_users.append(user_details["nick"])

                            if self.online_users_details[user_details["nick"]]["Hash"] in self.args["ignored"]["hashes"]:
                                self.online_ignored_users.append(user_details["nick"])

                        self.manage_complete_list()

                        self.channel = received["users"][0]["channel"]

                        self.print_msg("{}|{}| {}".format(termcolor.colored(packet_receive_time, self.args["timestamp_color"]),
                                                          termcolor.colored("SERVER", self.args["server_color"]),
                                                          termcolor.colored("Channel: {} - Users: {}".format(self.channel, ", ".join(self.online_users)), self.args["server_color"])))

                    case "chat":
                        if received["nick"] in self.online_ignored_users:
                            continue

                        if len(received.get("trip", "")) < 6:
                            tripcode = "NOTRIP"

                        else:
                            tripcode = received.get("trip", "")

                        if received["uType"] == "mod":
                            color_to_use = self.args["mod_nickname_color"] if self.nick != received["nick"] else self.args["self_nickname_color"]
                            received["nick"] = "⭐ {}".format(received["nick"]) if not self.args["no_unicode"] else received["nick"]

                        elif received["uType"] == "admin":
                            color_to_use = self.args["admin_nickname_color"] if self.nick != received["nick"] else self.args["self_nickname_color"]
                            received["nick"] = "⭐ {}".format(received["nick"]) if not self.args["no_unicode"] else received ["nick"]
                            tripcode = "Admin"

                        else:
                            color_to_use = self.args["nickname_color"] if self.nick != received["nick"] else self.args["self_nickname_color"]

                        if f"@{self.nick}" in received["text"] and not self.args["no_notify"]:
                            if shutil.which("termux-notification"):
                                subprocess.Popen([
                                    "termux-notification",
                                    "-t", "hcclient",
                                    "-c", "[{}] {}".format(received["nick"], received["text"])
                                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                            else:
                                notification = notifypy.Notify()
                                notification.title = "hcclient"
                                notification.message = "[{}] {}".format(received["nick"], received["text"])
                                if os.path.isfile(os.path.join(self.def_config_dir, "tone.wav")):
                                    notification.audio = os.path.join(self.def_config_dir, "tone.wav")

                                notification.send(block=False)

                        self.print_msg("{}|{}| [{}] {}".format(termcolor.colored(packet_receive_time, self.args["timestamp_color"]),
                                                               termcolor.colored(tripcode, color_to_use),
                                                               termcolor.colored(received["nick"], color_to_use),
                                                               termcolor.colored(received["text"], self.args["message_color"])))

                    case "info":
                        if received.get("type") is not None and received.get("type") == "whisper":
                            if received["from"] in self.online_ignored_users:
                                continue

                            if len(received.get("trip", "")) < 6:
                                tripcode = "NOTRIP"

                            else:
                                tripcode = received.get("trip", "")

                            if received["from"] in self.online_users and not self.args["no_notify"]:
                                if shutil.which("termux-notification"):
                                    subprocess.Popen([
                                        "termux-notification",
                                        "-t", "hcclient",
                                        "-c", received["text"]
                                    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                                else:
                                    notification = notifypy.Notify()
                                    notification.title = "hcclient"
                                    notification.message = received["text"]
                                    if os.path.isfile(os.path.join(self.def_config_dir, "tone.wav")):
                                        notification.audio = os.path.join(self.def_config_dir, "tone.wav")

                                    notification.send(block=False)

                            self.print_msg("{}|{}| {}".format(termcolor.colored(packet_receive_time, self.args["timestamp_color"]),
                                                              termcolor.colored(tripcode, self.args["whisper_color"]),
                                                              termcolor.colored(received["text"], self.args["whisper_color"])))

                        else:
                            self.print_msg("{}|{}| {}".format(termcolor.colored(packet_receive_time, self.args["timestamp_color"]),
                                                              termcolor.colored("SERVER", self.args["server_color"]),
                                                              termcolor.colored(received["text"], self.args["server_color"])))

                    case "onlineAdd":
                        self.online_users.append(received["nick"])
                        self.online_users_details[received["nick"]] = {"Trip": received["trip"], "Type": received["uType"], "Hash": received["hash"]}

                        self.manage_complete_list()

                        if self.online_users_details[received["nick"]]["Trip"] in self.args["ignored"]["trips"]:
                            self.online_ignored_users.append(received["nick"])

                        if self.online_users_details[received["nick"]]["Hash"] in self.args["ignored"]["hashes"]:
                            self.online_ignored_users.append(received["nick"])

                        self.print_msg("{}|{}| {}".format(termcolor.colored(packet_receive_time, self.args["timestamp_color"]),
                                                          termcolor.colored("SERVER", self.args["server_color"]),
                                                          termcolor.colored(received["nick"] + " joined", self.args["server_color"])))

                    case "onlineRemove":
                        self.online_users.remove(received["nick"])
                        self.online_users_details.pop(received["nick"])

                        self.manage_complete_list()

                        if received["nick"] in self.online_ignored_users:
                            self.online_ignored_users.remove(received["nick"])

                        self.print_msg("{}|{}| {}".format(termcolor.colored(packet_receive_time, self.args["timestamp_color"]),
                                                          termcolor.colored("SERVER", self.args["server_color"]),
                                                          termcolor.colored(received["nick"] + " left", self.args["server_color"])))

                    case "emote":
                        if received["nick"] in self.online_ignored_users:
                            continue

                        if len(received.get("trip", "")) < 6:
                            tripcode = "NOTRIP"

                        else:
                            tripcode = received.get("trip", "")

                        self.print_msg("{}|{}| {}".format(termcolor.colored(packet_receive_time, self.args["timestamp_color"]),
                                                          termcolor.colored(tripcode, self.args["emote_color"]),
                                                          termcolor.colored(received["text"], self.args["emote_color"])))

                    case "warn":
                        self.print_msg("{}|{}| {}".format(termcolor.colored(packet_receive_time, self.args["timestamp_color"]),
                                                          termcolor.colored("!WARN!", self.args["warning_color"]),
                                                          termcolor.colored(received["text"], self.args["warning_color"])))

                        if received["text"].startswith("Nickname"):
                            self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                              termcolor.colored("CLIENT", self.args["client_color"]),
                                                              termcolor.colored("Try running /nick <newnick> and /reconnect", self.args["client_color"])))

        except:
            self.online_users = []
            self.online_users_details = {}
            self.online_ignored_users = []

            self.manage_complete_list()

            if self.args["is_mod"]:
                self.auto_complete_list.extend(self.mod_command_list)

            if self.reconnecting:
                self.close(thread=True)

            else:
                self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                  termcolor.colored("CLIENT", self.args["client_color"]),
                                                  termcolor.colored("Disconnected from server: {}".format(sys.exc_info()[1]), self.args["client_color"])))
                self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                  termcolor.colored("CLIENT", self.args["client_color"]),
                                                  termcolor.colored("Try running /reconnect", self.args["client_color"])))

                self.ping_event.set()
                self.close(thread=True)

    def ping_thread(self) -> None:
        """
        Sends a ping every 60 seconds as a keepalive
        """
        while self.ws.connected and not self.ping_event.is_set():
            self.send(json.dumps({"cmd": "ping"}))
            self.ping_event.wait(60)

    def input_loop(self) -> None:
        """
        The main input loop that draws the prompt and handles input
        """
        exit_attempted = False
        with prompt_toolkit.patch_stdout.patch_stdout(raw=True):
            while True:
                self.input_lock.clear()

                if self.args["prompt_string"] and self.args["prompt_string"] != "default":
                    prompt_string = self.args["prompt_string"]

                else:
                    prompt_string = "> " if self.args["no_unicode"] else "❯ "

                if exit_attempted:
                    prompt_string = "(ctrl+c again to exit, enter to cancel) " + prompt_string

                else:
                    buffer = ""

                self.prompt_length = len(prompt_string)

                nick_completer = prompt_toolkit.completion.WordCompleter(self.auto_complete_list, match_middle=True, ignore_case=True, sentence=True)

                self.unlock_after = threading.Timer(0.3, self.input_lock.set)
                self.unlock_after.start()

                try:
                    self.send_input(self.prompt_session.prompt(prompt_string, default=buffer, completer=nick_completer, complete_in_thread=True, multiline=True, key_bindings=self.bindings, prompt_continuation=(" " * self.prompt_length)))
                    exit_attempted = False

                except KeyboardInterrupt:
                    if not exit_attempted:
                        if self.unlock_after.is_alive():
                            self.unlock_after.cancel()
                        self.input_lock.clear()

                        buffer = self.prompt_session.default_buffer.document.text
                        lines = buffer.split("\n")
                        no_lines = len(lines)
                        true_term_size = shutil.get_terminal_size().columns - self.prompt_length
                        for line in lines:
                            if len(line) > true_term_size:
                                no_lines += round(len(line) / true_term_size - 0.5)

                        for _ in range(no_lines):
                            print("\033[A{}\033[A".format(" " * shutil.get_terminal_size().columns))

                        exit_attempted = True

                    else:
                        self.close(thread=False)

                except EOFError:
                    self.close(thread=False)

                except:
                    self.close(error=sys.exc_info(), thread=False)

    def send_input(self, message: str) -> None:
        """
        Handles input returned from the prompt
        """
        if self.unlock_after.is_alive():
            self.unlock_after.cancel()
        self.input_lock.clear()

        lines = message.split("\n")
        no_lines = len(lines)
        true_term_size = shutil.get_terminal_size().columns - self.prompt_length
        for line in lines:
            if len(line) > true_term_size:
                no_lines += round(len(line) / true_term_size - 0.5)

        for _ in range(no_lines):
            print("\033[A{}\033[A".format(" " * shutil.get_terminal_size().columns))

        if len(message) > 0:
            split_message = message.split(" ")
            for alias in self.args["aliases"]:
                split_message[:] = [part if part != f"${alias}" else self.args["aliases"][alias] for part in split_message]
            message = " ".join(split_message)

            parsed_message = message.partition(" ")
            match parsed_message[0]:
                case "/raw":
                    try:
                        json_to_send = json.loads(parsed_message[2])
                        self.send(json.dumps(json_to_send))

                    except:
                        self.print_msg("{}|{}| Error sending json: {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                                              termcolor.colored("CLIENT", self.args["client_color"]),
                                                                              termcolor.colored("{}".format(sys.exc_info()[1]), self.args["client_color"])),
                                                                              bypass_lock=True)

                case "/list":
                    self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                      termcolor.colored("CLIENT", self.args["client_color"]),
                                                      termcolor.colored("Channel: {} - Users: {}".format(self.channel, ", ".join(self.online_users)), self.args["client_color"])),
                                                      bypass_lock=True)

                case "/profile":
                    target = parsed_message[2].lstrip("@")
                    if target in self.online_users:
                        ignored = "Yes" if target in self.online_ignored_users else "No"
                        profile = "{}'s profile:\n".format(target) + "\n".join("{}: {}".format(option, value) for option, value in self.online_users_details[target].items()) + "\nIgnored: {}".format(ignored)

                        self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored(profile, self.args["client_color"])),
                                                          bypass_lock=True)


                    else:
                        self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored("No such user: '{}'".format(target), self.args["client_color"])),
                                                          bypass_lock=True)

                case "/nick":
                    if re.match("^[A-Za-z0-9_]*$", parsed_message[2]) and 0 < len(parsed_message[2]) < 25:
                        if self.ws.connected:
                            self.send(json.dumps({"cmd": "changenick", "nick": parsed_message[2]}))

                        self.nick = parsed_message[2]
                        self.args["nickname"] = parsed_message[2]

                    else:
                        self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored("Nickname must consist of up to 24 letters, numbers, and underscores", self.args["client_color"])),
                                                          bypass_lock=True)

                case "/clear":
                    if self.args["clear"]:
                        os.system("cls" if os.name=="nt" else "clear")

                    else:
                        self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored("Clearing is disabled, enable with the --clear flag or run `/configset clear true`", self.args["client_color"])),
                                                          bypass_lock=True)

                case "/wlock":
                    self.whisper_lock = not self.whisper_lock

                    self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                      termcolor.colored("CLIENT", self.args["client_color"]),
                                                      termcolor.colored("Toggled whisper lock to {}".format(self.whisper_lock), self.args["client_color"])),
                                                      bypass_lock=True)

                case "/ignore":
                    target = parsed_message[2].lstrip("@")
                    if target in self.online_users:
                        self.online_ignored_users.append(target)
                        trip_to_ignore = self.online_users_details[target]["Trip"] if self.online_users_details[target]["Trip"] != "" else None

                        if trip_to_ignore not in self.args["ignored"]["trips"] and trip_to_ignore is not None:
                            self.args["ignored"]["trips"].append(trip_to_ignore)

                        if self.online_users_details[target]["Hash"] not in self.args["ignored"]["hashes"]:
                            self.args["ignored"]["hashes"].append(self.online_users_details[target]["Hash"])

                        self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored("Ignoring trip '{}' and hash '{}', run /save to persist".format(trip_to_ignore, self.online_users_details[target]["Hash"]), self.args["client_color"])),
                                                          bypass_lock=True)

                    else:
                        self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored("No such user: '{}'".format(target), self.args["client_color"])),
                                                          bypass_lock=True)

                case "/unignoreall":
                    self.online_ignored_users = []
                    self.args["ignored"] = {"trips": [], "hashes": []}

                    self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                      termcolor.colored("CLIENT", self.args["client_color"]),
                                                      termcolor.colored("Unignored all trips/hashes, run /save to persist", self.args["client_color"])),
                                                      bypass_lock=True)

                case "/reconnect":
                    self.reconnecting = True

                    self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                      termcolor.colored("CLIENT", self.args["client_color"]),
                                                      termcolor.colored("Reconnecting...", self.args["client_color"])),
                                                      bypass_lock=True)

                    self.ws.close()
                    self.ping_event.set()
                    self.thread_ping.join()
                    self.thread_recv.join()

                    try:
                        self.connect_to_server()

                        self.ping_event.clear()
                        self.thread_ping = threading.Thread(target=self.ping_thread, daemon=True)
                        self.thread_recv = threading.Thread(target=self.recv_thread, daemon=True)
                        self.thread_ping.start()
                        self.thread_recv.start()

                    except:
                        self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored("Reconnect failed: {}".format(sys.exc_info()[1]), self.args["client_color"])),
                                                          bypass_lock=True)

                case "/set":
                    message_args = parsed_message[2].split(" ")
                    if len(message_args) < 2:
                        self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored("Alias/Value cannot be empty", self.args["client_color"])),
                                                          bypass_lock=True)

                    else:
                        self.args["aliases"][message_args[0]] = " ".join(message_args[1:])

                        self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored("Set alias '{}' = '{}'".format(message_args[0], self.args["aliases"][message_args[0]]), self.args["client_color"])),
                                                          bypass_lock=True)

                case "/unset":
                    try:
                        self.args["aliases"].pop(parsed_message[2])

                        self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored("Unset alias '{}'".format(parsed_message[2]), self.args["client_color"])),
                                                          bypass_lock=True)

                    except KeyError:
                        self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored("Alias '{}' isn't defined".format(parsed_message[2]), self.args["client_color"])),
                                                          bypass_lock=True)

                case "/configset":
                    message_args = parsed_message[2].lower().split(" ")
                    if message_args[0] in self.args and message_args[0] not in ("config_file", "channel", "nickname", "aliases", "ignored"):

                        value, option = " ".join(message_args[1:]), message_args[0]
                        if value.lower() == "false":
                            value = False

                        elif value.lower() == "true":
                            value = True

                        elif value.lower() in ("none", "null"):
                            value = None

                        if Client.validate_config(option, value):
                            self.args[option] = value

                            self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                              termcolor.colored("CLIENT", self.args["client_color"]),
                                                              termcolor.colored("Set configuration option '{}' to '{}'".format(option, value), self.args["client_color"])),
                                                              bypass_lock=True)

                        else:
                            self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                              termcolor.colored("CLIENT", self.args["client_color"]),
                                                              termcolor.colored("Error setting configuration: Invalid value '{}' for option '{}'".format(value, option), self.args["client_color"])),
                                                              bypass_lock=True)

                    else:
                        problem = "Invalid" if message_args[0] not in self.args else "Read-only"

                        self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored("Error setting configuration: {} option '{}'".format(problem, message_args[0]), self.args["client_color"])),
                                                          bypass_lock=True)

                case "/configdump":
                    self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                      termcolor.colored("CLIENT", self.args["client_color"]),
                                                      termcolor.colored("Active configuration:\n" + "\n".join("{}: {}".format(option, value) for option, value in self.args.items()), self.args["client_color"])),
                                                      bypass_lock=True)

                case "/save":
                    if self.args["config_file"]:
                        config = copy.deepcopy(self.args)
                        for arg in ("config_file", "channel", "nickname"):
                            config.pop(arg)

                        try:
                            with open(self.args["config_file"], "w") as config_file:
                                if self.args["config_file"].endswith(".json"):
                                    json.dump(config, config_file, indent=2)

                                else:
                                    yaml.dump(config, config_file, sort_keys=False, default_flow_style=False)

                                self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                                  termcolor.colored("CLIENT", self.args["client_color"]),
                                                                  termcolor.colored("Configuration saved to {}".format(self.args["config_file"]), self.args["client_color"])),
                                                                  bypass_lock=True)

                        except:
                            self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                              termcolor.colored("CLIENT", self.args["client_color"]),
                                                              termcolor.colored("Error saving configuration: {}".format(sys.exc_info()[1]), self.args["client_color"])),
                                                              bypass_lock=True)

                    else:
                        self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored("Unable to save configuration without a loaded config file, use --load-config", self.args["client_color"])),
                                                          bypass_lock=True)

                case "/quit":
                    self.close()

                case "/ban":
                    if self.args["is_mod"]:
                        [self.send(json.dumps({"cmd": "ban", "nick": user.lstrip("@")})) for user in parsed_message[2].split(" ")]

                case "/unban":
                    if self.args["is_mod"]:
                        [self.send(json.dumps({"cmd": "unban", "hash": uhash})) for uhash in parsed_message[2].split(" ")]

                case "/unbanall":
                    if self.args["is_mod"]:
                        self.send(json.dumps({"cmd": "unbanall"}))

                case "/dumb":
                    if self.args["is_mod"]:
                        [self.send(json.dumps({"cmd": "dumb", "nick": user.lstrip("@")})) for user in parsed_message[2].split(" ")]

                case "/speak":
                    if self.args["is_mod"]:
                        [self.send(json.dumps({"cmd": "speak", "nick": user.lstrip("@")})) for user in parsed_message[2].split(" ")]

                case "/moveuser":
                    if self.args["is_mod"]:
                        message_args = parsed_message[2].split(" ")
                        if len(message_args) > 1:
                            self.send(json.dumps({"cmd": "moveuser", "nick": message_args[0].lstrip("@"), "channel": message_args[1]}))

                        else:
                            self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                              termcolor.colored("CLIENT", self.args["client_color"]),
                                                              termcolor.colored("User/Channel cannot be empty", self.args["client_color"])),
                                                              bypass_lock=True)

                case "/kick":
                    if self.args["is_mod"]:
                        [self.send(json.dumps({"cmd": "kick", "nick": user.lstrip("@")})) for user in parsed_message[2].split(" ")]

                case "/kickasone":
                    if self.args["is_mod"]:
                        self.send(json.dumps({"cmd": "kick", "nick": [user.lstrip("@") for user in parsed_message[2].split(" ")]})) # supply a list so everyone gets banished to the same room

                case "/overflow":
                    if self.args["is_mod"]:
                        [self.send(json.dumps({"cmd": "overflow", "nick": user.lstrip("@")})) for user in parsed_message[2].split(" ")]

                case "/authtrip":
                    if self.args["is_mod"]:
                        [self.send(json.dumps({"cmd": "authtrip", "trip": trip})) for trip in parsed_message[2].split(" ")]

                case "/deauthtrip":
                    if self.args["is_mod"]:
                        [self.send(json.dumps({"cmd": "deauthtrip", "trip": trip})) for trip in parsed_message[2].split(" ")]

                case "/enablecaptcha":
                    if self.args["is_mod"]:
                        self.send(json.dumps({"cmd": "enablecaptcha"}))

                case "/disablecaptcha":
                    if self.args["is_mod"]:
                        self.send(json.dumps({"cmd": "disablecaptcha"}))

                case "/lockroom":
                    if self.args["is_mod"]:
                        self.send(json.dumps({"cmd": "lockroom"}))

                case "/unlockroom":
                    if self.args["is_mod"]:
                        self.send(json.dumps({"cmd": "unlockroom"}))

                case "/forcecolor":
                    if self.args["is_mod"]:
                        message_args = parsed_message[2].split(" ")
                        if len(message_args) > 1:
                            self.send(json.dumps({"cmd": "forcecolor", "nick": message_args[0].lstrip("@"), "color": message_args[1]}))

                        else:
                            self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                              termcolor.colored("CLIENT", self.args["client_color"]),
                                                              termcolor.colored("User/Color cannot be empty", self.args["client_color"])),
                                                              bypass_lock=True)

                case "/anticmd":
                    if self.args["is_mod"]:
                        self.send(json.dumps({"cmd": "anticmd"}))

                case "/uwuify":
                    if self.args["is_mod"]:
                        [self.send(json.dumps({"cmd": "uwuify", "nick": user.lstrip("@")})) for user in parsed_message[2].split(" ")]

                case "/help":
                    if parsed_message[2] == "":
                        help_text = """Help:
Input is multiline, so you can type, paste and edit code in the input field.
Press enter to send, and esc+enter/alt+enter/ctrl+n to add a newline.
Lines can be cleared with ctrl+u.

Client-based commands:
/help [server-based command]
  Displays this help message if no
  command is specified, otherwise
  displays information about the
  specified server-based command.
/raw <json>
  Sends json directly to the server
  without parsing.
/list
  Lists users in the channel.
/profile <nick>
  Prints a user's details.
/clear
  Clears the terminal.
/wlock
  Toggles whisper lock, which will
  prevent sending any messages
  other than whispers.
/nick <newnick>
  Changes your nickname.
/ignore <nick>
  Adds a user's trip and hash to
  the ignore list.
/unignoreall
  Clears the ignore list.
/reconnect
  Disconnects forcefully and
  reconnects to the server.
/set <alias> <value>
  Sets an alias. $alias will be
  replaced with the value in your
  messages.
/unset <alias>
  Unsets an alias.
/configset <option> <value>
  Sets a configuration option to a
  value. Changed values will be in
  effect immediately.
/configdump
  Prints the current configuration.
/save
  Saves the current configuration
  to the loaded configuration file.
  Will save aliases and ignored
  trips/hashes.
/quit
  Exits the client."""
                        mod_help_text = """\n\nClient-based mod commands:
/ban <nick> <nick2> <nick3>...
/unban <hash> <hash2> <hash3>...
/unbanall
/dumb <nick> <nick2> <nick3>...
/speak <nick> <nick2> <nick3>...
/moveuser <nick> <channel>
/kick <nick> <nick2> <nick3>...
/kickasone <nick> <nick2> <nick3>...
/overflow <nick> <nick2> <nick3>...
/authtrip <trip> <trip2> <trip3>...
/deauthtrip <trip> <trip2> <trip3>...
/enablecaptcha
/disablecaptcha
/lockroom
/unlockroom
/forcecolor <nick> <color>
/anticmd
/uwuify <nick> <nick2> <nick3>..."""
                        server_help_text = "\n\nServer-based commands should be displayed below:"
                        display = help_text + mod_help_text + server_help_text if self.args["is_mod"] else help_text + server_help_text

                        self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored(display, self.args["client_color"])),
                                                          bypass_lock=True)

                        self.send(json.dumps({"cmd": "help"}))

                    else:
                        self.send(json.dumps({"cmd": "help", "command": parsed_message[2]}))

                case _:
                    if self.whisper_lock:
                        if not message.split(" ")[0] in ("/whisper", "/w", "/reply", "/r") or message.startswith(" "):
                            self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                              termcolor.colored("CLIENT", self.args["client_color"]),
                                                              termcolor.colored("Whisper lock active, toggle it off to send messages", self.args["client_color"])),
                                                              bypass_lock=True)
                            return

                    self.send(json.dumps({"cmd": "chat", "text": message}))

    def close(self, error: bool=False, thread: bool=True) -> None:
        """
        Exits the client or thread
        """
        if not thread:
            colorama.deinit()

        if self.term_content_saved and not thread:
            os.system("tput rmcup")

        if error:
            print(error)
            sys.exit(1)

        else:
            sys.exit(0)


def generate_config(config: argparse.Namespace) -> None:
    """
    Generates a config file from the specified arguments
    """
    config = vars(config)
    for arg in ("gen_config", "config_file", "no_config", "channel", "nickname", "colors"):
            config.pop(arg)

    try:
        if not os.path.isfile("config.yml"):
            with open("config.yml", "x") as config_file:
                yaml.dump(config, config_file, sort_keys=False, default_flow_style=False)
                print("Configuration written to config.yml")

        else:
            with open("config.json", "x") as config_file:
                json.dump(config, config_file, indent=2)
                print("Configuration written to config.json")

    except:
        sys.exit("{}: error: {}".format(sys.argv[0], sys.exc_info()[1]))


def load_config(filepath: str) -> dict:
    """
    Loads a config file from the specified path
    """
    try:
        with open(filepath, "r") as config_file:
            if filepath.endswith(".json"):
                config = json.load(config_file)

            else:
                config = yaml.safe_load(config_file)

            missing_args = []
            for key in ("trip_password", "websocket_address", "no_parse",
                       "clear", "is_mod", "no_unicode", "no_notify",
                       "prompt_string", "message_color", "whisper_color",
                       "emote_color", "nickname_color", "self_nickname_color",
                       "warning_color", "server_color", "client_color",
                       "timestamp_color", "mod_nickname_color",
                       "admin_nickname_color", "ignored", "aliases", "proxy"):
                if key not in config:
                    missing_args.append(key)

            if len(missing_args) > 0:
                raise ValueError("{} is missing the following option(s): {}".format(filepath, ", ".join(missing_args)))

            return config

    except:
        sys.exit("{}: error: {}".format(sys.argv[0], sys.exc_info()[1]))


def initialize_config(args: argparse.Namespace, parser: argparse.ArgumentParser) -> dict:
    """
    Initializes the configuration and returns a dictionary
    """
    if args.gen_config:
        args.aliases = {"example": "example"}
        args.ignored = {"trips": ["example"], "hashes": ["example"]}
        if not args.prompt_string:
            args.prompt_string = "default"
        generate_config(args)
        sys.exit(0)

    if not args.channel or not args.nickname:
        parser.print_usage()
        print("hcclient: error: the following arguments are required: -c/--channel, -n/--nickname")
        sys.exit(1)

    if args.no_config:
        args.config_file = None

    if args.config_file:
        config = load_config(args.config_file)
        config["nickname"] = args.nickname
        config["channel"] = args.channel
        config["config_file"] = args.config_file
        for option in config:
            if not Client.validate_config(option, config[option]):
                sys.exit("{}: error: Invalid configuration value for option '{}'".format(sys.argv[0], option))

    else:
        loaded_config = False

        if not args.no_config:
            def_config_dir = os.path.join(os.getenv("APPDATA"), "hcclient") if os.name == "nt" else os.path.join(os.getenv("HOME"), ".config", "hcclient")
            file_options = ("config.yml", "config.json")

            for config_file in file_options:
                if os.path.isfile(os.path.join(def_config_dir, config_file)):
                    def_config_file = os.path.join(def_config_dir, config_file)
                    config = load_config(def_config_file)
                    config["nickname"] = args.nickname
                    config["channel"] = args.channel
                    config["config_file"] = def_config_file
                    for option in config:
                        if not Client.validate_config(option, config[option]):
                            sys.exit("{}: error: Invalid configuration value for option '{}'".format(sys.argv[0], option))
                    loaded_config = True
                    break

        if not loaded_config:
            config = vars(args)
            config["aliases"] = {}
            config["ignored"] = {"trips": [], "hashes": []}
            config.pop("gen_config")
            config.pop("no_config")
            config.pop("colors")
            for option in config:
                if not Client.validate_config(option, config[option]):
                    sys.exit("{}: error: Invalid configuration value for option '{}'".format(sys.argv[0], option))

    return config

def main():
    """
    Entry point
    """
    parser = argparse.ArgumentParser(description="Terminal client for connecting to hack.chat servers. Use --colors to see a list of valid colors")
    required_group = parser.add_argument_group("required arguments")
    optional_group = parser.add_argument_group("optional arguments")
    required_group.add_argument("-c", "--channel", help="specify the channel to join")
    required_group.add_argument("-n", "--nickname", help="specify the nickname to use")
    optional_group.add_argument("-t", "--trip-password", help="specify a tripcode password to use when joining")
    optional_group.add_argument("-w", "--websocket-address", help="specify the websocket address to connect to (default: wss://hack-chat/chat-ws)")
    optional_group.add_argument("-l", "--load-config", help="specify a config file to load", dest="config_file")
    optional_group.add_argument("--no-config", help="disables loading of the default config file", action="store_true")
    optional_group.add_argument("--gen-config", help="generates a config file with provided arguments", action="store_true")
    optional_group.add_argument("--no-parse", help="log received packets without parsing", action="store_true")
    optional_group.add_argument("--clear", help="enables clearing of the terminal", action="store_true")
    optional_group.add_argument("--is-mod", help="enables moderator commands", action="store_true")
    optional_group.add_argument("--no-unicode", help="disables moderator/admin icon and unicode characters in the UI", action="store_true")
    optional_group.add_argument("--no-notify", help="disables desktop notifications", action="store_true")
    optional_group.add_argument("--prompt-string", help="sets the prompt string (default: '❯ ' or '> ' if --no-unicode)")
    optional_group.add_argument("--colors", help="displays a list of valid colors and exits", action="store_true")
    optional_group.add_argument("--message-color", help="sets the message color (default: white)")
    optional_group.add_argument("--whisper-color", help="sets the whisper color (default: green)")
    optional_group.add_argument("--emote-color", help="sets the emote color (default: green)")
    optional_group.add_argument("--nickname-color", help="sets the nickname color of other users (default: blue)")
    optional_group.add_argument("--self-nickname-color", help="sets the nickname color of yourself (default: magenta)")
    optional_group.add_argument("--warning-color", help="sets the warning color (default: yellow)")
    optional_group.add_argument("--server-color", help="sets the server color (default: green)")
    optional_group.add_argument("--client-color", help="sets the client color (default: green)")
    optional_group.add_argument("--timestamp-color", help="sets the timestamp color (default: white)")
    optional_group.add_argument("--mod-nickname-color", help="sets the nickname color of moderators (default: cyan)")
    optional_group.add_argument("--admin-nickname-color", help="sets the nickname color of the admin (default: red)")
    optional_group.add_argument("--proxy", help="specify a proxy to use (format: TYPE:HOST:PORT) (default: None)")
    optional_group.add_argument("--version", help="displays the version and exits", action="version", version="hcclient 1.11.0-git")
    optional_group.set_defaults(gen_config=False,
                                config_file=None,
                                no_config=False,
                                no_parse=False,
                                clear=False,
                                is_mod=False,
                                no_unicode=False,
                                no_notify=False,
                                prompt_string="default",
                                colors=False,
                                message_color="white",
                                whisper_color="green",
                                emote_color="green",
                                nickname_color="blue",
                                self_nickname_color="magenta",
                                warning_color="yellow",
                                server_color="green",
                                client_color="green",
                                timestamp_color="white",
                                mod_nickname_color="cyan",
                                admin_nickname_color="red",
                                trip_password="",
                                websocket_address="wss://hack.chat/chat-ws",
                                proxy=False)
    args = parser.parse_args()

    if args.colors:
        print("Valid colors: \n{}".format("\n".join(termcolor.COLORS)))
        sys.exit(0)

    bindings = prompt_toolkit.key_binding.KeyBindings()

    # Newline on esc+enter, alt+enter or ctrl+n
    @bindings.add("escape", "enter")
    @bindings.add("c-n")
    def _(event):
        event.current_buffer.insert_text('\n')

    # Accept input on enter
    @bindings.add("enter")
    def _(event):
        event.current_buffer.validate_and_handle()

    client = Client(initialize_config(args, parser), bindings)
    client.thread_ping.start()
    client.thread_recv.start()
    client.input_loop()


if __name__ == "__main__":
    main()
