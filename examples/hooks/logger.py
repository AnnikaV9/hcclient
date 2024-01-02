# Functional hook to log stdout messages to a file
# Cannot be used with prepend_sample.py as they both modify the same function

import re


class HookInfo:
    name = "Logger"
    description = "Logs stdout messages to a file"
    version = "0.1.0"
    compat = ">=1.19.3"


ansi_remover = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

def print_msg(self, message, hist=True):
    print(message)

    if hist:
        self.stdout_history.append(message)
        if len(self.stdout_history) > 100:
            self.stdout_history.pop(0)

    with open(f"{self.args['channel']}.log", "a") as f:
        f.write(self.ansi_remover.sub("", message) + "\n")


def hook(client):
    client.ansi_remover = ansi_remover
    funcType = type(client.print_msg)
    client.print_msg = funcType(print_msg, client)

    return client
