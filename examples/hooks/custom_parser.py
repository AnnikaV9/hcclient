# Hook to use a custom markdown parser


class HookInfo:
    name = "CustomParser"
    description = "Use a custom markdown parser"
    version = "0.1.0"


class MarkdownParser:
    # ...
    # ...
    # ...
    def render(self, text):
        # ...
        # ...
        # ...
        return html


def hook(client):
    parser = MarkdownParser()
    client.formatter.parser = parser

    # Probably have to override a
    # bunch of regex/replace operations
    # and possibly formatter.markdown()

    return client
