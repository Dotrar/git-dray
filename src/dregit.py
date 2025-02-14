from __future__ import annotations
import typing
from collections.abc import Iterable
import urwid


class Stageable:
    pass


class Line(Stageable):
    pass


class Hunk(Stageable):
    lines: list[Line]

    def __init__(self, *lines: list[Line]) -> None:
        self.lines = lines


class File(Stageable):
    hunks: list[Hunk]

    def __init__(self, *hunks: list[Hunk]) -> None:
        self.hunks = hunks


class Directory(Stageable):
    items: list[Directory | File]

    def __init__(self, *args: list[Directory | File]) -> None:
        self.items = args


test_structure = Directory(
    Directory(),
    Directory(
        Directory(File()),
    ),
)

choices = "Chapman Cleese Gilliam Idle Jones Palin".split()


def menu(title: str, choices_: Iterable[str]) -> urwid.ListBox:
    body = [urwid.Text(title), urwid.Divider()]
    for c in choices_:
        button = urwid.Button(c)
        urwid.connect_signal(button, "click", item_chosen, c)
        body.append(urwid.AttrMap(button, None, focus_map="reversed"))
    return urwid.ListBox(urwid.SimpleFocusListWalker(body))


def item_chosen(button: urwid.Button, choice: str) -> None:
    response = urwid.Text(["You chose ", choice, "\n"])
    done = urwid.Button("Ok")
    urwid.connect_signal(done, "click", exit_program)
    main.original_widget = urwid.Filler(
        urwid.Pile(
            [
                response,
                urwid.AttrMap(done, None, focus_map="reversed"),
            ]
        )
    )


def exit_program(button: urwid.Button) -> None:
    raise urwid.ExitMainLoop()


main = urwid.Padding(menu("Pythons", choices), left=2, right=2)
top = urwid.Overlay(
    main,
    urwid.SolidFill("\N{MEDIUM SHADE}"),
    align=urwid.CENTER,
    width=(urwid.RELATIVE, 60),
    valign=urwid.MIDDLE,
    height=(urwid.RELATIVE, 60),
    min_width=20,
    min_height=9,
)

urwid.MainLoop(
    top,
).run()
