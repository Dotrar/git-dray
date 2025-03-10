import asyncio
import os
import urwid
import typing

from log import LogPage
from staging import StagingPage
from git_operations import GitHandler
from dto import GitOperation


def _nop(operation: GitOperation) -> None:
    pass


class BackgroundWorker:
    def __init__(self, main_loop: urwid.MainLoop):
        self.event_loop = asyncio.get_event_loop()
        self.main_loop = main_loop
        self.background_tasks: set[asyncio.Task] = set()
        self.git = GitHandler(self.switch_to_editor_commit)
        self.operations: list[GitOperation] = []
        self.quiting = False
        self._post_data_callback: typing.Callable[..., typing.Any] | None = None

        self._operation_task = self.event_loop.create_task(self.process_operations())
        self._operation_callback = _nop

    def get_event_loop(self) -> asyncio.AbstractEventLoop:
        return self.event_loop

    def post_data_callback(self, callable: typing.Callable[..., typing.Any]) -> None:
        self._post_data_callback = callable

    def get_next_operation(self) -> GitOperation | None:
        if self.operations:
            return self.operations.pop(0)
        return None

    def switch_to_editor_commit(self) -> None:
        self.main_loop.stop()
        os.system("git commit")
        self.main_loop.start()

    async def process_operations(self):
        while not self.quiting:
            while op := self.get_next_operation():
                self.git.do_operation(op)
                await asyncio.sleep(0)
                self._operation_callback(op)
                if self._post_data_callback is not None:
                    self.event_loop.call_soon(self._post_data_callback)
            await asyncio.sleep(0)

    def add_background_task(self, task: typing.Awaitable | typing.Generator) -> None:
        task = self.event_loop.create_task(task)
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)

    def cancel_all_background_tasks(self) -> None:
        for task in self.background_tasks:
            task.cancel()
        self.background_tasks.clear()

    def sync_commit_log_to_page(self, page: LogPage) -> None:
        async def async_commit_log_to_page() -> None:
            count = 10
            for commit in self.git.get_commit_log():
                page.load_commit_data(commit)
                if self._post_data_callback is not None:
                    self.event_loop.call_soon(self._post_data_callback)
                count -= 1
                if count == 0:
                    break
                await asyncio.sleep(0.01)  # TODO: get more only when needed

        self.add_background_task(async_commit_log_to_page())

    def set_operation_callback(self, callable) -> None:
        self._operation_callback = callable

    def sync_staging_area_changes(self, page: StagingPage) -> None:
        async def gather_unstaged_changes() -> None:
            for patch in self.git.get_unstaged_changes():
                page.add_unstaged_data(patch)
                if self._post_data_callback is not None:
                    self.event_loop.call_soon(self._post_data_callback)
                await asyncio.sleep(0)

        async def gather_staged_changes() -> None:
            for patch in self.git.get_staged_changes():
                page.add_staged_data(patch)
                if self._post_data_callback is not None:
                    self.event_loop.call_soon(self._post_data_callback)
                await asyncio.sleep(0)

        self.add_background_task(gather_unstaged_changes())
        self.add_background_task(gather_staged_changes())

    def add_operation(self, op: GitOperation) -> None:
        self.operations.append(op)

    def shutdown(self) -> list[asyncio.Task]:
        pass
