from __future__ import annotations
from dto import GitOperation, GitOperationType

import typing
import pygit2 as git
import urwid


class LineWidget(urwid.TreeWidget):
    def get_display_text(self) -> str:
        line: git.DiffLine = self.get_node().get_value()
        return f"{line.origin}{str(line.content).rstrip()}"


class HunkWidget(urwid.TreeWidget):
    def get_display_text(self) -> str:
        hunk: git.DiffHunk = self.get_node().get_value()
        return hunk.header


class PatchWidget(urwid.TreeWidget):
    def get_display_text(self) -> str:
        patch: git.Patch = self.get_node().get_value()
        status = patch.delta.status_char()
        newpath = patch.delta.new_file.path
        oldpath = patch.delta.old_file.path
        if status == "D":
            return f"D {oldpath}"
        return f"{status} {newpath}"


class LineNode(urwid.TreeNode):
    def load_widget(self) -> LineWidget:
        return LineWidget(self)


class HunkNode(urwid.ParentNode):
    def load_widget(self) -> HunkWidget:
        return HunkWidget(self)

    def load_child_keys(self) -> typing.Iterable[int]:
        hunk: git.DiffHunk = self.get_value()
        return range(len(hunk.lines))

    def load_child_node(self, key: int) -> HunkNode:
        hunk: git.DiffHunk = self.get_value()
        line = hunk.lines[key]

        return LineNode(
            line,
            parent=self,
            key=key,
            depth=self.get_depth() + 1,
        )


class PatchParent(urwid.ParentNode):
    def load_widget(self) -> PatchWidget:
        return PatchWidget(self)

    def load_child_keys(self) -> typing.Iterable[int]:
        patch: git.Patch = self.get_value()
        return range(len(patch.hunks))

    def load_child_node(self, key: int) -> HunkNode:
        patch: git.Patch = self.get_value()
        hunk = patch.hunks[key]

        return HunkNode(
            hunk,
            parent=self,
            key=key,
            depth=self.get_depth() + 1,
        )


class UnstagedChangesWidget(urwid.TreeWidget):
    def __init__(self, staging_label: str, node: urwid.TreeNode):
        self.staging_label = staging_label
        super().__init__(node)

    def get_display_text(self) -> str:
        return self.staging_label


class StagingAreaChanges(urwid.ParentNode):
    def __init__(self, staging_label: str, data: list):
        self.staging_label = staging_label
        super().__init__(data)

    def load_widget(self) -> PatchWidget:
        return UnstagedChangesWidget(self.staging_label, self)

    def load_child_keys(self) -> typing.Iterable[int]:
        patches: list[git.Patch] = self.get_value()
        return range(len(patches))

    def load_child_node(self, key: int) -> HunkNode:
        patches: list[git.Patch] = self.get_value()
        patch = patches[key]

        return PatchParent(
            patch,
            parent=self,
            key=key,
            depth=self.get_depth() + 1,
        )


class StagingPage(urwid.Pile):
    STAGED = "STAGED CHANGES"
    UNSTAGED = "UNSTAGED CHANGES"

    def __init__(
        self,
    ) -> None:
        self.showing_unstaged = True
        self.mode_widget = urwid.Text(self.UNSTAGED)
        self.list_widget = urwid.TreeListBox([])
        self.staged = set()
        self.unstaged = set()
        self.operations: list[GitOperation] = []

        print("started")
        super().__init__(
            [
                ("pack", self.mode_widget),
                self.list_widget,
            ]
        )

    def operation_callback(self, operation: GitOperation) -> None:
        if operation.type in [
            GitOperationType.AMEND,
            GitOperationType.COMMIT,
            GitOperationType.FIXUP,
        ]:
            self.staged = set()
            self.refresh_mode()

    def get_pending_operations(self) -> typing.Iterator[GitOperation]:
        while self.operations:
            yield self.operations.pop(0)

    def refresh_mode(self) -> None:
        if self.showing_unstaged:
            self.set_mode_unstaged()
        else:
            self.set_mode_staged()

    def add_staged_data(self, patch: git.Patch) -> None:
        self.staged.add(patch)
        self.refresh_mode()

    def add_unstaged_data(self, patch: git.Patch) -> None:
        self.unstaged.add(patch)
        self.refresh_mode()

    def toggle_mode(self) -> None:
        self.showing_unstaged = not self.showing_unstaged
        if self.showing_unstaged:
            self.set_mode_unstaged()
        else:
            self.set_mode_staged()

    def set_mode_staged(self) -> None:
        self.mode_widget.set_text(self.STAGED)
        self.show_hunk_data(self.STAGED, self.staged)

    def set_mode_unstaged(self) -> None:
        self.mode_widget.set_text(self.UNSTAGED)
        self.show_hunk_data(self.UNSTAGED, self.unstaged)

    def handle_key(self, key: str) -> None:
        print(f"calling handle key on {key}")
        if key == "tab":
            self.toggle_mode()
        elif key == "c":
            self.commit()
        elif key == "a":
            self.amend()
        # elif key == "s":
        #     self.stage_selection()
        # elif key == "u":
        #     self.unstage_selection()
        else:
            return key
        return None

    def show_hunk_data(self, label: str, data: set[git.Patch]) -> None:
        self.topnode = StagingAreaChanges(label, list(data))
        self.walker = urwid.TreeWalker(self.topnode)
        self.list_widget.body = self.walker

    def commit(self) -> None:
        self.operations.append(GitOperation.commit())

    def amend(self) -> None:
        print("adding append")
        self.operations.append(GitOperation.amend())


def _nop() -> None:
    pass
