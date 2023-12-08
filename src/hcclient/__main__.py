#!/usr/bin/python3
#
# Author:    AnnikaV9
# License:   Unlicense
# Version:   1.18.0-git
#
# Everything is thrown into one file for now, as I'm not sure how
# to structure this project yet while keeping support for multiple
# distribution methods (PyPI, PyInstaller, Local)
# Will be restructured properly in the future (hopefully)
#
# Two classes are defined in this file:
#   - Client:          The main client class
#   - TextFormatter:   Handles markdown parsing, code highlighting and LaTeX simplifying
#


import json
import threading
import ssl
import sys
import re
import os
import subprocess
import copy
import argparse
import contextlib
import importlib
import datetime
import time
import random
import shutil
import termcolor
import colorama
import prompt_toolkit
import notifypy
import yaml
import websocket
import html
import linkify_it
import markdown_it
import mdit_py_plugins.texmath
import pygments.util
import pygments.lexers
import pygments.styles
import pygments.formatters


class Client:
    """
    The main client class
    """
    def __init__(self, args: dict) -> None:
        """
        Initializes the client and environment, sets up variables and threads
        """
        self.args = args

        colorama.init()
        self.bindings = prompt_toolkit.key_binding.KeyBindings()

        self.nick = self.args["nickname"]
        self.channel = None
        self.online_users = []
        self.online_users_details = {}
        self.online_ignored_users = []

        self.client_command_list = [
            "/help", "/raw", "/list", "/nick", "/clear", "/profile",
            "/wlock", "/ignore", "/unignoreall", "/reconnect", "/set",
            "/unset", "/configset", "/configdump", "/save", "/reprint",
            "/quit"
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

        self.formatter = TextFormatter()
        self.stdout_history = []
        self.updatable_messages = {}
        self.updatable_messages_lock = threading.Lock()

        self.def_config_dir = os.path.join(os.getenv("APPDATA"), "hcclient") if os.name == "nt" else os.path.join(os.getenv("HOME"), ".config", "hcclient")

        self.ws = websocket.WebSocket(sslopt={"cert_reqs": ssl.CERT_NONE})
        self.reconnecting = False
        self.timed_reconnect = threading.Timer(0, None)

        self.whisper_lock = False
        self.prompt_session = prompt_toolkit.PromptSession(reserve_space_for_menu=4)

        self.thread_ping = threading.Thread(target=self.ping_thread, daemon=True)
        self.thread_recv = threading.Thread(target=self.recv_thread, daemon=True)
        self.thread_cleanup = threading.Thread(target=self.cleanup_thread, daemon=True)

    def formatted_datetime(self) -> str:
        """
        Returns the current datetime as a string formatted with timestamp_format
        """
        return datetime.datetime.now().strftime(self.args["timestamp_format"])

    def connect_to_server(self) -> None:
        """
        Connects to the websocket server and send the join packet
        Uses a proxy if specified
        """
        connect_status = (f"Connecting to {self.args['websocket_address']}..." if not self.args["proxy"]
                          else f"Connecting to {self.args['websocket_address']} through proxy {self.args['proxy']}...")

        self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                          termcolor.colored(connect_status, self.args["client_color"])))

        if self.args["proxy"]:
            proxy_opt = self.args["proxy"].split(":")
            self.ws.connect(self.args["websocket_address"], http_proxy_host=proxy_opt[1], http_proxy_port=proxy_opt[2], proxy_type=proxy_opt[0].lower())

        else:
            self.ws.connect(self.args["websocket_address"])

        self.send({
            "cmd": "join",
            "channel": self.args["channel"],
            "nick": f"{self.nick}#{self.args['trip_password']}"
        })

    def reconnect_to_server(self) -> None:
        """
        Reconnects to the websocket server
        Runs in a separate temporary thread
        """
        self.reconnecting = True

        self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                          termcolor.colored("Initiating reconnect...", self.args["client_color"])))

        self.ws.close()
        self.thread_recv.join()

        self.reconnecting = False

        self.thread_recv = threading.Thread(target=self.recv_thread, daemon=True)
        self.thread_recv.start()

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

        elif option in ("no_unicode", "no_notify", "no_parse", "clear", "is_mod", "no_markdown", "latex"):
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

    def print_msg(self, message: str, hist: bool=True) -> None:
        """
        Prints a message to the terminal and adds it to the stdout history
        """
        print(message)

        if hist:
            self.stdout_history.append(message)
            if len(self.stdout_history) > 100:
                self.stdout_history.pop(0)

    def format(self, text: str, text_type: str="message") -> str:
        """
        Formats a string with the TextFormatter class,
        providing syntax highlighting and markdown
        """
        if not self.args["no_markdown"]:
            text = self.formatter.markdown(text, self.args["highlight_theme"], self.args["client_color"], self.args[f"{text_type}_color"], self.args["latex"], self.args["backticks_bg"])

        return text

    def send(self, packet: dict) -> None:
        """
        Sends a packet to the server if connected, otherwise prints an error
        """
        if self.ws.connected:
            self.ws.send(json.dumps(packet))

        else:
            self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                              termcolor.colored("CLIENT", self.args["client_color"]),
                                              termcolor.colored("Can't send packet, not connected to server. Run `/reconnect`", self.args["client_color"])))

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
                self.auto_complete_list.append(f"{prefix}@{user}")

    def level_to_utype(self, level: int) -> str:
        """
        Converts a user level to a user type
        """
        match level:
            case 9999999:
                return "Admin"

            case 999999:
                return "Mod"

            case _:
                return "User"

    def cleanup_updatables(self) -> None:
        """
        Expires updatable messages if older than 3 minutes
        We're being stricter than the official web client,
        which expires messages after 6 minutes
        """
        with self.updatable_messages_lock:
            hashes_to_remove = []
            for message_hash, message in self.updatable_messages.items():
                if time.time() - message["sent"] > 3 * 60:
                    unique_id = message["unique_id"]
                    timestamp = datetime.datetime.now().strftime("%H:%M")

                    self.print_msg("{}|{}| [{}] [{}] {}".format(termcolor.colored(timestamp, self.args["timestamp_color"]),
                                                                termcolor.colored(message["trip"], message["color"]),
                                                                f"Expired.ID: {unique_id}" if self.args["no_unicode"] else f"{chr(10007)} {unique_id}",
                                                                termcolor.colored(message["nick"], message["color"]),
                                                                termcolor.colored(self.format(message["text"]), self.args["message_color"])))

                    hashes_to_remove.append(message_hash)

                else:
                    break

            for message_hash in hashes_to_remove:
                self.updatable_messages.pop(message_hash)

    def cleanup_thread(self) -> None:
        """
        Thread that runs cleanup tasks every 30 seconds
        """
        while True:
            self.cleanup_updatables()
            # future cleanup tasks here
            threading.Event().wait(30)

    def push_notification(self, message: str, title: str="hcclient") -> None:
        """
        Sends a desktop/android notification if configured to do so
        """
        if self.args["no_notify"]:
            return

        if shutil.which("termux-notification"):
            subprocess.Popen([
                "termux-notification",
                "-t", title,
                "-c", message
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        else:
            notification = notifypy.Notify()
            notification.title = title
            notification.message = message
            if os.path.isfile(os.path.join(self.def_config_dir, "tone.wav")):
                notification.audio = os.path.join(self.def_config_dir, "tone.wav")

            notification.send(block=False)

    def recv_thread(self) -> None:
        """
        Receives packets from the server and handles them
        """
        try:
            if not self.ws.connected:
                self.connect_to_server()

            while self.ws.connected:
                received = json.loads(self.ws.recv())
                packet_receive_time = datetime.datetime.now().strftime(self.args["timestamp_format"])

                if self.args["no_parse"]:
                    self.print_msg("\n{}|{}".format(packet_receive_time, json.dumps(received)))
                    continue

                match received["cmd"]:
                    case "onlineSet":
                        for nick in received["nicks"]:
                            self.online_users.append(nick)

                        for user_details in received["users"]:
                            self.online_users_details[user_details["nick"]] = {
                                "Trip": user_details["trip"] if user_details["trip"] != "" else None,
                                "Type": self.level_to_utype(user_details["level"]),
                                "Hash": user_details["hash"]
                            }

                            if self.online_users_details[user_details["nick"]]["Trip"] in self.args["ignored"]["trips"]:
                                self.online_ignored_users.append(user_details["nick"])

                            if self.online_users_details[user_details["nick"]]["Hash"] in self.args["ignored"]["hashes"]:
                                self.online_ignored_users.append(user_details["nick"])

                        self.manage_complete_list()

                        self.channel = received["users"][0]["channel"]

                        self.print_msg("{}|{}| {}".format(termcolor.colored(packet_receive_time, self.args["timestamp_color"]),
                                                          termcolor.colored("SERVER", self.args["server_color"]),
                                                          termcolor.colored(f"Channel: {self.channel} - Users: {', '.join(self.online_users)}", self.args["server_color"])))

                    case "chat":
                        if received["nick"] in self.online_ignored_users:
                            continue

                        if len(received.get("trip", "")) < 6:
                            tripcode = "NOTRIP"

                        else:
                            tripcode = received.get("trip", "")

                        match self.level_to_utype(received["level"]):
                            case "Mod":
                                color_to_use = self.args["mod_nickname_color"] if self.nick != received["nick"] else self.args["self_nickname_color"]
                                received["nick"] = f"{chr(11088)} {received['nick']}" if not self.args["no_unicode"] else received["nick"]

                            case "Admin":
                                color_to_use = self.args["admin_nickname_color"] if self.nick != received["nick"] else self.args["self_nickname_color"]
                                received["nick"] = f"{chr(11088)} {received['nick']}" if not self.args["no_unicode"] else received ["nick"]
                                tripcode = "Admin"

                            case _:
                                color_to_use = self.args["nickname_color"] if self.nick != received["nick"] else self.args["self_nickname_color"]

                        if f"@{self.nick}" in received["text"]:
                            self.push_notification(f"[{received['nick']}] {received['text']}")

                        if "customId" in received:
                            message_hash = abs(hash(str(received["userid"]) + received["customId"])) % 100000000
                            unique_id = "".join(random.choice("123456789") for _ in range(5))

                            with self.updatable_messages_lock:
                                self.updatable_messages[message_hash] = {
                                    "customId": received["customId"],
                                    "userid": received["userid"],
                                    "text": received["text"],
                                    "sent": time.time(),
                                    "trip": tripcode,
                                    "nick": received["nick"],
                                    "color": color_to_use,
                                    "unique_id": unique_id
                                }

                            self.print_msg("{}|{}| [{}] [{}] {}".format(termcolor.colored(packet_receive_time, self.args["timestamp_color"]),
                                                                        termcolor.colored(tripcode, color_to_use),
                                                                        f"Updatable.ID: {unique_id}" if self.args["no_unicode"] else f"{chr(10711)} {unique_id}",
                                                                        termcolor.colored(received["nick"], color_to_use),
                                                                        termcolor.colored(self.format(received["text"]), self.args["message_color"])))

                        else:
                            self.print_msg("{}|{}| [{}] {}".format(termcolor.colored(packet_receive_time, self.args["timestamp_color"]),
                                                                   termcolor.colored(tripcode, color_to_use),
                                                                   termcolor.colored(received["nick"], color_to_use),
                                                                   termcolor.colored(self.format(received["text"]), self.args["message_color"])))

                    case "updateMessage":
                        message_hash = abs(hash(str(received["userid"]) + received["customId"])) % 100000000
                        with self.updatable_messages_lock:
                            match received["mode"]:
                                case "overwrite":
                                    if message_hash in self.updatable_messages:
                                        self.updatable_messages[message_hash]["text"] = received["text"]

                                case "append":
                                    if message_hash in self.updatable_messages:
                                        self.updatable_messages[message_hash]["text"] += received["text"]

                                case "prepend":
                                    if message_hash in self.updatable_messages:
                                        self.updatable_messages[message_hash]["text"] = received["text"] + self.updatable_messages[message_hash]["text"]

                                case "complete":
                                    if message_hash in self.updatable_messages:
                                        message = self.updatable_messages[message_hash]
                                        unique_id = message["unique_id"]

                                        self.print_msg("{}|{}| [{}] [{}] {}".format(termcolor.colored(packet_receive_time, self.args["timestamp_color"]),
                                                                                    termcolor.colored(message["trip"], message["color"]),
                                                                                    f"Completed.ID: {unique_id}" if self.args["no_unicode"] else f"{chr(10003)} {unique_id}",
                                                                                    termcolor.colored(message["nick"], message["color"]),
                                                                                    termcolor.colored(self.format(message["text"]), self.args["message_color"])))

                                        self.updatable_messages.pop(message_hash)

                    case "info":
                        if received.get("type") is not None and received.get("type") == "whisper":
                            sender = received["from"]
                            if sender in self.online_ignored_users:
                                continue

                            if len(received.get("trip", "")) < 6:
                                tripcode = "NOTRIP"

                            else:
                                tripcode = received.get("trip", "")

                            if sender in self.online_users:
                                self.push_notification(received["text"])

                            self.print_msg("{}|{}| {}".format(termcolor.colored(packet_receive_time, self.args["timestamp_color"]),
                                                              termcolor.colored(tripcode, self.args["whisper_color"]),
                                                              termcolor.colored(self.format(received["text"], "whisper"), self.args["whisper_color"])))

                        else:
                            self.print_msg("{}|{}| {}".format(termcolor.colored(packet_receive_time, self.args["timestamp_color"]),
                                                              termcolor.colored("SERVER", self.args["server_color"]),
                                                              termcolor.colored(received["text"], self.args["server_color"])))

                    case "onlineAdd":
                        self.online_users.append(received["nick"])

                        self.online_users_details[received["nick"]] = {
                            "Trip": received["trip"] if received["trip"] != "" else None,
                            "Type": self.level_to_utype(received["level"]),
                            "Hash": received["hash"]
                        }

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
                                                          termcolor.colored(self.format(received["text"], "emote"), self.args["emote_color"])))

                    case "warn":
                        self.print_msg("{}|{}| {}".format(termcolor.colored(packet_receive_time, self.args["timestamp_color"]),
                                                          termcolor.colored("!WARN!", self.args["warning_color"]),
                                                          termcolor.colored(received["text"], self.args["warning_color"])))

                        if received["text"].startswith("Nickname"):
                            self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                              termcolor.colored("CLIENT", self.args["client_color"]),
                                                              termcolor.colored("Try running `/nick <newnick>` and `/reconnect`", self.args["client_color"])))

        except Exception as e:
            self.channel = None
            self.online_users = []
            self.online_users_details = {}
            self.online_ignored_users = []

            self.manage_complete_list()

            if self.args["is_mod"]:
                self.auto_complete_list.extend(self.mod_command_list)

            if self.reconnecting:
                self.close()

            else:
                self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                  termcolor.colored("CLIENT", self.args["client_color"]),
                                                  termcolor.colored(f"Disconnected from server: {e}", self.args["client_color"])))
                self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                  termcolor.colored("CLIENT", self.args["client_color"]),
                                                  termcolor.colored("Reconnecting in 60 seconds, run `/reconnect` do it immediately", self.args["client_color"])))
                self.timed_reconnect = threading.Timer(60, self.reconnect_to_server)
                self.timed_reconnect.start()
                self.close()

    def ping_thread(self) -> None:
        """
        Sends a ping every 60 seconds as a keepalive
        """
        while True:
            if self.ws.connected:
                with contextlib.suppress(Exception):
                    self.ws.send(json.dumps({"cmd": "ping"}))

                threading.Event().wait(60)

    def buffer_replace_aliases(self, event: prompt_toolkit.key_binding.KeyPressEvent) -> None:
        """
        Replaces aliases with their values in the current buffer
        Will be bound to space
        """
        event.current_buffer.insert_text(" ")
        no_chars = len(event.current_buffer.text)

        word_list = event.current_buffer.text.split(" ")
        for alias, value in self.args["aliases"].items():
            word_list[:] = [word if word != f"${alias}" else value for word in word_list]
        processed_text = " ".join(word_list)
        no_added = len(processed_text) - no_chars

        event.current_buffer.text = processed_text
        event.current_buffer.cursor_position += no_added

    def buffer_add_newline(self, event: prompt_toolkit.key_binding.KeyPressEvent) -> None:
        """
        Adds a newline to the current buffer
        Will be bound to ctrl+n, escape+enter and alt+enter
        """
        event.current_buffer.insert_text("\n")

    def buffer_clear(self, event: prompt_toolkit.key_binding.KeyPressEvent) -> None:
        """
        Clears the current buffer
        Will be bound to ctrl+l
        """
        event.current_buffer.reset()

    def keyboard_interrupt(self, event: prompt_toolkit.key_binding.KeyPressEvent) -> None:
        """
        Closes the client if initated twice
        Will be bound to ctrl+c
        """
        if self.exit_attempted:
            raise KeyboardInterrupt

        self.exit_attempted = True
        event.current_buffer.reset()

        self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                            termcolor.colored("CLIENT", self.args["client_color"]),
                                            termcolor.colored("Press ctrl+c again to exit", self.args["client_color"])))

    def buffer_handle_send(self, event: prompt_toolkit.key_binding.KeyPressEvent) -> None:
        """
        Sends the message and adds it to the prompt history
        Will be bound to enter
        """
        buffer = event.current_buffer.text
        event.current_buffer.reset()

        self.send_input(buffer)
        self.prompt_session.history.append_string(buffer)

        self.exit_attempted = False

    def return_prompt_string(self) -> str:
        """
        Returns the prompt string, either the default or the one specified by the user
        Used as a callable, so it can be changed at runtime with /configset
        """
        if self.args["prompt_string"] and self.args["prompt_string"] != "default":
            return self.args["prompt_string"]

        return "> " if self.args["no_unicode"] else f"{chr(10095)} "

    def create_completer(self) -> prompt_toolkit.completion.Completer | None:
        """
        Creates a completer instance based on the suggest_aggr option
        """
        base_completer = prompt_toolkit.completion.WordCompleter(
            self.auto_complete_list,
            match_middle=False if self.args["suggest_aggr"] < 2 else True,
            ignore_case=True,
            sentence=True
        )

        match self.args["suggest_aggr"]:
            case 0:
                return None

            case 1 | 2:
                return base_completer

            case 3:
                return prompt_toolkit.completion.FuzzyCompleter(base_completer)

    def input_manager(self) -> None:
        """
        Input manager that draws the prompt and handles input
        """
        self.bindings.add("space")(self.buffer_replace_aliases)
        self.bindings.add("enter")(self.buffer_handle_send)
        self.bindings.add("escape", "enter")(self.buffer_add_newline)
        self.bindings.add("c-n")(self.buffer_add_newline)
        self.bindings.add("c-c")(self.keyboard_interrupt)
        self.bindings.add("c-l")(self.buffer_clear)

        self.exit_attempted = False

        with prompt_toolkit.patch_stdout.patch_stdout(raw=True):
            try:
                self.prompt_session.prompt(self.return_prompt_string, completer=self.create_completer(), complete_in_thread=True, multiline=True, key_bindings=self.bindings)

            except (EOFError, KeyboardInterrupt, SystemExit):
                self.close(thread=False)

            except Exception as e:
                self.close(error=e, thread=False)

    def send_input(self, message: str) -> None:
        """
        Handles input received from the prompt
        """
        if len(message) > 0:
            word_list = message.split(" ")
            for alias, value in self.args["aliases"].items():
                word_list[:] = [word if word != f"${alias}" else value for word in word_list]
            message = " ".join(word_list)

            parsed_message = message.partition(" ")
            match parsed_message[0]:
                case "/raw":
                    try:
                        self.send(json.loads(parsed_message[2]))

                    except Exception as e:
                        self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored(f"Error sending json: {e}", self.args["client_color"])))

                case "/list":
                    self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                      termcolor.colored("CLIENT", self.args["client_color"]),
                                                      termcolor.colored(f"Channel: {self.channel} - Users: {', '.join(self.online_users)}", self.args["client_color"])))

                case "/profile":
                    target = parsed_message[2].lstrip("@")
                    if target in self.online_users:
                        ignored = "Yes" if target in self.online_ignored_users else "No"
                        profile = f"{target}'s profile:\n" + "\n".join(f"{option}: {value}" for option, value in self.online_users_details[target].items()) + f"\nIgnored: {ignored}"

                        self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored(profile, self.args["client_color"])))


                    else:
                        self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored(f"No such user: '{target}'", self.args["client_color"])))

                case "/nick":
                    if re.match("^[A-Za-z0-9_]*$", parsed_message[2]) and 0 < len(parsed_message[2]) < 25:
                        if self.ws.connected:
                            self.send({"cmd": "changenick", "nick": parsed_message[2]})

                        self.nick = parsed_message[2]
                        self.args["nickname"] = parsed_message[2]

                    else:
                        self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored("Nickname must consist of up to 24 letters, numbers, and underscores", self.args["client_color"])))

                case "/clear":
                    os.system("cls" if os.name == "nt" else "clear")
                    self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                      termcolor.colored("CLIENT", self.args["client_color"]),
                                                      termcolor.colored("Console cleared, run `/reprint` to undo", self.args["client_color"])),
                                                      hist=False)

                case "/wlock":
                    self.whisper_lock = not self.whisper_lock

                    self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                      termcolor.colored("CLIENT", self.args["client_color"]),
                                                      termcolor.colored(f"Toggled whisper lock to {self.whisper_lock}", self.args["client_color"])))

                case "/ignore":
                    target = parsed_message[2].lstrip("@")
                    if target in self.online_users:
                        self.online_ignored_users.append(target)
                        target_trip = self.online_users_details[target]["Trip"]
                        target_hash = self.online_users_details[target]["Hash"]

                        if target_trip not in self.args["ignored"]["trips"] and target_trip is not None:
                            self.args["ignored"]["trips"].append(target_trip)

                        if target_hash not in self.args["ignored"]["hashes"]:
                            self.args["ignored"]["hashes"].append(target_hash)

                        return_msg = f"Ignoring trip '{target_trip}' and hash '{target_hash}'" if target_trip is not None else f"Ignoring hash '{target_hash}'"
                        return_msg += ", run `/save` to persist"

                        self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored(return_msg, self.args["client_color"])))

                    else:
                        self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored(f"No such user: '{target}'", self.args["client_color"])))

                case "/unignoreall":
                    self.online_ignored_users = []
                    self.args["ignored"] = {"trips": [], "hashes": []}

                    self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                      termcolor.colored("CLIENT", self.args["client_color"]),
                                                      termcolor.colored("Unignored all trips/hashes, run `/save` to persist", self.args["client_color"])))

                case "/reconnect":
                    self.timed_reconnect.cancel()
                    threading.Thread(target=self.reconnect_to_server, daemon=True).start()

                case "/set":
                    message_args = parsed_message[2].split(" ")
                    if len(message_args) < 2:
                        self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored("Alias/Value cannot be empty", self.args["client_color"])))

                    else:
                        self.args["aliases"][message_args[0]] = " ".join(message_args[1:])

                        self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored(f"Set alias '{message_args[0]}' = '{self.args['aliases'][message_args[0]]}'", self.args["client_color"])))

                case "/unset":
                    try:
                        self.args["aliases"].pop(parsed_message[2])

                        self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored(f"Unset alias '{parsed_message[2]}'", self.args["client_color"])))

                    except KeyError:
                        self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored(f"Alias '{parsed_message[2]}' isn't defined", self.args["client_color"])))

                case "/configset":
                    message_args = parsed_message[2].split(" ")
                    value, option = " ".join(message_args[1:]), message_args[0].lower()

                    if option in self.args and option not in ("config_file", "channel", "nickname", "aliases", "ignored"):
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

                        if Client.validate_config(option, value):
                            self.args[option] = value
                            self.manage_complete_list()
                            self.prompt_session.completer = self.create_completer()

                            self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                              termcolor.colored("CLIENT", self.args["client_color"]),
                                                              termcolor.colored(f"Set configuration option '{option}' to '{value}'", self.args["client_color"])))

                            if option == "latex" and value:
                                if "latex2sympy2" not in sys.modules:
                                    global latex2sympy2
                                    import latex2sympy2

                                    self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                                      termcolor.colored("CLIENT", self.args["client_color"]),
                                                                      termcolor.colored("Warning: You have enabled LaTeX simplifying", self.args["client_color"])))
                                    self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                                      termcolor.colored("CLIENT", self.args["client_color"]),
                                                                      termcolor.colored("Idle memory usage will increase significantly", self.args["client_color"])))

                        else:
                            self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                              termcolor.colored("CLIENT", self.args["client_color"]),
                                                              termcolor.colored(f"Error setting configuration: Invalid value '{value}' for option '{option}'", self.args["client_color"])))

                    else:
                        problem = "Invalid" if option not in self.args else "Read-only"

                        self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored(f"Error setting configuration: {problem} option '{option}'", self.args["client_color"])))

                case "/configdump":
                    self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                      termcolor.colored("CLIENT", self.args["client_color"]),
                                                      termcolor.colored("Active configuration:\n" + "\n".join(f"{option}: {value}" for option, value in self.args.items()), self.args["client_color"])))

                case "/save":
                    if self.args["config_file"]:
                        config = copy.deepcopy(self.args)
                        for arg in ("config_file", "channel", "nickname"):
                            config.pop(arg)

                        try:
                            with open(self.args["config_file"], "w", encoding="utf8") as config_file:
                                if self.args["config_file"].endswith(".json"):
                                    json.dump(config, config_file, indent=2)

                                else:
                                    yaml.dump(config, config_file, sort_keys=False, default_flow_style=False)

                                self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                                  termcolor.colored("CLIENT", self.args["client_color"]),
                                                                  termcolor.colored(f"Configuration saved to {self.args['config_file']}", self.args["client_color"])))

                        except Exception as e:
                            self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                              termcolor.colored("CLIENT", self.args["client_color"]),
                                                              termcolor.colored(f"Error saving configuration: {e}", self.args["client_color"])))

                    else:
                        self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored("Unable to save configuration without a loaded config file", self.args["client_color"])))
                        self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored(f"Load a config file with `--load-config` or place `config.yml` in {self.def_config_dir}", self.args["client_color"])))

                case "/reprint":
                    self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                      termcolor.colored("CLIENT", self.args["client_color"]),
                                                      termcolor.colored(f"Re-printing {len(self.stdout_history)} messages...", self.args["client_color"])),
                                                      hist=False)

                    print("\n".join(self.stdout_history))

                case "/quit":
                    raise SystemExit

                case "/ban":
                    if self.args["is_mod"]:
                        [self.send({"cmd": "ban", "nick": user.lstrip("@")}) for user in parsed_message[2].split(" ")]

                case "/unban":
                    if self.args["is_mod"]:
                        [self.send({"cmd": "unban", "hash": uhash}) for uhash in parsed_message[2].split(" ")]

                case "/unbanall":
                    if self.args["is_mod"]:
                        self.send({"cmd": "unbanall"})

                case "/dumb":
                    if self.args["is_mod"]:
                        [self.send({"cmd": "dumb", "nick": user.lstrip("@")}) for user in parsed_message[2].split(" ")]

                case "/speak":
                    if self.args["is_mod"]:
                        [self.send({"cmd": "speak", "nick": user.lstrip("@")}) for user in parsed_message[2].split(" ")]

                case "/moveuser":
                    if self.args["is_mod"]:
                        message_args = parsed_message[2].split(" ")
                        if len(message_args) > 1:
                            self.send({"cmd": "moveuser", "nick": message_args[0].lstrip("@"), "channel": message_args[1]})

                        else:
                            self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                              termcolor.colored("CLIENT", self.args["client_color"]),
                                                              termcolor.colored("User/Channel cannot be empty", self.args["client_color"])))

                case "/kick":
                    if self.args["is_mod"]:
                        [self.send({"cmd": "kick", "nick": user.lstrip("@")}) for user in parsed_message[2].split(" ")]

                case "/kickasone":
                    if self.args["is_mod"]:
                        self.send({"cmd": "kick", "nick": [user.lstrip("@") for user in parsed_message[2].split(" ")]}) # supply a list so everyone gets banished to the same room

                case "/overflow":
                    if self.args["is_mod"]:
                        [self.send({"cmd": "overflow", "nick": user.lstrip("@")}) for user in parsed_message[2].split(" ")]

                case "/authtrip":
                    if self.args["is_mod"]:
                        [self.send({"cmd": "authtrip", "trip": trip}) for trip in parsed_message[2].split(" ")]

                case "/deauthtrip":
                    if self.args["is_mod"]:
                        [self.send({"cmd": "deauthtrip", "trip": trip}) for trip in parsed_message[2].split(" ")]

                case "/enablecaptcha":
                    if self.args["is_mod"]:
                        self.send({"cmd": "enablecaptcha"})

                case "/disablecaptcha":
                    if self.args["is_mod"]:
                        self.send({"cmd": "disablecaptcha"})

                case "/lockroom":
                    if self.args["is_mod"]:
                        self.send({"cmd": "lockroom"})

                case "/unlockroom":
                    if self.args["is_mod"]:
                        self.send({"cmd": "unlockroom"})

                case "/forcecolor":
                    if self.args["is_mod"]:
                        message_args = parsed_message[2].split(" ")
                        if len(message_args) > 1:
                            self.send({"cmd": "forcecolor", "nick": message_args[0].lstrip("@"), "color": message_args[1]})

                        else:
                            self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                              termcolor.colored("CLIENT", self.args["client_color"]),
                                                              termcolor.colored("User/Color cannot be empty", self.args["client_color"])))

                case "/anticmd":
                    if self.args["is_mod"]:
                        self.send({"cmd": "anticmd"})

                case "/uwuify":
                    if self.args["is_mod"]:
                        [self.send({"cmd": "uwuify", "nick": user.lstrip("@")}) for user in parsed_message[2].split(" ")]

                case "/help":
                    if parsed_message[2] == "":
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
                        display = help_text + mod_help_text + footer_text if self.args["is_mod"] else help_text + footer_text

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
                            self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                              termcolor.colored("CLIENT", self.args["client_color"]),
                                                              termcolor.colored(f"Help text:{display}", self.args["client_color"])))

                    else:
                        if parsed_message[2] == "server":
                            self.send({"cmd": "help"})

                        else:
                            self.send({"cmd": "help", "command": parsed_message[2]})

                case _:
                    if self.whisper_lock:
                        if not message.split(" ")[0] in ("/whisper", "/w", "/reply", "/r") or message.startswith(" "):
                            self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                              termcolor.colored("CLIENT", self.args["client_color"]),
                                                              termcolor.colored("Whisper lock active, toggle it off to send messages", self.args["client_color"])))
                            return

                    self.send({"cmd": "chat", "text": message})

    def close(self, error: bool=False, thread: bool=True) -> None:
        """
        Exits the client or thread
        """
        if not thread:
            colorama.deinit()

        if error:
            print(f"{type(error).__name__}: {error}")
            sys.exit(1)

        else:
            sys.exit(0)

    def run(self) -> None:
        """
        Start threads and run the input manager
        """
        if self.args["clear"]:
            os.system("cls" if os.name == "nt" else "clear")

        if self.args["latex"]:
            global latex2sympy2
            import latex2sympy2

            self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                              termcolor.colored("CLIENT", self.args["client_color"]),
                                              termcolor.colored("Warning: You have enabled LaTeX simplifying", self.args["client_color"])))
            self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                              termcolor.colored("CLIENT", self.args["client_color"]),
                                              termcolor.colored("Idle memory usage will increase significantly", self.args["client_color"])))

        for thread in (self.thread_ping, self.thread_recv, self.thread_cleanup):
            thread.start()

        self.input_manager()


class TextFormatter:
    """
    Handles markdown parsing, code highlighting and LaTeX simplifying
    """
    def __init__(self) -> None:
        """
        Initializes the markdown parser and compiles regex patterns
        """
        self.parser = markdown_it.MarkdownIt("zero")
        self.parser.enable(["emphasis", "escape", "strikethrough", "link", "image", "fence", "autolink", "backticks"])
        self.parser.use(mdit_py_plugins.texmath.texmath_plugin)

        self.linkify = (
            linkify_it.LinkifyIt()
            .add("git:", "http:")
            .add("ws:", "http:")
            .add("wss:", "https:")
        )

        self.codeblock_pattern = re.compile(r"\s*<pre><code(?: class=\"(?P<lang>[^\s\n]+)\")?>(?P<code>.*?)</code></pre>", re.DOTALL)
        self.code_pattern = re.compile(r"<(?!pre>)(?:code>(?P<code>.*?)</code>)", re.DOTALL)

        self.link_pattern = re.compile(r"<a href=\"(?P<url>.*?)\">(.*?)</a>", re.DOTALL)
        self.image_pattern = re.compile(r"<img src=\"(?P<url>.*?)\" alt=\"(.*?)\">", re.DOTALL)

        self.eq_pattern = re.compile(r"<eq>(?P<equation>.*?)</eq>", re.DOTALL)
        self.eqn_pattern = re.compile(r"<section>\n<eqn>(?P<equation>.*?)</eqn>\n</section>", re.DOTALL)

    def markdown(self, text: str, highlight_theme: str, client_color: str, message_color: str, latex: bool, backticks_bg: int) -> str:
        """
        Formats text with markdown and calls the highlighter and LaTeX simplifier
        """
        parsed = self.parser.render(text)
        message_color_open = "\033[%dm" % (termcolor.COLORS[message_color])

        parsed = parsed.replace("<p>", "").replace("</p>\n", "\n").replace("</p>", "\n")
        parsed = parsed.replace("<em>", "\033[3m").replace("</em>", "\033[0m" + message_color_open)
        parsed = parsed.replace("<strong>", "\033[1m").replace("</strong>", "\033[0m" + message_color_open)
        parsed = parsed.replace("<s>", "\033[9m").replace("</s>", "\033[0m" + message_color_open)

        parsed = self.link_pattern.sub("\033[4m\\g<url>\033[0m" + message_color_open, parsed)
        parsed = self.image_pattern.sub("\033[4m\\g<url>\033[0m" + message_color_open, parsed)

        parsed = parsed.replace("<pre><code>", "<pre><code class=\"guess\">")
        parsed = self.code_pattern.sub("\033[48;5;{}m \\g<code> \033[0m".format(backticks_bg) + message_color_open, parsed)
        parsed = self.highlight_blocks(parsed, highlight_theme, client_color, message_color_open)

        if latex:
            self.message_color_open = message_color_open
            parsed = self.eq_pattern.sub(self.simplify_latex, parsed)
            parsed = self.eqn_pattern.sub(self.simplify_latex, parsed)

        else:
            parsed = self.eq_pattern.sub("$\\g<equation>$", parsed)
            parsed = self.eqn_pattern.sub("$$\\g<equation>$$", parsed)

        if self.linkify.test(parsed):
            links = self.linkify.match(parsed)
            for link in links:
                parsed = parsed.replace(link.raw, f"\033[4m{link.raw}\033[0m" + message_color_open)

        return html.unescape(parsed.strip("\n"))

    def highlight_blocks(self, text: str, highlight_theme: str, client_color: str, message_color_open: str) -> str:
        """
        Highlights code blocks with pygments
        """
        matches = self.codeblock_pattern.finditer(text)
        for match in matches:
            code = html.unescape(match.group("code"))
            lang = match.group("lang").replace("language-", "")

            try:
                lexer = pygments.lexers.get_lexer_by_name(lang)
                guess_tag = ""

            except pygments.util.ClassNotFound:
                lexer = pygments.lexers.guess_lexer(code)
                guess_tag = "(guessed) "

            highlighted = pygments.highlight(code, lexer, pygments.formatters.Terminal256Formatter(style=highlight_theme)).strip("\n")

            text = text.replace(match.group(), termcolor.colored(f"\n--- {lexer.name.lower()} {guess_tag}---\n", client_color) +
                                               highlighted +
                                               termcolor.colored("\n------", client_color) +
                                               message_color_open)

        return text

    def simplify_latex(self, match):
        """
        Simplifies LaTeX equations with latex2sympy2
        """
        equation = match.group("equation")
        if match.group(0).startswith("<eq>"):
            block = "|"

        else:
            block = "||"

        try:
            sympy_expr = str(latex2sympy2.latex2sympy(equation)).replace("**", "^")
            replacement = f"\033[3m\033[1m{block}latex: {sympy_expr}{block}\033[0m" + self.message_color_open

        except:
            replacement = f"\033[3m\033[1m{block}latex-error: {equation}{block}\033[0m" + self.message_color_open

        return replacement


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
                                  "backticks_bg",
                                  "no_highlight", # deprecated
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
            if not Client.validate_config(option, value):
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
                        if not Client.validate_config(option, value):
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
                if not Client.validate_config(option, value):
                    sys.exit(f"{sys.argv[0]}: error: invalid configuration value for option '{option}'")

    return config


def load_hooks(client: Client) -> Client:
    hook_dir = os.path.join(os.getenv("APPDATA"), "hcclient", "hooks") if os.name == "nt" else os.path.join(os.getenv("HOME"), ".config", "hcclient", "hooks")
    if not os.path.isdir(hook_dir):
        return client

    for hook in os.listdir(hook_dir):
        if hook.endswith(".py"):
            try:
                hook_path = os.path.join(hook_dir, hook)
                spec = importlib.util.spec_from_file_location(hook, hook_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                client = module.hook(client)

            except Exception as e:
                sys.exit(f"{sys.argv[0]}: error: Unable to load hook '{hook}': {e}")

    return client


default_config = {
    "trip_password": "",
    "websocket_address": "wss://hack.chat/chat-ws",
    "no_parse": False,
    "clear": False,
    "is_mod": False,
    "no_unicode": False,
    "highlight_theme": "monokai",
    "no_markdown": False,
    "backticks_bg": 238,
    "latex": False,
    "no_notify": False,
    "prompt_string": "default",
    "timestamp_format": "%H:%M",
    "suggest_aggr": 1,
    "proxy": False,
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


def main():
    """
    Entry point
    """
    parser = argparse.ArgumentParser(description="terminal client for hack.chat",
                                     add_help=False,
                                     formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=45))

    command_group = parser.add_argument_group("commands")
    required_group = parser.add_argument_group("required arguments")
    optional_group = parser.add_argument_group("optional arguments")

    command_group.add_argument("-h", "--help", help="display this help message", action="help")
    command_group.add_argument("-v", "--version", help="display version information", action="version", version="hcclient 1.18.0-git")
    command_group.add_argument("--gen-config", help="generate config file", action="store_true")
    command_group.add_argument("--defaults", help="display default config values", action="store_true")
    command_group.add_argument("--colors", help="display valid color values", action="store_true")
    command_group.add_argument("--themes", help="display valid highlight themes", action="store_true")
    command_group.set_defaults(gen_config=False, colors=False)

    required_group.add_argument("-c", "--channel", help="set channel to join", metavar="CHANNEL")
    required_group.add_argument("-n", "--nickname", help="set nickname to use", metavar="NICKNAME")

    optional_group.add_argument("-p", "--password", help="specify tripcode password", dest="trip_password", metavar="PASSWORD", default=argparse.SUPPRESS)
    optional_group.add_argument("-t", "--trip-password", help=argparse.SUPPRESS, dest="trip_password", default=argparse.SUPPRESS) # deprecated
    optional_group.add_argument("-w", "--websocket", help="specify alternate websocket", dest="websocket_address", metavar="ADDRESS", default=argparse.SUPPRESS)
    optional_group.add_argument("--websocket-address", help=argparse.SUPPRESS, dest="websocket_address", default=argparse.SUPPRESS) # deprecated
    optional_group.add_argument("-l", "--load-config", help="specify config file to load", dest="config_file", metavar="FILE", default=None)
    optional_group.add_argument("--no-config", help="ignore global config file", action="store_true", default=False)
    optional_group.add_argument("--no-hooks", help="ignore global hooks", action="store_true", default=False)
    optional_group.add_argument("--no-parse", help="log received packets as JSON", action="store_true", default=argparse.SUPPRESS)
    optional_group.add_argument("--clear", help="clear console before joining", action="store_true", default=argparse.SUPPRESS)
    optional_group.add_argument("--is-mod", help="enable moderator commands", action="store_true", default=argparse.SUPPRESS)
    optional_group.add_argument("--no-unicode", help="disable unicode UI elements", action="store_true", default=argparse.SUPPRESS)
    optional_group.add_argument("--no-highlight", help=argparse.SUPPRESS, action="store_true", default=False) # deprecated, doesn't do anything
    optional_group.add_argument("--highlight-theme", help="set highlight theme", metavar="THEME", default=argparse.SUPPRESS)
    optional_group.add_argument("--no-markdown", help="disable markdown formatting", action="store_true", default=argparse.SUPPRESS)
    optional_group.add_argument("--backticks-bg", help="set backticks background color", type=int, metavar="0-255", default=argparse.SUPPRESS)
    optional_group.add_argument("--latex", help="enable LaTeX simplifying", action="store_true", default=argparse.SUPPRESS)
    optional_group.add_argument("--no-notify", help="disable desktop notifications", action="store_true", default=argparse.SUPPRESS)
    optional_group.add_argument("--prompt-string", help="set custom prompt string", metavar="STRING", default=argparse.SUPPRESS)
    optional_group.add_argument("--timestamp-format", help="set timestamp format", metavar="FORMAT", default=argparse.SUPPRESS)
    optional_group.add_argument("--suggest-aggr", help="set suggestion aggressiveness", type=int, metavar="0-3", default=argparse.SUPPRESS)
    optional_group.add_argument("--proxy", help="specify proxy to use", metavar="TYPE:HOST:PORT", default=argparse.SUPPRESS)

    args = parser.parse_args()

    del args.no_highlight # deprecated

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
    del args.no_hooks # we dont want to pass this to the client

    client = Client(initialize_config(args, parser))

    if hook:
        client = load_hooks(client)

    client.run()


if __name__ == "__main__":
    main()
