#!/usr/bin/python3
#
# Author:    AnnikaV9
# License:   Unlicense
# Version:   1.7.6-git

# import required modules
import json
import threading
import websocket
import sys
import re
import os
import time
import copy
import argparse
import colorama
import datetime
import termcolor
import shutil
import prompt_toolkit
import notifypy


# define the client class
class Client:

    # initialize the client
    def __init__(self, args):
        colorama.init()

        self.args = args
        self.nick = self.args["nickname"]
        self.online_users = []
        self.online_users_prepended = []

        self.term_content_saved = False
        self.manage_term_contents()

        self.initial_connection()

        self.input_lock = False
        self.prompt_session = prompt_toolkit.PromptSession(reserve_space_for_menu=3)

        self.ping_event = threading.Event()
        self.thread_ping = threading.Thread(target=self.ping_thread, daemon=True)
        self.thread_recv = threading.Thread(target=self.recv_thread, daemon=True)

    # first connection to the server, exit if failed
    def initial_connection(self):
        try:
            self.ws = websocket.create_connection(self.args["websocket_address"])
            self.ws.send(json.dumps({
                "cmd": "join",
                "channel": self.args["channel"],
                "nick": "{}#{}".format(self.nick, self.args["trip_password"])
            }))
            self.reconnecting = False
        
        except:
            self.input_lock = True
            self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                              termcolor.colored("CLIENT", self.args["client_color"]),
                                              termcolor.colored("Error connecting to server: {}".format(sys.exc_info()[1]), self.args["client_color"])),
                                              bypass_lock=True)
            self.close()

    # manage terminal contents
    def manage_term_contents(self):
        if self.args["clear"]:
            if shutil.which("tput"):
                os.system("tput smcup")
                self.term_content_saved = True

            else:
                try:
                    print("Warning!\nThe 'tput' command was not found in your path.\nThis means that the terminal's contents will not be saved.\nExit and re-run without --clear as a workaround.\nPress enter to continue and clear the terminal anyway.")
                    input()

                except (KeyboardInterrupt, EOFError):
                    sys.exit(0)

            os.system("cls" if os.name=="nt" else "clear")

    # print a message to the terminal
    def print_msg(self, message, bypass_lock=False):
        while self.input_lock and not bypass_lock:
            time.sleep(0.01)

        print(message)
    
    def send(self, packet):
        if self.ws.connected:
            self.ws.send(packet)
        
        else:
            self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                              termcolor.colored("CLIENT", self.args["client_color"]),
                                              termcolor.colored("Can't send packet, you're not connected. Run /reconnect", self.args["client_color"])),
                                              bypass_lock=True)

    # ws.recv() loop that receives and parses packets
    def recv_thread(self):
        while self.ws.connected:
            try:
                received = json.loads(self.ws.recv())
                packet_receive_time = datetime.datetime.now().strftime("%H:%M")

                if self.args["no_parse"]:
                    self.print_msg("\n{}|{}".format(packet_receive_time, received))

                match received["cmd"]:
                    case "onlineSet":
                        for nick in received["nicks"]:
                            if self.nick in self.online_users:
                                self.online_users.remove(self.nick)
                            self.online_users.append(nick)
                        
                        for user in self.online_users:
                            self.online_users_prepended.append("@{}".format(user))

                        self.channel = received["users"][0]["channel"]

                        self.print_msg("{}|{}| {}".format(termcolor.colored(packet_receive_time, self.args["timestamp_color"]),
                                                          termcolor.colored("SERVER", self.args["server_color"]),                
                                                          termcolor.colored("Channel: {} - Users: {}".format(self.channel, ", ".join(self.online_users)), self.args["server_color"])))

                    case "chat":
                        if len(received.get("trip", "")) < 6:
                            tripcode = "NOTRIP"

                        else:
                            tripcode = received.get("trip", "")

                        if received["uType"] == "mod":
                            color_to_use = self.args["mod_nickname_color"]
                            received["nick"] = "⭐ {}".format(received["nick"]) if not self.args["no_unicode"] else received["nick"]

                        elif received["uType"] == "admin":
                            color_to_use = self.args["admin_nickname_color"]
                            received["nick"] = "⭐ {}".format(received["nick"]) if not self.args["no_unicode"] else received ["nick"]

                        else:
                            color_to_use = self.args["nickname_color"]

                        if f"@{self.nick}" in received["text"] and not self.args["no_notify"]:
                            notification = notifypy.Notify()
                            notification.title = "hcclient"
                            notification.message = "[{}] {}".format(received["nick"], received["text"])
                            notification.send()

                        self.print_msg("{}|{}| [{}] {}".format(termcolor.colored(packet_receive_time, self.args["timestamp_color"]),
                                                               termcolor.colored(tripcode, color_to_use),
                                                               termcolor.colored(received["nick"], color_to_use),
                                                               termcolor.colored(received["text"], self.args["message_color"])))

                    case "info":
                        if received.get("type") is not None and received.get("type") == "whisper":
                            if len(received.get("trip", "")) < 6:
                                tripcode = "NOTRIP"

                            else:
                                tripcode = received.get("trip", "")

                            if f"@{self.nick}" not in received["text"] and not self.args["no_notify"]:
                                notification = notifypy.Notify()
                                notification.title = "hcclient"
                                notification.message = "{}".format(received["text"])
                                notification.send()

                            self.print_msg("{}|{}| {}".format(termcolor.colored(packet_receive_time, self.args["timestamp_color"]),
                                                              termcolor.colored(tripcode, self.args["whisper_color"]),
                                                              termcolor.colored(received["text"], self.args["whisper_color"])))
                        else:
                            self.print_msg("{}|{}| {}".format(termcolor.colored(packet_receive_time, self.args["timestamp_color"]),
                                                              termcolor.colored("SERVER", self.args["server_color"]),
                                                              termcolor.colored(received["text"], self.args["server_color"])))

                    case "onlineAdd":
                        self.online_users.append(received["nick"])
                        self.online_users_prepended.append("@{}".format(received["nick"]))

                        self.print_msg("{}|{}| {}".format(termcolor.colored(packet_receive_time, self.args["timestamp_color"]),
                                                          termcolor.colored("SERVER", self.args["server_color"]),
                                                          termcolor.colored(received["nick"] + " joined", self.args["server_color"])))

                    case "onlineRemove":
                        self.online_users.remove(received["nick"])
                        self.online_users_prepended.remove("@{}".format(received["nick"]))

                        self.print_msg("{}|{}| {}".format(termcolor.colored(packet_receive_time, self.args["timestamp_color"]),
                                                          termcolor.colored("SERVER", self.args["server_color"]),
                                                          termcolor.colored(received["nick"] + " left", self.args["server_color"])))

                    case "emote":
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
                        if received["text"] == "Nickname taken":
                            self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                              termcolor.colored("CLIENT", self.args["client_color"]),
                                                              termcolor.colored("Try Running /nick <newnick> and /reconnect", self.args["client_color"])))

            except:
                if self.reconnecting:
                    self.close()

                else:
                    self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                      termcolor.colored("CLIENT", self.args["client_color"]),
                                                      termcolor.colored("Disconnected from server: {}".format(sys.exc_info()[1]), self.args["client_color"])))
                    self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                      termcolor.colored("CLIENT", self.args["client_color"]),
                                                      termcolor.colored("Try running /reconnect", self.args["client_color"])))
                    self.ping_event.set()
                    self.close(thread=True)

    # ping thread acting as a heartbeat
    def ping_thread(self):
        while self.ws.connected and not self.ping_event.is_set():
            self.send(json.dumps({"cmd": "ping"}))
            self.ping_event.wait(60)

    # input loop that draws the prompt and handles input
    def input_loop(self):
        with prompt_toolkit.patch_stdout.patch_stdout(raw=True):
            while True:
                self.input_lock = True

                if self.args["prompt_string"]:
                    prompt_string = self.args["prompt_string"]

                else:
                    prompt_string = "> " if self.args["no_unicode"] else "❯ "

                nick_completer = prompt_toolkit.completion.WordCompleter(self.online_users_prepended, match_middle=True, ignore_case=True, sentence=True)

                self.input_lock = False

                try:
                    self.send_input(self.prompt_session.prompt(prompt_string , completer=nick_completer, wrap_lines=False))

                except (KeyboardInterrupt, EOFError):
                    self.close(thread=False)

                except:
                    self.close(error=sys.exc_info(), thread=False)

    # send input to the server and handle client commands
    def send_input(self, message):
        self.input_lock = True
        print("\033[A{}\033[A".format(" " * shutil.get_terminal_size().columns))

        try:
            message = message.replace("\\n", "\n")

        except AttributeError:
            return

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

                case "/nick":
                    if re.match("^[A-Za-z0-9_]*$", parsed_message[2]) and len(parsed_message[2]) < 25:
                        if self.ws.connected:
                            self.send(json.dumps({"cmd": "changenick", "nick": parsed_message[2]}))

                        self.nick = parsed_message[2]
                        self.args["nickname"] = parsed_message[2]

                    else:
                        self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored("Nickname should a maximum of 24 characters and consist of letters, numbers and underscores.", self.args["client_color"])),
                                                          bypass_lock=True)

                case "/clear":
                    if self.args["clear"]:
                        os.system("cls" if os.name=="nt" else "clear")

                    else:
                        self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored("Clearing is disabled, enable with the --clear flag or run `/configset clear true`", self.args["client_color"])),
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
                        self.ws = websocket.create_connection(self.args["websocket_address"])
                        self.ws.send(json.dumps({
                            "cmd": "join",
                            "channel": self.args["channel"],
                            "nick": "{}#{}".format(self.nick, self.args["trip_password"])
                        }))
                        self.reconnecting = False

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
                    if message_args[0] in self.args and message_args[0] not in ("config_file", "channel", "nickname", "aliases"):
                        self.args[message_args[0]] = " ".join(message_args[1:])
                        self.args[message_args[0]] = False if self.args[message_args[0]] == "false" else self.args[message_args[0]]
                        self.args[message_args[0]] = True if self.args[message_args[0]] == "true" else self.args[message_args[0]]
                        self.args[message_args[0]] = None if self.args[message_args[0]] in ("none", "null", "default") else self.args[message_args[0]]
                        self.print_msg("{}|{}| {}".format(termcolor.colored("-NIL-", self.args["timestamp_color"]),
                                                          termcolor.colored("CLIENT", self.args["client_color"]),
                                                          termcolor.colored("Set configuration value '{}' to '{}'".format(message_args[0], self.args[message_args[0]]), self.args["client_color"])),
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
                                                      termcolor.colored("Running config:\n" + "\n".join("{}: {}".format(option, value) for option, value in self.args.items()), self.args["client_color"])),
                                                      bypass_lock=True)

                case "/save":
                    if self.args["config_file"]:
                        config = copy.deepcopy(self.args)
                        for arg in ("config_file", "channel", "nickname"):
                            config.pop(arg)

                        try:
                            with open(self.args["config_file"], "w") as config_file:
                                json.dump(config, config_file, indent=2)
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
                        [self.send(json.dumps({"cmd": "ban", "nick": user})) for user in parsed_message[2].split(" ")]

                case "/unban":
                    if self.args["is_mod"]:
                        [self.send(json.dumps({"cmd": "unban", "nick": user})) for user in parsed_message[2].split(" ")]

                case "/unbanall":
                    if self.args["is_mod"]:
                        self.send(json.dumps({"cmd": "unbanall"}))

                case "/dumb":
                    if self.args["is_mod"]:
                        [self.send(json.dumps({"cmd": "dumb", "nick": user})) for user in parsed_message[2].split(" ")]

                case "/speak":
                    if self.args["is_mod"]:
                        [self.send(json.dumps({"cmd": "speak", "nick": user})) for user in parsed_message[2].split(" ")]

                case "/moveuser":
                    if self.args["is_mod"]:
                        message_args = parsed_message[2].split(" ")
                        self.send(json.dumps({"cmd": "moveuser", "nick": message_args[0], "channel": message_args[1]}))

                case "/kick":
                    if self.args["is_mod"]:
                        [self.send(json.dumps({"cmd": "kick", "nick": user})) for user in parsed_message[2].split(" ")]

                case "/kickasone":
                    if self.args["is_mod"]:
                        self.send(json.dumps({"cmd": "kick", "nick": parsed_message[2].split(" ")})) # supply a list so everyone gets banished to the same room

                case "/overflow":
                    if self.args["is_mod"]:
                        [self.send(json.dumps({"cmd": "overflow", "nick": user})) for user in parsed_message[2].split(" ")]

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
                        self.send(json.dumps({"cmd": "forcecolor", "nick": message_args[0], "color": message_args[1]}))

                case "/anticmd":
                    if self.args["is_mod"]:
                        self.send(json.dumps({"cmd": "anticmd"}))

                case "/uwuify":
                    if self.args["is_mod"]:
                        self.send(json.dumps({"cmd": "uwuify", "nick": parsed_message[2]}))

                case "/help":
                    if parsed_message[2] == "":
                        self.print_msg("""Any '\\n' will be converted into a linebreak.

Client-specific commands:
/raw <json>
  Sends json directly to the server
  without parsing.
/list
  Lists users in the channel.
/clear
  Clears the terminal.
/nick <newnick>
  Changes your nickname.
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
  effect immediately. Values are not
  checked, an invalid value will
  crash the client. Use carefully.
/configdump
  Prints the current configuration.
/save
  Saves the current configuration
  to the loaded configuration file.
  Will also save aliases.
/quit
  Exits the client.

Server-specific commands should be displayed below:""", bypass_lock=True)
                        self.send(json.dumps({"cmd": "help"}))

                    else:
                        self.send(json.dumps({"cmd": "help", "command": parsed_message[2]}))

                case _:
                    self.send(json.dumps({"cmd": "chat", "text": message}))

    # close the client or thread and print an error if there is one
    def close(self, error=False, thread=True): 
        if not thread:
            colorama.deinit()

        if self.term_content_saved and not thread:
            os.system("tput rmcup")

        if error:
            print(error)
            sys.exit(1)

        else:
            sys.exit(0)


# generate a config file in the current directory
def generate_config(config):
    config = vars(config)
    for arg in ("gen_config", "config_file", "channel", "nickname"):
            config.pop(arg)

    try:
        with open("config.json", "x") as config_file:
            json.dump(config, config_file, indent=2)
            print("Configuration written to config.json")

    except:
        sys.exit("Error generating configuration!\n{}".format(sys.exc_info()[1]))


# load a config file from the specified path
def load_config(filepath):
    try:
        with open(filepath, "r") as config_file:
            config = json.load(config_file)

            missing_args = []
            for key in ("trip_password", "websocket_address", "no_parse",
                       "clear", "is_mod", "no_unicode", "no_notify",
                       "prompt_string", "message_color", "whisper_color",
                       "emote_color", "nickname_color", "warning_color",
                       "server_color", "client_color", "timestamp_color",
                       "mod_nickname_color", "admin_nickname_color", "aliases"):
                if key not in config:
                    missing_args.append(key)

            if len(missing_args) > 0:
                raise ValueError("{} is missing the following option(s): {}".format(filepath, ", ".join(missing_args)))

            return config

    except:
        sys.exit("Error loading configuration!\n{}".format(sys.exc_info()[1]))


# initialize the configuration options
def initialize_config(args):
    if args.gen_config:
        args.aliases = {}
        generate_config(args)
        sys.exit(0)

    if args.config_file:
        config = load_config(args.config_file)
        config["nickname"] = args.nickname
        config["channel"] = args.channel
        config["config_file"] = args.config_file

    else:
        def_config_file = os.path.join(os.getenv("APPDATA"), "hcclient", "config.json") if os.name == "nt" else os.path.join(os.getenv("HOME"), ".config", "hcclient", "config.json")

        if os.path.isfile(def_config_file):
            config = load_config(def_config_file)
            config["nickname"] = args.nickname
            config["channel"] = args.channel
            config["config_file"] = def_config_file
        
        else:
            config = vars(args)
            config["aliases"] = {}
            config.pop("gen_config")

    return config

# parse arguments and run the client
def main():
    parser = argparse.ArgumentParser(description="Terminal client for connecting to hack.chat servers. Colors are provided by termcolor.")
    required_group = parser.add_argument_group("required arguments")
    optional_group = parser.add_argument_group("optional arguments")
    required_group.add_argument("-c", "--channel", help="specify the channel to join", required=True)
    required_group.add_argument("-n", "--nickname", help="specify the nickname to use", required=True)
    optional_group.add_argument("-l", "--load-config", help="specify a config file to load", dest="config_file")
    optional_group.add_argument("-t", "--trip-password", help="specify a tripcode password to use when joining")
    optional_group.add_argument("-w", "--websocket-address", help="specify the websocket address to connect to (default: wss://hack-chat/chat-ws)")
    optional_group.add_argument("--no-parse", help="log received packets without parsing", action="store_true")
    optional_group.add_argument("--clear", help="enables clearing of the terminal", action="store_true")
    optional_group.add_argument("--is-mod", help="enables moderator commands", action="store_true")
    optional_group.add_argument("--no-unicode", help="disables moderator/admin icon and unicode characters in the UI", action="store_true")
    optional_group.add_argument("--no-notify", help="disables desktop notifications", action="store_true")
    optional_group.add_argument("--prompt-string", help="sets the prompt string (default: '❯ ' or '> ' if --no-unicode)")
    optional_group.add_argument("--message-color", help="sets the message color (default: white)")
    optional_group.add_argument("--whisper-color", help="sets the whisper color (default: green)")
    optional_group.add_argument("--emote-color", help="sets the emote color (default: green)")
    optional_group.add_argument("--nickname-color", help="sets the nickname color (default: white)")
    optional_group.add_argument("--warning-color", help="sets the warning color (default: yellow)")
    optional_group.add_argument("--server-color", help="sets the server color (default: green)")
    optional_group.add_argument("--client-color", help="sets the client color (default: green)")
    optional_group.add_argument("--timestamp-color", help="sets the timestamp color (default: white)")
    optional_group.add_argument("--mod-nickname-color", help="sets the moderator nickname color (default: cyan)")
    optional_group.add_argument("--admin-nickname-color", help="sets the admin nickname color (default: red)")
    optional_group.add_argument("--gen-config", help="generates a config file with provided arguments", action="store_true")
    optional_group.add_argument("--version", help="displays the version and exits", action="version", version="hcclient 1.7.6-git")
    optional_group.set_defaults(no_parse=False,
                                clear=False,
                                is_mod=False,
                                no_unicode=False,
                                no_notify=False,
                                prompt_string=None,
                                message_color="white",
                                whisper_color="green",
                                emote_color="green",
                                nickname_color="white",
                                warning_color="yellow",
                                server_color="green",
                                client_color="green",
                                timestamp_color="white",
                                mod_nickname_color="cyan",
                                admin_nickname_color="red",
                                trip_password="",
                                websocket_address="wss://hack.chat/chat-ws",
                                gen_config=False,
                                config_file=None)
    args = parser.parse_args()

    client = Client(initialize_config(args))
    client.thread_ping.start()
    client.thread_recv.start()
    client.input_loop()


if __name__ == "__main__":
    main()
