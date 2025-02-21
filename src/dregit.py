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
    TITLE: str = "dregit"
    QUIT: bool = False

    pages: typing.ClassVar[dict[int, tuple[str, PageTypes]]] = {
        "0": ("About", AboutPage),
        "1": ("Staging", StagingPage),
        "2": ("GitLog", LogPage),
    }

    def __init__(
        self,
    ) -> None:
        opening_page = StagingPage()
        super().__init__(opening_page, "press '0' for help", "right")
        self.QUIT = False
        self.event_loop = asyncio.get_event_loop()
        self.git = GitHandler()
        self.main_loop = urwid.MainLoop(
            self,
            unhandled_input=self.unhandled_input,
            event_loop=urwid.AsyncioEventLoop(loop=self.event_loop),
        )
        self.background_tasks: set[asyncio.Task] = set()
        self.background_operations: list[asyncio.Task] = []

        # call this last to start the background staging change
        self.post_page_change_callback(opening_page)

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
                    await asyncio.sleep(0.01)  # TODO: get more only when needed

            self.add_background_task(sync_commit_log_to_page())

        if isinstance(page, StagingPage):

            async def gather_unstaged_changes() -> None:
                for patch in self.git.get_unstaged_changes():
                    page.add_unstaged_data(patch)
                    await asyncio.sleep(0)

            async def gather_staged_changes() -> None:
                for patch in self.git.get_staged_changes():
                    page.add_staged_data(patch)
                    await asyncio.sleep(0)

            async def poll_and_operate_git() -> None:
                while True:
                    for operation in page.get_pending_operations():
                        print("doing operation", operation)
                        self.git.do_operation(operation)
                        await asyncio.sleep(0)
                    if self.QUIT:
                        break
                    await asyncio.sleep(0)

            self.add_background_task(gather_unstaged_changes())
            self.add_background_task(gather_staged_changes())
            self.background_operation_poll = self.event_loop.create_task(poll_and_operate_git())

    def quit(self) -> None:
        self.cancel_all_background_tasks()
        self.QUIT = True
        exit_program()

    def unhandled_input(self, key: str) -> None:
        if key in self.pages:
            title, wcls = self.pages[key]
            self.set_title(title)
            self.original_widget = wcls()
            self.post_page_change_callback(self.original_widget)

        elif key == "q":
            self.quit()

        else:
            handler = getattr(self.original_widget, "handle_key", lambda _: ())
            handler(key)

    def wait_for_operations(self) -> None:
        if self.background_operation_poll.done():
            return

        print("Waiting for background operations to finish")
        self.event_loop.run_until_complete(self.background_operation_poll)
        # def spinner():
        #     while True:
        #         yield from "|/-\\"

        # async def spinner_coro():
        #     spinner = spinner()
        #     while True:
        #         sys.stdout.write(next(spinner))
        #         sys.stdout.flush()
        #         await asyncio.sleep(0.01)
        #         sys.stdout.write("\r")

        # async def final_wait():
        #     spinner_ = self.event_loop.create_task(spinner_coro())
        #     while (done,pending) := await asyncio.wait([self.background_operation_poll, spinner_]):
        #         if len(pending) == 1:
        #             break

        # self.event_loop.run_until_complete(
        #     self.event_loop.create_task(final_wait())
        # )

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
