#!/usr/bin/python3

import json
import threading
import websocket
import sys
import re
import os
import time
import argparse
from datetime import datetime



class Client:


    def __init__(self, args):

        self.args = args

        if self.args.trip_password is not None:
            self.password = self.args.trip_password

        else:
            self.password = ""

        self.nick = self.args.nickname
        self.online_users = []

        self.ws = websocket.create_connection(self.args.websocket_address)
        self.ws.send(json.dumps({
            "cmd": "join",
            "channel": self.args.channel,
            "nick": "{}#{}".format(self.args.nickname, self.password)
        }))

        self.thread_ping = threading.Thread(target=self.ping_thread, daemon=True)
        self.thread_input = threading.Thread(target=self.input_thread, daemon=True)


    def main_thread(self):

        try:
            while self.ws.connected:
                received = json.loads(self.ws.recv())
                packet_receive_time = datetime.now().strftime("%H:%M")

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

                        print("You are now connected to channel: {}\nType '/help' for a list of commands you can use with this client\n\n".format(self.channel))

                    elif received["cmd"] == "chat":

                        if len(received.get("trip", "")) < 6:
                            tripcode = "NOTRIP"

                        else:
                            tripcode = received.get("trip", "")
                        print("{}|{}|[{}] {}".format(packet_receive_time, tripcode, received["nick"], received["text"]))

                    elif received["cmd"] == "onlineAdd":

                        if len(received.get("trip", "")) < 6:
                            tripcode = "NOTRIP"

                        else:
                            tripcode = received.get("trip", "")

                        self.online_users.append(received["nick"])
                        print("{}|{}|{} joined".format(packet_receive_time, tripcode, received["nick"]))

                    elif received["cmd"] == "onlineRemove":

                        if len(received.get("trip", "")) < 6:
                            tripcode = "NOTRIP"

                        else:
                            tripcode = received.get("trip", "")

                        self.online_users.remove(received["nick"])
                        print("{}|{}|{} left".format(packet_receive_time, tripcode, received["nick"]))

                    elif received["cmd"] == "emote":

                        if len(received.get("trip", "")) < 6:
                            tripcode = "NOTRIP"

                        else:
                            tripcode = received.get("trip", "")

                        print("{}|{}|{}".format(packet_receive_time, tripcode, received["text"]))

                    elif received["cmd"] == "info" and received.get("type") is not None and received.get("type") == "whisper":

                        if len(received.get("trip", "")) < 6:
                            tripcode = "NOTRIP"

                        else:
                            tripcode = received.get("trip", "")

                        print("{}|{}|{}".format(packet_receive_time, tripcode, received["text"]))

                    elif received["cmd"] == "info":

                        print("{}|{}|{}".format(packet_receive_time, "SYSTEM", received["text"]))

                    elif received["cmd"] == "warn":

                        print("{}|{}|{}".format(packet_receive_time, "!WARN!", received["text"]))
 
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
                print("\nError sending json: {}".format(sys.exc_info()))

        elif message == "/list":
            user_list = "\n\nChannel: {}\nOnline users:\n{}\n\n".format(self.channel,
                                                                        "\n".join(map(str, self.online_users)))
            print(user_list)


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

    parser = argparse.ArgumentParser()
    required_group = parser.add_argument_group('required arguments')
    optional_group = parser.add_argument_group('optional arguments')
    required_group.add_argument("-c", "--channel", help="specify the channel to join", required=True)
    required_group.add_argument("-n", "--nickname", help="specify the nickname to use", required=True)
    optional_group.add_argument("-t", "--trip-password", help="specify a tripcode password to use when joining")
    optional_group.add_argument("-w", "--websocket-address", help="specify the websocket address to connect to (default: wss://hack-chat/chat-ws)")
    optional_group.add_argument("--no-parse", help="log received packets without parsing",  dest="no_parse", action="store_true")
    optional_group.add_argument("--no-clear", help="disables terminal clearing when joining a new channel", dest="no_clear", action="store_true")
    optional_group.set_defaults(no_parse=False, no_clear=False, websocket_address="wss://hack.chat/chat-ws")
    args = parser.parse_args()

    client = Client(args)
    client.thread_ping.start()
    client.thread_input.start()
    client.main_thread()

