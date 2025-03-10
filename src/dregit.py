from __future__ import annotations

import asyncio
import typing

import urwid
from about import AboutPage
from log import LogPage
from staging import StagingPage
from background import BackgroundWorker


def exit_program() -> None:
    raise urwid.ExitMainLoop


PageTypes = AboutPage | StagingPage | LogPage

palette = [
    ("line-added", "dark green", "black"),
    ("line-removed", "dark red", "black"),
    ("line-normal", "white", "black"),
    ("hunk-header", "dark blue", "black"),
    ("patch-file", "dark magenta", "black"),
    # ("tree-widget", "dark blue", "dark green"),
]


class Application(urwid.LineBox):
    TITLE: str = "dregit"
    QUIT: bool = False

    pages: typing.ClassVar[dict[int, tuple[str, PageTypes]]] = {
        "0": ("About", AboutPage),
        "1": ("Staging", StagingPage),
        "2": ("GitLog", LogPage),
    }

    messages: list[str]

    def __init__(
        self,
    ) -> None:
        self.messages = []
        opening_page = StagingPage()
        super().__init__(opening_page, "press '0' for help", "right")
        self.QUIT = False
        self.main_loop = urwid.MainLoop(
            self,
            palette,
            unhandled_input=self.unhandled_input,
            event_loop=urwid.AsyncioEventLoop(loop=asyncio.get_event_loop()),
        )
        self.background = BackgroundWorker(self.main_loop)
        self.background.post_data_callback(self.main_loop.draw_screen)
        self.post_page_change_callback(opening_page)

    def format_title(self, text: str) -> str:
        if text:
            return f" {self.TITLE} - {text} "
        return self.TITLE

    def run(self) -> None:
        self.main_loop.run()

    def post_page_change_callback(self, page: PageTypes) -> None:
        if isinstance(page, LogPage):
            self.background.sync_commit_log_to_page(page)
            page.give_operation_to(self.background.add_operation)

        if isinstance(page, StagingPage):
            self.background.sync_staging_area_changes(page)
            page.give_operation_to(self.background.add_operation)
            self.background.set_operation_callback(page.operation_callback)

    def quit(self) -> None:
        exit_program()

    def wait_for_operations(self) -> None:
        self.background.shutdown()

    def unhandled_input(self, key: str) -> None:
        if key in self.pages:
            title, wcls = self.pages[key]
            if isinstance(self.original_widget, wcls):
                return key
            self.set_title(title)
            self.original_widget = wcls()
            self.post_page_change_callback(self.original_widget)

        elif key == "q":
            self.quit()

        else:
            handler = getattr(self.original_widget, "handle_key", lambda _: ())
            handler(key)

    # -------------------------------------------------------
    # this is to fix a bug in urwid
    @property
    def original_widget(self) -> urwid.WrappedWidget:
        return self._original_widget

    @original_widget.setter
    def original_widget(self, original_widget: urwid.WrappedWidget) -> None:
        self._original_widget = original_widget
        top, (middle, mopts), bottom = self._wrapped_widget.contents
        left, (_, copts), right = middle.contents
        middle.contents = [left, (self.original_widget, copts), right]
        self._wrapped_widget.contents = [top, (middle, mopts), bottom]
        self._invalidate()


def main() -> None:
    app = Application()
    app.run()
    app.wait_for_operations()


if __name__ == "__main__":
    main()
