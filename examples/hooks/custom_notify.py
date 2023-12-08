# Hook to use a custom notification system


def push_notification(self, message, title="hcclient"):
    if self.args["no_notify"]:
        return

    # This is where you would put your custom notification code
    # For example:
    # subprocess.Popen([
    #     "/path/to/your/notification/script",
    #     "-t", title,
    #     "-c", message
    # ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def hook(client):
    funcType = type(client.push_notification)
    client.push_notification = funcType(push_notification, client)

    return client
