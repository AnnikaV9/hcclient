#!/usr/bin/python3

import json
import threading
import websocket
import sys
import re
import os
import time
import argparse
import colorama
import datetime
import termcolor
import readline


class Client:

    def __init__(self, args):
        self.args = args
        self.nick = self.args.nickname
        self.online_users = []
        self.ws = websocket.create_connection(self.args.websocket_address)
        self.ws.send(json.dumps({
            "cmd": "join",
            "channel": self.args.channel,
            "nick": "{}#{}".format(self.args.nickname, self.args.trip_password)
        }))

        self.thread_ping = threading.Thread(target=self.ping_thread, daemon=True)
        self.thread_input = threading.Thread(target=self.input_thread, daemon=True)


    def main_thread(self):
        try:
            while self.ws.connected:
                received = json.loads(self.ws.recv())
                packet_receive_time = datetime.datetime.now().strftime("%H:%M")

                if self.args.no_parse:
                    print("\n{}|{}".format(packet_receive_time, received))

                else:
                    match received["cmd"]:
                        case "onlineSet":
                            for nick in received["nicks"]:
                                if self.nick in self.online_users:
                                    self.online_users.remove(self.nick)
                                self.online_users.append(nick)
                                self.channel = received["users"][0]["channel"]

                            if not self.args.no_clear:
                                os.system("cls" if os.name=="nt" else "clear")

                            print("{}|{}|{}".format(termcolor.colored(packet_receive_time, self.args.timestamp_color),
                                                    termcolor.colored("CLIENT", self.args.client_color),                
                                                    termcolor.colored("Channel: {} - Users: {}".format(self.channel, ", ".join(self.online_users)), self.args.client_color)))

                        case "chat":
                            if len(received.get("trip", "")) < 6:
                                tripcode = "NOTRIP"

                            else:
                                tripcode = received.get("trip", "")

                            if received["uType"] == "mod":
                                color_to_use = self.args.mod_nickname_color
                                received["nick"] = "⭐ {}".format(received["nick"]) if not self.args.no_icon else received["nick"]

                            elif received["uType"] == "admin":
                                color_to_use = self.args.admin_nickname_color
                                received["nick"] = "⭐ {}".format(received["nick"]) if not self.args.no_icon else received ["nick"]

                            else:
                                color_to_use = self.args.nickname_color 

                            print("{}|{}|[{}] {}".format(termcolor.colored(packet_receive_time, self.args.timestamp_color),
                                                         termcolor.colored(tripcode, color_to_use),
                                                         termcolor.colored(received["nick"], color_to_use),
                                                         termcolor.colored(received["text"], self.args.message_color)))

                        case "info":
                            if received.get("type") is not None and received.get("type") == "whisper":
                                if len(received.get("trip", "")) < 6:
                                    tripcode = "NOTRIP"

                                else:
                                    tripcode = received.get("trip", "")

                                print("{}|{}|[{}] {}".format(termcolor.colored(packet_receive_time, self.args.timestamp_color),
                                                             termcolor.colored(tripcode, self.args.whisper_color),
                                                             termcolor.colored(received["text"], self.args.whisper_color)))
                            else:
                                print("{}|{}|{}".format(termcolor.colored(packet_receive_time, self.args.timestamp_color),
                                                        termcolor.colored("SERVER", self.args.server_color),
                                                        termcolor.colored(received["text"], self.args.server_color)))

                        case "onlineAdd":
                            self.online_users.append(received["nick"])

                            print("{}|{}|{}".format(termcolor.colored(packet_receive_time, self.args.timestamp_color),
                                                    termcolor.colored("SERVER", self.args.server_color),
                                                    termcolor.colored(received["nick"] + " joined", self.args.server_color)))

                        case "onlineRemove":
                            self.online_users.remove(received["nick"])

                            print("{}|{}|{}".format(termcolor.colored(packet_receive_time, self.args.timestamp_color),
                                                    termcolor.colored("SERVER", self.args.server_color),
                                                    termcolor.colored(received["nick"] + " left", self.args.server_color)))

                        case "emote":
                            if len(received.get("trip", "")) < 6:
                                tripcode = "NOTRIP"

                            else:
                                tripcode = received.get("trip", "")

                            print("{}|{}|{}".format(termcolor.colored(packet_receive_time, self.args.timestamp_color),
                                                    termcolor.colored(tripcode, self.args.emote_color),
                                                    termcolor.colored(received["text"], self.args.emote_color)))

                        case "warn":
                            print("{}|{}|{}".format(termcolor.colored(packet_receive_time, self.args.timestamp_color),
                                                    termcolor.colored("!WARN!", self.args.warning_color),
                                                    termcolor.colored(received["text"], self.args.warning_color)))

        except KeyboardInterrupt:
            None


    def ping_thread(self):
        while self.ws.connected:
            self.ws.send(json.dumps({"cmd": "ping"}))
            time.sleep(60)


    def input_thread(self):
        while self.ws.connected:
            self.send_input(input())


    def send_input(self, message):
        message = message.replace("/n/", "\n")

        if len(message) == 0:
            pass

        else:
            parsed_message = message.partition(" ")
            match parsed_message[0]:
                case "/raw":
                    try:
                        json_to_send = json.loads(parsed_message[2])
                        self.ws.send(json.dumps(json_to_send))

                    except:
                        print("{}|{}|Error sending json: {}".format(termcolor.colored("-NIL-", self.args.timestamp_color),
                                                                    termcolor.colored("CLIENT", self.args.client_color),
                                                                    termcolor.colored(sys.exc_info(), self.args.client_color)))

                case "/list":
                    print("{}|{}|{}".format(termcolor.colored("-NIL-", self.args.timestamp_color),
                                            termcolor.colored("CLIENT", self.args.client_color),
                                            termcolor.colored("Channel: {} - Users: {}".format(self.channel, ", ".join(self.online_users)), self.args.client_color)))

                case "/nick":
                    if re.match("^[A-Za-z0-9_]*$", parsed_message[2]) and len(parsed_message[2]) < 25:
                        self.ws.send(json.dumps({"cmd": "changenick", "nick": parsed_message[2]}))
                        self.nick = parsed_message[2]

                    else:
                        # We send it anyway, the server will handle it and return a warning
                        self.ws.send(json.dumps({"cmd": "changenick", "nick": parsed_message[2]}))

                case "/clear":
                    os.system("cls" if os.name=="nt" else "clear")

                case "/ban":
                    if self.args.is_mod:
                        [self.ws.send(json.dumps({"cmd": "ban", "nick": user})) for user in parsed_message[2].split(" ")]

                case "/unban":
                    if self.args.is_mod:
                        [self.ws.send(json.dumps({"cmd": "unban", "nick": user})) for user in parsed_message[2].split(" ")]

                case "/unbanall":
                    if self.args.is_mod:
                        self.ws.send(json.dumps({"cmd": "unbanall"}))

                case "/dumb":
                    if self.args.is_mod:
                        [self.ws.send(json.dumps({"cmd": "dumb", "nick": user})) for user in parsed_message[2].split(" ")]

                case "/speak":
                    if self.args.is_mod:
                        [self.ws.send(json.dumps({"cmd": "speak", "nick": user})) for user in parsed_message[2].split(" ")]

                case "/moveuser":
                    if self.args.is_mod:
                        message_args = parsed_message[2].split(" ")
                        self.ws.send(json.dumps({"cmd": "moveuser", "nick": message_args[0], "channel": message_args[1]}))

                case "/kick":
                    if self.args.is_mod:
                        [self.ws.send(json.dumps({"cmd": "kick", "nick": user})) for user in parsed_message[2].split(" ")]

                case "/kickasone":
                    if self.args.is_mod:
                        self.ws.send(json.dumps({"cmd": "kick", "nick": parsed_message[2].split(" ")})) # supply a list so everyone gets banished to the same room

                case "/overflow":
                    if self.args.is_mod:
                        [self.ws.send(json.dumps({"cmd": "overflow", "nick": user})) for user in parsed_message[2].split(" ")]

                case "/authtrip":
                    if self.args.is_mod:
                        [self.ws.send(json.dumps({"cmd": "authtrip", "trip": trip})) for trip in parsed_message[2].split(" ")]

                case "/deauthtrip":
                    if self.args.is_mod:
                        [self.ws.send(json.dumps({"cmd": "deauthtrip", "trip": trip})) for trip in parsed_message[2].split(" ")]

                case "/enablecaptcha":
                    if self.args.is_mod:
                        self.ws.send(json.dumps({"cmd": "enablecaptcha"}))

                case "/disablecaptcha":
                    if self.args.is_mod:
                        self.ws.send(json.dumps({"cmd": "disablecaptcha"}))

                case "/lockroom":
                    if self.args.is_mod:
                        self.ws.send(json.dumps({"cmd": "lockroom"}))

                case "/unlockroom":
                    if self.args.is_mod:
                        self.ws.send(json.dumps({"cmd": "unlockroom"}))

                case "/forcecolor":
                    if self.args.is_mod:
                        message_args = parsed_message[2].split(" ")
                        self.ws.send(json.dumps({"cmd": "forcecolor", "nick": message_args[0], "color": message_args[1]}))

                case "/anticmd":
                    if self.args.is_mod:
                        self.ws.send(json.dumps({"cmd": "anticmd"}))

                case "/uwuify":
                    if self.args.is_mod:
                        self.ws.send(json.dumps({"cmd": "uwuify", "nick": parsed_message[2]}))

                case "/help":
                    if parsed_message[2] == "":
                        print("""Any '/n/' will be converted into a linebreak

Client-specific commands:

Raw json packets can be sent with '/raw'
Usage: /raw <json>

User list can be viewed with '/list'
Usage: /list

Chat can be cleared with '/clear'
Usage: /clear

Nickname can be changed with '/nick'
Usage: /nick <newnick>

Server-specific commands should be displayed below:
                        """)
                        self.ws.send(json.dumps({"cmd": "help"}))

                    else:
                        self.ws.send(json.dumps({"cmd": "help", "command": parsed_message[2]}))

                case _:
                    self.ws.send(json.dumps({"cmd": "chat", "text": message}))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Terminal client for connecting to hack.chat servers. Colors are provided by termcolor.")
    required_group = parser.add_argument_group("required arguments")
    optional_group = parser.add_argument_group("optional arguments")
    required_group.add_argument("-c", "--channel", help="specify the channel to join", required=True)
    required_group.add_argument("-n", "--nickname", help="specify the nickname to use", required=True)
    optional_group.add_argument("-t", "--trip-password", help="specify a tripcode password to use when joining")
    optional_group.add_argument("-w", "--websocket-address", help="specify the websocket address to connect to (default: wss://hack-chat/chat-ws)")
    optional_group.add_argument("--no-parse", help="log received packets without parsing",  dest="no_parse", action="store_true")
    optional_group.add_argument("--no-clear", help="disables terminal clearing when joining a new channel", dest="no_clear", action="store_true")
    optional_group.add_argument("--is-mod", help="enables moderator commands",  dest="is_mod", action="store_true")
    optional_group.add_argument("--no-icon", help="disables moderator/admin icon",  dest="no_icon", action="store_true")
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
    optional_group.set_defaults(no_parse=False,
                                no_clear=False,
                                is_mod=False,
                                no_icon=False,
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
                                websocket_address="wss://hack.chat/chat-ws")
    args = parser.parse_args()

    colorama.init()

    client = Client(args)
    client.thread_ping.start()
    client.thread_input.start()
    client.main_thread()

    print("Exiting...")
    colorama.deinit()
