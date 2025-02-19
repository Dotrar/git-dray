from __future__ import annotations

import asyncio
import typing

import urwid
from about import AboutPage
from git_operations import GitHandler
from log import LogPage
from staging import StagingPage


def exit_program() -> None:
    raise urwid.ExitMainLoop


PageTypes = AboutPage | StagingPage | LogPage


class Application(urwid.LineBox):
    TITLE = "dregit"

    pages: typing.ClassVar[dict[int, tuple[str, urwid.Widget]]] = {
        "0": ("About", AboutPage),
        "1": ("Staging", StagingPage),
        "2": ("GitLog", LogPage),
    }

    def __init__(
        self,
    ) -> None:
        super().__init__(self.pages["1"][1](), "press '0' for help", "left")
        self.event_loop = asyncio.get_event_loop()
        self.git = GitHandler()
        self.main_loop = urwid.MainLoop(
            self,
            unhandled_input=self.unhandled_input,
            event_loop=urwid.AsyncioEventLoop(loop=self.event_loop),
        )
        self.background_tasks: set[asyncio.Task] = set()

    def format_title(self, text: str) -> str:
        if text:
            return f" {self.TITLE} - {text} "
        return self.TITLE

    def run(self) -> None:
        self.main_loop.run()

    def add_background_task(self, task: typing.Awaitable | typing.Generator) -> None:
        task = self.event_loop.create_task(task)
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)

    def cancel_all_background_tasks(self) -> None:
        for task in self.background_tasks:
            task.cancel()
        self.background_tasks.clear()

    def post_page_change_callback(self, page: PageTypes) -> None:
        self.cancel_all_background_tasks()

        if isinstance(page, LogPage):

            async def sync_commit_log_to_page() -> None:
                for commit in self.git.get_commit_log():
                    page.load_commit_data(commit)
                    self.event_loop.call_soon(self.main_loop.draw_screen)
                    await asyncio.sleep(0.1)  # TODO: get more only when needed

            self.add_background_task(sync_commit_log_to_page())

        if isinstance(page, StagingPage):

            async def gather_unstaged_changes() -> None:
                for diff in self.git.get_unstaged_changes():
                    page.add_unstaged_data(diff)
                self.event_loop.call_soon(self.main_loop.draw_screen)
                await asyncio.sleep(0)

            self.add_background_task(gather_unstaged_changes())

    def unhandled_input(self, key: str) -> None:
        if key in self.pages:
            title, wcls = self.pages[key]
            self.set_title(title)
            self.original_widget = wcls()
            self.post_page_change_callback(self.original_widget)

        elif key == "q":
            self.cancel_all_background_tasks()
            exit_program()

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


if __name__ == "__main__":
    main()
