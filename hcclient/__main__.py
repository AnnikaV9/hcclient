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
                    if received["cmd"] == "onlineSet":
                        for nick in received["nicks"]:
                            if self.nick in self.online_users:
                                self.online_users.remove(self.nick)
                            self.online_users.append(nick)
                            self.channel = received["users"][0]["channel"]

                        if not self.args.no_clear:
                            os.system('cls' if os.name=='nt' else 'clear')

                        print("{}|{}|{}".format(termcolor.colored(packet_receive_time, self.args.timestamp_color),
                                                termcolor.colored("CLIENT", self.args.client_color),                
                                                termcolor.colored("You are now connected to channel: {} - Type '/help' for a list of commands you can use with this client\n\n".format(self.channel), self.args.client_color)))

                    elif received["cmd"] == "chat":
                        if len(received.get("trip", "")) < 6:
                            tripcode = "NOTRIP"

                        else:
                            tripcode = received.get("trip", "")
                        
                        if received["uType"] == "mod":
                            color_to_use = self.args.mod_nickname_color
                        
                        elif received["uType"] == "admin":
                            color_to_use = self.args.admin_nickname_color

                        else:
                            color_to_use = self.args.nickname_color
                        
                        print("{}|{}|[{}] {}".format(termcolor.colored(packet_receive_time, self.args.timestamp_color),
                                                     termcolor.colored(tripcode, color_to_use),
                                                     termcolor.colored(received["nick"], color_to_use),
                                                     termcolor.colored(received["text"], self.args.message_color)))

                    elif received["cmd"] == "onlineAdd":
                        self.online_users.append(received["nick"])
                        print("{}|{}|{}".format(termcolor.colored(packet_receive_time, self.args.timestamp_color),
                                                       termcolor.colored("SERVER", self.args.server_color),
                                                       termcolor.colored(received["nick"] + " joined", self.args.server_color)))

                    elif received["cmd"] == "onlineRemove":
                        self.online_users.remove(received["nick"])
                        print("{}|{}|{}".format(termcolor.colored(packet_receive_time, self.args.timestamp_color),
                                                     termcolor.colored(tripcode, self.args.server_color),
                                                     termcolor.colored(received["nick"] + " left", self.args.server_color)))

                    elif received["cmd"] == "emote":

                        if len(received.get("trip", "")) < 6:
                            tripcode = "NOTRIP"

                        else:
                            tripcode = received.get("trip", "")

                        print("{}|{}|{}".format(termcolor.colored(packet_receive_time, self.args.timestamp_color),
                                                termcolor.colored(tripcode, self.args.emote_color),
                                                termcolor.colored(received["text"], self.args.emote_color)))

                    elif received["cmd"] == "info" and received.get("type") is not None and received.get("type") == "whisper":

                        if len(received.get("trip", "")) < 6:
                            tripcode = "NOTRIP"

                        else:
                            tripcode = received.get("trip", "")

                        print("{}|{}|{}".format(termcolor.colored(packet_receive_time, self.args.timestamp_color),
                                                termcolor.colored(tripcode, self.args.whisper_color),
                                                termcolor.colored(received["text"], self.args.whisper_color)))

                    elif received["cmd"] == "info":

                        print("{}|{}|{}".format(termcolor.colored(packet_receive_time, self.args.timestamp_color),
                                                termcolor.colored("SERVER", self.args.server_color),
                                                termcolor.colored(received["text"], self.args.server_color)))

                    elif received["cmd"] == "warn":

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

        message = message.replace("/n/",
                                  "\n")

        if message.split()[0] == "/raw":
            split_message = message.split()
            split_message.pop(0)
            to_send = ' '.join(split_message)

            try:
                json_to_send = json.loads(to_send)
                self.ws.send(json.dumps(json_to_send))

            except:
                print("{}|{}|Error sending json: {}".format(termcolor.colored("-NIL-", self.args.timestamp_color),
                                                            termcolor.colored("CLIENT", self.args.client_color),
                                                            termcolor.colored(sys.exc_info(), self.args.client_color)))

        elif message == "/list":
            print("{}|{}|{}".format(termcolor.colored("-NIL-", self.args.timestamp_color),
                                                      termcolor.colored("CLIENT", self.args.client_color),
                                                      termcolor.colored("Channel: {} - Online users: {}".format(self.channel, ", ".join(self.online_users)), self.args.client_color)))

        elif message.split()[0] == "/move":
            split_message = message.split()
            split_message.pop(0)
            channel_to_join = ' '.join(split_message)
            self.ws.send(json.dumps({"cmd": "move", "channel": channel_to_join}))

        elif message.split()[0] == "/nick":
            split_message = message.split()
            split_message.pop(0)
            nick_to_change = ''.join(split_message)

            if re.match("^[A-Za-z0-9_]*$", nick_to_change):
                self.ws.send(json.dumps({"cmd": "changenick", "nick": nick_to_change}))
                self.nick = nick_to_change
            
            else:
                self.ws.send(json.dumps({"cmd": "changenick", "nick": nick_to_change}))

        elif message.split()[0] == "/me":
            split_message = message.split()
            split_message.pop(0)
            message_to_send = ' '.join(split_message)
            self.ws.send(json.dumps({"cmd": "emote", "text": message_to_send}))

        elif message.split()[0] == "/clear":
            os.system('cls' if os.name=='nt' else 'clear')

        else:
            self.ws.send(json.dumps({"cmd": "chat", "text": message}))

            if message == "/help":
                print("""


All '/n/'s will be converted into linebreaks


Raw json packets can be sent with '/raw'
Usage: /raw <json>

User list can be viewed with '/list'\
Usage: /list

Chat can be cleared with '/clear'
Usage: /clear

Channel can be changed with '/move'
Usage: /move <newchannel>

Nickname can be changed with '/nick'
Usage: /nick <newnick>

Action messages can be sent with '/me'
Usage: /me <message>

Whispers can be sent with '/whisper'
Usage: /whisper <user> <message> or /w <user> <message>

Use '/reply' to reply to the user who last whispered to you
Usage: /reply <message> or /r <message>


                """)



if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Terminal client for connecting to hack.chat servers. Colors are provided by termcolor.")
    required_group = parser.add_argument_group('required arguments')
    optional_group = parser.add_argument_group('optional arguments')
    required_group.add_argument("-c", "--channel", help="specify the channel to join", required=True)
    required_group.add_argument("-n", "--nickname", help="specify the nickname to use", required=True)
    optional_group.add_argument("-t", "--trip-password", help="specify a tripcode password to use when joining")
    optional_group.add_argument("-w", "--websocket-address", help="specify the websocket address to connect to (default: wss://hack-chat/chat-ws)")
    optional_group.add_argument("--no-parse", help="log received packets without parsing",  dest="no_parse", action="store_true")
    optional_group.add_argument("--no-clear", help="disables terminal clearing when joining a new channel", dest="no_clear", action="store_true")
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

