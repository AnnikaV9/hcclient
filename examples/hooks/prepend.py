# Sample functional hook to prepend a string to stdout messages
# Cannot be used with logger_sample.py as they both modify the same function


class HookInfo:
    name = "Prepend"
    description = "Prepends a string to stdout messages"
    version = "0.1.0"
    compat = ">=1.19.3"


STRING_TO_PREPEND = "Hello World! "

def print_msg(self, message, hist=True):
    message = STRING_TO_PREPEND + message
    print(message)

    if hist:
        self.stdout_history.append(message)
        if len(self.stdout_history) > 100:
            self.stdout_history.pop(0)


def hook(client):
    funcType = type(client.print_msg)
    client.print_msg = funcType(print_msg, client)

    return client
