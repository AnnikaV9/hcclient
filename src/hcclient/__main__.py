#!/usr/bin/python3
#
# Author:    AnnikaV9
# License:   Unlicense
# Version:   1.13.0-git

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
import contextlib
import datetime
import time
import termcolor
import shutil
import prompt_toolkit
import notifypy
import yaml

class Client:
    """
    The main client class
    """
    def __init__(self, args: dict) -> None:
        """
        Initializes the client and environment, sets up variables and threads
        """
        colorama.init()
        self.bindings = prompt_toolkit.key_binding.KeyBindings()

        self.args = args
        self.nick = self.args["nickname"]
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

        self.term_content_saved = False
        self.manage_term_contents()
        self.stdout_history = []
        self.updatable_messages = []
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


    def connect_to_server(self) -> None:
        """
        Connects to the websocket server and send the join packet
        Uses a proxy if specified
        """
        connect_status = "Connecting to {}...".format(self.args["websocket_address"]) if not self.args["proxy"] else "Connecting to {} through proxy {}...".format(self.args["websocket_address"], self.args["proxy"])

        self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                          termcolor.colored(connect_status, self.args["client_color"])))

        if self.args["proxy"]:
            self.ws.connect(self.args["websocket_address"], http_proxy_host=self.args["proxy"].split(":")[1], http_proxy_port=self.args["proxy"].split(":")[2], proxy_type=self.args["proxy"].split(":")[0].lower())

        else:
            self.ws.connect(self.args["websocket_address"])

        self.ws.send(json.dumps({
            "cmd": "join",
            "channel": self.args["channel"],
            "nick": "{}#{}".format(self.nick, self.args["trip_password"])
        }))

    def reconnect_to_server(self) -> None:
        """
        Reconnects to the websocket server
        Runs in a separate temporary thread
        """
        self.reconnecting = True

        self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
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
        if option in ("timestamp_color", "client_color", "server_color", "nickname_color",
                      "self_nickname_color", "mod_nickname_color", "admin_nickname_color",
                      "message_color", "emote_color", "whisper_color", "warning_color"):
            return value in termcolor.COLORS

        elif option in ("no_unicode", "no_notify", "no_parse", "clear", "is_mod"):
            return isinstance(value, bool)

        elif option in ("websocket_address", "trip_password", "prompt_string"):
            return isinstance(value, str)

        elif option in ("aliases", "ignored"):
            if not isinstance(value, dict):
                return False

            match option:
                case "aliases":
                    for alias, replacement in value.items():
                        if not isinstance(alias, str) or not isinstance(replacement, str):
                            return False

                case "ignored":
                    if "trips" not in value or "hashes" not in value:
                        return False

                    if not isinstance(value["trips"], list) or not isinstance(value["hashes"], list):
                        return False

        elif option == "proxy":
            if value and not isinstance(value, str):
                return False

        elif option == "suggest_aggr":
            return value in range(4)

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

    def print_msg(self, message: str) -> None:
        """
        Prints a message to the terminal and adds it to the stdout history
        """
        print(message)

        self.stdout_history.append(message)
        if len(self.stdout_history) > 100:
            self.stdout_history.pop(0)

    def send(self, packet: str) -> None:
        """
        Sends a packet to the server if connected, otherwise prints an error
        """
        if self.ws.connected:
            self.ws.send(packet)

        else:
            self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                              termcolor.colored("CLIENT", self.args["client_color"]),
                                              termcolor.colored("Can't send packet, not connected to server. Run /reconnect", self.args["client_color"])))

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

    def level_to_utype(self, level: int) -> str:
        """
        Converts a user level to a user type
        """
        match level:
            case 9999999:
                return "admin"

            case 999999:
                return "mod"

            case _:
                return "user"

    def cleanup_updatables(self) -> None:
        """
        Removes expired updatable messages
        """
        self.updatable_messages_lock.acquire()
        for message in self.updatable_messages:
            if time.time() - message["sent"] > 6 * 60:
                self.updatable_messages.remove(message)
                timestamp = datetime.datetime.now().strftime("%H:%M")

                self.print_msg("{}|{}| [{}] [{}] {}".format(termcolor.colored(timestamp, self.args["timestamp_color"]),
                                                            termcolor.colored(message["trip"], message["color"]),
                                                            "Expired.ID: {}".format(message["unique_id"]),
                                                            termcolor.colored(message["nick"], message["color"]),
                                                            termcolor.colored(message["text"], self.args["message_color"])))

        self.updatable_messages_lock.release()

    def cleanup_thread(self) -> None:
        """
        Thread that runs cleanup tasks every 30 seconds
        """
        while True:
            self.cleanup_updatables()
            # more cleanup tasks here
            threading.Event().wait(30)

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
                    continue

                match received["cmd"]:
                    case "onlineSet":
                        for nick in received["nicks"]:
                            self.online_users.append(nick)

                        for user_details in received["users"]:
                            self.online_users_details[user_details["nick"]] = {"Trip": user_details["trip"], "Type": self.level_to_utype(user_details["level"]), "Hash": user_details["hash"]}

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

                        match self.level_to_utype(received["level"]):
                            case "mod":
                                color_to_use = self.args["mod_nickname_color"] if self.nick != received["nick"] else self.args["self_nickname_color"]
                                received["nick"] = "{} {}".format(chr(11088), received["nick"]) if not self.args["no_unicode"] else received["nick"]

                            case "admin":
                                color_to_use = self.args["admin_nickname_color"] if self.nick != received["nick"] else self.args["self_nickname_color"]
                                received["nick"] = "{} {}".format(chr(11088), received["nick"]) if not self.args["no_unicode"] else received ["nick"]
                                tripcode = "Admin"

                            case _:
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

                        if "customId" in received:
                            self.updatable_messages_lock.acquire()
                            for message in self.updatable_messages:
                                if message["customId"] == received["customId"] and message["userid"] == received["userid"]:
                                    self.updatable_messages.remove(message)
                                    break

                            self.updatable_messages.append({
                                "customId": received["customId"],
                                "userid": received["userid"],
                                "text": received["text"],
                                "sent": time.time(),
                                "trip": tripcode,
                                "nick": received["nick"],
                                "color": color_to_use,
                                "unique_id": abs(hash(str(received["userid"]) + received["customId"])) % 100000
                            })
                            self.updatable_messages_lock.release()

                            self.print_msg("{}|{}| [{}] [{}] {}".format(termcolor.colored(packet_receive_time, self.args["timestamp_color"]),
                                                                        termcolor.colored(tripcode, color_to_use),
                                                                        "Updatable.ID: {}".format(self.updatable_messages[-1]["unique_id"]),
                                                                        termcolor.colored(received["nick"], color_to_use),
                                                                        termcolor.colored(received["text"], self.args["message_color"])))

                        else:
                            self.print_msg("{}|{}| [{}] {}".format(termcolor.colored(packet_receive_time, self.args["timestamp_color"]),
                                                                   termcolor.colored(tripcode, color_to_use),
                                                                   termcolor.colored(received["nick"], color_to_use),
                                                                   termcolor.colored(received["text"], self.args["message_color"])))

                    case "updateMessage":
                        self.updatable_messages_lock.acquire()
                        match received["mode"]:
                            case "overwrite":
                                for message in self.updatable_messages:
                                    if message["customId"] == received["customId"] and message["userid"] == received["userid"]:
                                        message["text"] = received["text"]
                                        break

                            case "append":
                                for message in self.updatable_messages:
                                    if message["customId"] == received["customId"] and message["userid"] == received["userid"]:
                                        message["text"] += received["text"]
                                        break

                            case "prepend":
                                for message in self.updatable_messages:
                                    if message["customId"] == received["customId"] and message["userid"] == received["userid"]:
                                        message["text"] = received["text"] + message["text"]
                                        break

                            case "complete":
                                for message in self.updatable_messages:
                                    if message["customId"] == received["customId"] and message["userid"] == received["userid"]:

                                        self.print_msg("{}|{}| [{}] [{}] {}".format(termcolor.colored(packet_receive_time, self.args["timestamp_color"]),
                                                                                    termcolor.colored(message["trip"], message["color"]),
                                                                                    "Completed.ID: {}".format(message["unique_id"]),
                                                                                    termcolor.colored(message["nick"], message["color"]),
                                                                                    termcolor.colored(message["text"], self.args["message_color"])))

                                        self.updatable_messages.remove(message)
                                        break

                        self.updatable_messages_lock.release()

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
                        self.online_users_details[received["nick"]] = {"Trip": received["trip"], "Type": self.level_to_utype(received["level"]), "Hash": received["hash"]}

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

        except Exception as e:
            self.online_users = []
            self.online_users_details = {}
            self.online_ignored_users = []

            self.manage_complete_list()

            if self.args["is_mod"]:
                self.auto_complete_list.extend(self.mod_command_list)

            if self.reconnecting:
                self.close()

            else:
                self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                  termcolor.colored("CLIENT", self.args["client_color"]),
                                                  termcolor.colored(f"Disconnected from server: {e}", self.args["client_color"])))
                self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                  termcolor.colored("CLIENT", self.args["client_color"]),
                                                  termcolor.colored("Reconnecting in 60 seconds, run /reconnect do it immediately", self.args["client_color"])))
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

        for alias in self.args["aliases"]:
            word_list[:] = [part if part != f"${alias}" else self.args["aliases"][alias] for part in word_list]

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

        else:
            self.exit_attempted = True
            self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
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

        else:
            return "> " if self.args["no_unicode"] else "❯ "

    def create_completer(self) -> prompt_toolkit.completion.Completer | None:
        """
        Creates a completer instance based on the suggest_aggr option
        """
        base_completer = prompt_toolkit.completion.WordCompleter(
            self.auto_complete_list,
            match_middle=False if self.args["suggest_aggr"] == 1 else True,
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

                    except Exception as e:
                        self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                                              termcolor.colored("CLIENT", self.args["client_color"]),
                                                                              termcolor.colored(f"Error sending json: {e}", self.args["client_color"])))

                case "/list":
                    self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                      termcolor.colored("CLIENT", self.args["client_color"]),
                                                      termcolor.colored("Channel: {} - Users: {}".format(self.channel, ", ".join(self.online_users)), self.args["client_color"])))

                case "/profile":
                    target = parsed_message[2].lstrip("@")
                    if target in self.online_users:
                        ignored = "Yes" if target in self.online_ignored_users else "No"
                        profile = "{}'s profile:\n".format(target) + "\n".join("{}: {}".format(option, value) for option, value in self.online_users_details[target].items()) + "\nIgnored: {}".format(ignored)

                        self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored(profile, self.args["client_color"])))


                    else:
                        self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored("No such user: '{}'".format(target), self.args["client_color"])))

                case "/nick":
                    if re.match("^[A-Za-z0-9_]*$", parsed_message[2]) and 0 < len(parsed_message[2]) < 25:
                        if self.ws.connected:
                            self.send(json.dumps({"cmd": "changenick", "nick": parsed_message[2]}))

                        self.nick = parsed_message[2]
                        self.args["nickname"] = parsed_message[2]

                    else:
                        self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored("Nickname must consist of up to 24 letters, numbers, and underscores", self.args["client_color"])))

                case "/clear":
                    if self.args["clear"]:
                        os.system("cls" if os.name=="nt" else "clear")

                    else:
                        self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored("Clearing is disabled, enable with the --clear flag or run `/configset clear true`", self.args["client_color"])))

                case "/wlock":
                    self.whisper_lock = not self.whisper_lock

                    self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                      termcolor.colored("CLIENT", self.args["client_color"]),
                                                      termcolor.colored("Toggled whisper lock to {}".format(self.whisper_lock), self.args["client_color"])))

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
                                                          termcolor.colored("Ignoring trip '{}' and hash '{}', run /save to persist".format(trip_to_ignore, self.online_users_details[target]["Hash"]), self.args["client_color"])))

                    else:
                        self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored("No such user: '{}'".format(target), self.args["client_color"])))

                case "/unignoreall":
                    self.online_ignored_users = []
                    self.args["ignored"] = {"trips": [], "hashes": []}

                    self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                      termcolor.colored("CLIENT", self.args["client_color"]),
                                                      termcolor.colored("Unignored all trips/hashes, run /save to persist", self.args["client_color"])))

                case "/reconnect":
                    self.timed_reconnect.cancel()
                    threading.Thread(target=self.reconnect_to_server, daemon=True).start()

                case "/set":
                    message_args = parsed_message[2].split(" ")
                    if len(message_args) < 2:
                        self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored("Alias/Value cannot be empty", self.args["client_color"])))

                    else:
                        self.args["aliases"][message_args[0]] = " ".join(message_args[1:])

                        self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored("Set alias '{}' = '{}'".format(message_args[0], self.args["aliases"][message_args[0]]), self.args["client_color"])))

                case "/unset":
                    try:
                        self.args["aliases"].pop(parsed_message[2])

                        self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored("Unset alias '{}'".format(parsed_message[2]), self.args["client_color"])))

                    except KeyError:
                        self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored("Alias '{}' isn't defined".format(parsed_message[2]), self.args["client_color"])))

                case "/configset":
                    message_args = parsed_message[2].lower().split(" ")
                    if message_args[0] in self.args and message_args[0] not in ("config_file", "channel", "nickname", "aliases", "ignored"):

                        value, option = " ".join(message_args[1:]), message_args[0]
                        match value.lower():
                            case "false":
                                value = False

                            case "true":
                                value = True

                            case "none" | "null":
                                value = None

                        if option == "suggest_aggr":
                            with contextlib.suppress(Exception):
                                value = int(value)

                        if Client.validate_config(option, value):
                            self.args[option] = value
                            self.manage_complete_list()
                            self.prompt_session.completer = self.create_completer()

                            self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                              termcolor.colored("CLIENT", self.args["client_color"]),
                                                              termcolor.colored("Set configuration option '{}' to '{}'".format(option, value), self.args["client_color"])))

                        else:
                            self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                              termcolor.colored("CLIENT", self.args["client_color"]),
                                                              termcolor.colored("Error setting configuration: Invalid value '{}' for option '{}'".format(value, option), self.args["client_color"])))

                    else:
                        problem = "Invalid" if message_args[0] not in self.args else "Read-only"

                        self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored("Error setting configuration: {} option '{}'".format(problem, message_args[0]), self.args["client_color"])))

                case "/configdump":
                    self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                      termcolor.colored("CLIENT", self.args["client_color"]),
                                                      termcolor.colored("Active configuration:\n" + "\n".join("{}: {}".format(option, value) for option, value in self.args.items()), self.args["client_color"])))

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
                                                                  termcolor.colored("Configuration saved to {}".format(self.args["config_file"]), self.args["client_color"])))

                        except Exception as e:
                            self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                              termcolor.colored("CLIENT", self.args["client_color"]),
                                                              termcolor.colored(f"Error saving configuration: {e}", self.args["client_color"])))

                    else:
                        self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored("Unable to save configuration without a loaded config file, use --load-config", self.args["client_color"])))

                case "/reprint":
                    print("\n".join(self.stdout_history))

                case "/quit":
                    raise SystemExit

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
                                                              termcolor.colored("User/Channel cannot be empty", self.args["client_color"])))

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
                                                              termcolor.colored("User/Color cannot be empty", self.args["client_color"])))

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
The entire buffer can be cleared with ctrl+l.

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
/reprint
  Prints the last 100 lines of
  output, even if they have been
  cleared with /clear.
/quit
  Exits the client."""
                        mod_help_text = """\n\nClient-based mod commands:
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
                        server_help_text = "\n\nServer-based commands should be displayed below:"
                        display = help_text + mod_help_text + server_help_text if self.args["is_mod"] else help_text + server_help_text

                        self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored(display, self.args["client_color"])))

                        self.send(json.dumps({"cmd": "help"}))

                    else:
                        self.send(json.dumps({"cmd": "help", "command": parsed_message[2]}))

                case _:
                    if self.whisper_lock:
                        if not message.split(" ")[0] in ("/whisper", "/w", "/reply", "/r") or message.startswith(" "):
                            self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                              termcolor.colored("CLIENT", self.args["client_color"]),
                                                              termcolor.colored("Whisper lock active, toggle it off to send messages", self.args["client_color"])))
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
            print(f"{type(error).__name__}: {error}")
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

    except Exception as e:
        sys.exit("{}: error: {}".format(sys.argv[0], e))


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
                       "timestamp_color", "mod_nickname_color", "suggest_aggr",
                       "admin_nickname_color", "ignored", "aliases", "proxy"):
                if key not in config:
                    missing_args.append(key)

            if len(missing_args) > 0:
                raise ValueError("{} is missing the following option(s): {}".format(filepath, ", ".join(missing_args)))

            return config

    except Exception as e:
        sys.exit("{}: error: {}".format(sys.argv[0], e))


def initialize_config(args: argparse.Namespace, parser: argparse.ArgumentParser) -> dict:
    """
    Initializes the configuration and returns a dictionary
    """
    default_colors = {
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
        "admin_nickname_color": "red"
    }
    for color in default_colors:
        args.__dict__[color] = default_colors[color]

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
    parser = argparse.ArgumentParser(description="terminal client for connecting to hack.chat", add_help=False)
    command_group = parser.add_argument_group("commands")
    required_group = parser.add_argument_group("required arguments")
    optional_group = parser.add_argument_group("optional arguments")
    command_group.add_argument("-h", "--help", help="display this help message", action="help")
    command_group.add_argument("--gen-config", help="generate a config file with provided arguments", action="store_true")
    command_group.add_argument("--colors", help="display a list of valid colors", action="store_true")
    command_group.add_argument("--version", help="display version information", action="version", version="hcclient 1.13.0-git")
    command_group.set_defaults(gen_config=False, colors=False)
    required_group.add_argument("-c", "--channel", help="specify the channel to join")
    required_group.add_argument("-n", "--nickname", help="specify the nickname to use")
    optional_group.add_argument("-t", "--trip-password", help="specify a tripcode password to use when joining")
    optional_group.add_argument("-w", "--websocket-address", help="specify the websocket address to connect to (default: wss://hack-chat/chat-ws)")
    optional_group.add_argument("-l", "--load-config", help="specify a config file to load", dest="config_file")
    optional_group.add_argument("--no-config", help="disable loading of the default config file", action="store_true")
    optional_group.add_argument("--no-parse", help="log received packets without parsing", action="store_true")
    optional_group.add_argument("--clear", help="enable clearing of the terminal", action="store_true")
    optional_group.add_argument("--is-mod", help="enable moderator commands", action="store_true")
    optional_group.add_argument("--no-unicode", help="disable moderator/admin icon and unicode characters in the UI", action="store_true")
    optional_group.add_argument("--no-notify", help="disable desktop notifications", action="store_true")
    optional_group.add_argument("--prompt-string", help="set the prompt string (default: '❯ ' or '> ' if --no-unicode)")
    optional_group.add_argument("--suggest-aggr", help="set the suggestion aggressiveness (default: 1)", type=int, choices=[0, 1, 2, 3])
    optional_group.add_argument("--proxy", help="specify a proxy to use (format: TYPE:HOST:PORT) (default: None)")
    optional_group.set_defaults(config_file=None, no_config=False, no_parse=False, clear=False,
                                is_mod=False, no_unicode=False, no_notify=False, prompt_string="default",
                                suggest_aggr=1, trip_password="", websocket_address="wss://hack.chat/chat-ws",
                                proxy=False)

    if parser.parse_args().colors:
        print("Valid colors: \n{}".format("\n".join(termcolor.COLORS)))
        sys.exit(0)

    client = Client(initialize_config(parser.parse_args(), parser))
    client.thread_ping.start()
    client.thread_recv.start()
    client.thread_cleanup.start()
    client.input_manager()


if __name__ == "__main__":
    main()
