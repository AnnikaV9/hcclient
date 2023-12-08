# Hook to use a custom markdown parser


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
    # and possibly client.markdown()

    return client
