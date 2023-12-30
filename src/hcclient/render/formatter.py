# Author:    AnnikaV9
# License:   Unlicense

import re
import html

import termcolor
import linkify_it
import markdown_it
import pygments
import pygments.util
import pygments.lexers
import pygments.formatters
import mdit_py_plugins.texmath


class TextFormatter:
    """
    Handles markdown parsing, code highlighting, LaTeX simplifying and linkifying
    """
    def __init__(self) -> None:
        """
        Initializes the markdown parser and compiles regex patterns
        """
        self.parser = markdown_it.MarkdownIt("zero")
        self.parser.enable(["emphasis", "escape", "strikethrough", "link", "image", "fence", "autolink", "backticks"])
        self.parser.use(mdit_py_plugins.texmath.texmath_plugin)

        self.linkify = (
            linkify_it.LinkifyIt()
            .add("git:", "http:")
            .add("ws:", "http:")
            .add("wss:", "https:")
        )

        self.latex2sympy = None  # client.py lazy loads this

        self.codeblock_pattern = re.compile(r"\s*<pre><code(?: class=\"(?P<lang>[^\s\n]+)\")?>(?P<code>.*?)</code></pre>", re.DOTALL)
        self.code_pattern = re.compile(r"<(?!pre>)(?:code>(?P<code>.*?)</code>)", re.DOTALL)

        self.link_pattern = re.compile(r"<a href=\"(?P<url>.*?)\">(.*?)</a>", re.DOTALL)
        self.image_pattern = re.compile(r"<img src=\"(?P<url>.*?)\" alt=\"(.*?)\">", re.DOTALL)

        self.eq_pattern = re.compile(r"<eq>(?P<equation>.*?)</eq>", re.DOTALL)
        self.eqn_pattern = re.compile(r"<section>\n<eqn>(?P<equation>.*?)</eqn>\n</section>", re.DOTALL)

    def markdown(self, text: str, highlight_theme: str, client_color: str, message_color: str, latex: bool, linkify: bool, backticks_bg: int) -> str:
        """
        Formats text with markdown and calls the highlighter and LaTeX simplifier
        """
        parsed = self.parser.render(text)
        message_color_open = "\033[%dm" % (termcolor.COLORS[message_color])

        parsed = parsed.replace("<p>", "").replace("</p>\n", "\n").replace("</p>", "\n")
        parsed = parsed.replace("<em>", "\033[3m").replace("</em>", "\033[0m" + message_color_open)
        parsed = parsed.replace("<strong>", "\033[1m").replace("</strong>", "\033[0m" + message_color_open)
        parsed = parsed.replace("<s>", "\033[9m").replace("</s>", "\033[0m" + message_color_open)

        parsed = self.link_pattern.sub("\033[4m\\g<url>\033[0m" + message_color_open, parsed)
        parsed = self.image_pattern.sub("\033[4m\\g<url>\033[0m" + message_color_open, parsed)

        parsed = parsed.replace("<pre><code>", "<pre><code class=\"guess\">")
        parsed = self.code_pattern.sub("\033[48;5;{}m \\g<code> \033[0m".format(backticks_bg) + message_color_open, parsed)
        parsed = self.highlight_blocks(parsed, highlight_theme, client_color, message_color_open)

        if latex:
            self.message_color_open = message_color_open
            parsed = self.eq_pattern.sub(self.simplify_latex, parsed)
            parsed = self.eqn_pattern.sub(self.simplify_latex, parsed)

        else:
            parsed = self.eq_pattern.sub("$\\g<equation>$", parsed)
            parsed = self.eqn_pattern.sub("$$\\g<equation>$$", parsed)

        if linkify and self.linkify.test(parsed):
            links = self.linkify.match(parsed)
            for link in links:
                parsed = parsed.replace(link.raw, f"\033[4m{link.raw}\033[0m" + message_color_open)

        return html.unescape(parsed.strip("\n"))

    def highlight_blocks(self, text: str, highlight_theme: str, client_color: str, message_color_open: str) -> str:
        """
        Highlights code blocks with pygments
        """
        matches = self.codeblock_pattern.finditer(text)
        for match in matches:
            code = html.unescape(match.group("code"))
            lang = match.group("lang").replace("language-", "")

            try:
                lexer = pygments.lexers.get_lexer_by_name(lang)
                guess_tag = ""

            except pygments.util.ClassNotFound:
                lexer = pygments.lexers.guess_lexer(code)
                guess_tag = "(guessed) "

            highlighted = pygments.highlight(code, lexer, pygments.formatters.Terminal256Formatter(style=highlight_theme)).strip("\n")

            text = text.replace(match.group(), termcolor.colored(f"\n--- {lexer.name.lower()} {guess_tag}---\n", client_color) +
                                highlighted +
                                termcolor.colored("\n------", client_color) +
                                message_color_open)

        return text

    def simplify_latex(self, match: re.Match) -> str:
        """
        Simplifies LaTeX equations with latex2sympy2
        """
        equation = match.group("equation")
        block = "|" if match.group(0).startswith("<eq>") else "||"

        try:
            sympy_expr = str(self.latex2sympy.latex2sympy(equation)).replace("**", "^")
            replacement = f"\033[3m\033[1m{block}latex: {sympy_expr}{block}\033[0m" + self.message_color_open

        except Exception:
            replacement = f"\033[3m\033[1m{block}latex-error: {equation}{block}\033[0m" + self.message_color_open

        return replacement
