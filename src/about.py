import urwid
import typing


class AboutPage(urwid.Filler):
    text = """
    Dregit - v0.1

    Dre's Remarkable Example of
    Git Infused Tooling

    ~~~~~~~~~~~ Keybinds ~~~~~~~~~~~~
    """
    keybinds = """
    0 - About page and help (this page)
    1 - Staging
    2 - Log
    q - quit

    Staging:
    tab - toggle between viewing stage and unstaged area
    n/p - next/prev hunk
    """

    def __init__(self) -> None:
        super().__init__(
            urwid.Pile(
                [
                    urwid.Text(self.text, align="center"),
                    urwid.Text(self.keybinds, align="left"),
                ]
            )
        )
