from __future__ import annotations

from typing import Iterable
import pygit2 as git
import urwid


class LineWidget(urwid.TreeWidget):
    def get_display_text(self) -> str:
        line: git.DiffLine = self.get_node().get_value()
        return f"{line.origin}{line.content}".strip()


class HunkWidget(urwid.TreeWidget):
    def get_display_text(self) -> str:
        hunk: git.DiffHunk = self.get_node().get_value()
        return hunk.header


class PatchWidget(urwid.TreeWidget):
    def get_display_text(self) -> str:
        patch: git.Patch = self.get_node().get_value()
        return patch.delta.new_file.path


class LineNode(urwid.TreeNode):
    def load_widget(self) -> LineWidget:
        return LineWidget(self)


class HunkNode(urwid.ParentNode):
    def load_widget(self) -> HunkWidget:
        return HunkWidget(self)

    def load_child_keys(self) -> Iterable[int]:
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

    def load_child_keys(self) -> Iterable[int]:
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


class StageWidget(urwid.TreeWidget):
    def get_display_text(self) -> str:
        return "stagables:"


class StagedChanges(urwid.ParentNode):
    def load_widget(self) -> PatchWidget:
        return StageWidget(self)

    def load_child_keys(self) -> Iterable[int]:
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
    STAGED = "STAGED"
    UNSTAGED = "UNSTAGED"

    def __init__(
        self,
    ) -> None:
        self.showing_unstaged = True
        self.mode_widget = urwid.Text(self.UNSTAGED)
        self.list_widget = urwid.TreeListBox([])
        self.staged = set()
        self.unstaged = set()

        super().__init__(
            [
                ("pack", self.mode_widget),
                self.list_widget,
            ]
        )

    def add_unstaged_data(self, patch: git.Patch) -> None:
        self.unstaged.add(patch)

    def toggle_mode(self) -> None:
        self.showing_unstaged = not self.showing_unstaged
        if self.showing_unstaged:
            self.set_mode_unstaged()
        else:
            self.set_mode_staged()

    def set_mode_staged(self) -> None:
        self.mode_widget.set_text(self.STAGED)
        # self.show_hunk_data(self.staged)

    def set_mode_unstaged(self) -> None:
        self.mode_widget.set_text(self.UNSTAGED)
        self.show_hunk_data(self.unstaged)

    def handle_key(self, key: str) -> None:
        if key == "tab":
            self.toggle_mode()

    def show_hunk_data(self, data: list[git.Patch]) -> None:
        self.topnode = StagedChanges(list(data))
        self.walker = urwid.TreeWalker(self.topnode)
        self.list_widget.body = self.walker


# presentation = []
# for p in data:
#     fpath = p.delta.new_file.path
#     stats = p.line_stats
#     presentation.append(f"{fpath} {stats}")
#     for h in p.hunks:
#         header = h.header
#         presentation.append(" " + header)
#         lines = h.lines
#         for l in lines[:-1]:
#             presentation.append(f" │{l.origin}{l.content}")
#         l = lines[-1]
#         presentation.append(f" └{l.origin}{l.content}")
