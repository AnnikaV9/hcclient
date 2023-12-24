# Author:    AnnikaV9
# License:   Unlicense

import os
import re
import sys
import ssl
import json
import copy
import time
import random
import shutil
import argparse
import datetime
import threading
import subprocess
import contextlib

import yaml
import notifypy
import colorama
import termcolor
import websocket
import prompt_toolkit

from hcclient.utils.config import validate_config
from hcclient.render.formatter import TextFormatter


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

        self.ws = websocket.WebSocket(sslopt={"cert_reqs": ssl.CERT_NONE} if self.args["ssl_no_verify"] else None)
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

    def print_msg(self, message: str, hist: bool=True) -> None:
        """
        Prints a message to the terminal and adds it to the stdout history
        """
        print(message)

        if hist:
            self.stdout_history.append(message)
            if len(self.stdout_history) > 100:
                self.stdout_history.pop(0)

    def format(self, text: str, text_type: str = "message") -> str:
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

    def push_notification(self, message: str, title: str = "hcclient") -> None:
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

                        if validate_config(option, value):
                            self.args[option] = value
                            self.manage_complete_list()
                            self.prompt_session.completer = self.create_completer()

                            self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                              termcolor.colored("CLIENT", self.args["client_color"]),
                                                              termcolor.colored(f"Set configuration option '{option}' to '{value}'", self.args["client_color"])))

                            if option == "latex" and value and "latex2sympy2" not in sys.modules:
                                try:
                                    import latex2sympy2
                                    self.formatter.latex2sympy = latex2sympy2

                                    self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                                      termcolor.colored("CLIENT", self.args["client_color"]),
                                                                      termcolor.colored("Warning: You have enabled LaTeX simplifying", self.args["client_color"])))
                                    self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                                      termcolor.colored("CLIENT", self.args["client_color"]),
                                                                      termcolor.colored("Idle memory usage will increase significantly", self.args["client_color"])))

                                except ImportError:
                                    self.args["latex"] = False

                                    self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                                      termcolor.colored("CLIENT", self.args["client_color"]),
                                                                      termcolor.colored("Error enabling LaTeX simplifying, optional dependencies not installed", self.args["client_color"])))
                                    self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                                      termcolor.colored("CLIENT", self.args["client_color"]),
                                                                      termcolor.colored("Packages that provide missing dependencies: PyPI: hcclient[latex], AUR: hcclient-latex", self.args["client_color"])))

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
                        if message.split(" ")[0] not in ("/whisper", "/w", "/reply", "/r") or message.startswith(" "):
                            self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                              termcolor.colored("CLIENT", self.args["client_color"]),
                                                              termcolor.colored("Whisper lock active, toggle it off to send messages", self.args["client_color"])))
                            return

                    self.send({"cmd": "chat", "text": message})

    def close(self, error: bool | Exception = False, thread: bool = True) -> None:
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
            try:
                import latex2sympy2
                self.formatter.latex2sympy = latex2sympy2

                self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                  termcolor.colored("CLIENT", self.args["client_color"]),
                                                  termcolor.colored("Warning: You have enabled LaTeX simplifying", self.args["client_color"])))
                self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                  termcolor.colored("CLIENT", self.args["client_color"]),
                                                  termcolor.colored("Idle memory usage will increase significantly", self.args["client_color"])))

            except ImportError:
                self.args["latex"] = False

                self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                  termcolor.colored("CLIENT", self.args["client_color"]),
                                                  termcolor.colored("Error enabling LaTeX simplifying, optional dependencies not installed", self.args["client_color"])))
                self.print_msg("{}|{}| {}".format(termcolor.colored(self.formatted_datetime(), self.args["timestamp_color"]),
                                                  termcolor.colored("CLIENT", self.args["client_color"]),
                                                  termcolor.colored("Packages that provide missing dependencies: PyPI: hcclient[latex], AUR: hcclient-latex", self.args["client_color"])))

        for thread in (self.thread_ping, self.thread_recv, self.thread_cleanup):
            thread.start()

        self.input_manager()
