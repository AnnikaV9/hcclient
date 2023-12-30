# Sample functional hook to add/modify commands

import termcolor

from hcclient.client.commands import ClientCommands


class CustomCommands(ClientCommands):
    # Adding a new command
    def hello(client, args_string):
        client.print_msg("{}|{}| {}".format(termcolor.colored(client.formatted_datetime(), client.args["timestamp_color"]),
                                            termcolor.colored("CLIENT", client.args["client_color"]),
                                            termcolor.colored("Hello World!", client.args["client_color"])))

    # Overriding an existing command
    # Original command exits the client without a message, this one prints a goodbye message
    def quit_client(client, args_string):
        client.print_msg("{}|{}| {}".format(termcolor.colored(client.formatted_datetime(), client.args["timestamp_color"]),
                                            termcolor.colored("CLIENT", client.args["client_color"]),
                                            termcolor.colored("Goodbye!", client.args["client_color"])))
        raise SystemExit


def hook(client):
    client.ClientCommands = CustomCommands
    client.ClientCommands.client_command_map["/hello"] = CustomCommands.hello
    client.ClientCommands.client_command_map["/quit"] = CustomCommands.quit_client

    return client