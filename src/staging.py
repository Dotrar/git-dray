from __future__ import annotations

import typing

import dto
import helpers
import pygit2 as git
import urwid
from staging_widgets import HunkNode, LineWidget, PatchNode, StagingAreaChanges


def _nop(_: dto.GitOperation) -> None:
    pass


class StagingPage(urwid.Pile):
    STAGED = "STAGED CHANGES"
    UNSTAGED = "UNSTAGED CHANGES"

    add_operation: typing.Callable[[dto.GitOperation], None] = _nop

    def __init__(
        self,
    ) -> None:
        self.showing_unstaged = True
        self.mode_widget = urwid.Text("Select items to stage")
        self.tree_widget = urwid.TreeListBox([])
        self.staged = set()
        self.unstaged = set()

        super().__init__(
            [
                ("pack", self.mode_widget),
                self.tree_widget,
            ]
        )

    def give_operation_to(
        self, callable: typing.Callable[[dto.GitOperation], None]
    ) -> None:
        self.add_operation = callable

    def operation_callback(self, operation: dto.GitOperation) -> None:
        if operation.type in [
            dto.GitOperationType.AMEND,
            dto.GitOperationType.COMMIT,
            dto.GitOperationType.FIXUP,
        ]:
            self.staged.clear()
            self.refresh_mode()

    def refresh_mode(self) -> None:
        if self.showing_unstaged:
            self.set_mode_unstaged()
        else:
            self.set_mode_staged()

    def add_staged_data(self, patch: git.Patch) -> None:
        self.staged.add(dto.DrePatch.from_patch(patch))
        self.refresh_mode()

    def add_unstaged_data(self, patch: git.Patch) -> None:
        self.unstaged.add(dto.DrePatch.from_patch(patch))
        self.refresh_mode()

    def toggle_mode(self) -> None:
        self.showing_unstaged = not self.showing_unstaged
        self.refresh_mode()

    def set_mode_staged(self) -> None:
        self.show_hunk_data(self.STAGED, self.staged)

    def set_mode_unstaged(self) -> None:
        self.show_hunk_data(self.UNSTAGED, self.unstaged)

    def keypress(self, size, key: str) -> str | None:
        if key == "tab":
            self.toggle_mode()
        elif key == "c":
            self.commit()
        elif key == "a":
            self.amend()
        elif key == "s" and self.showing_unstaged:
            self.stage_selection()
        elif key == "u" and not self.showing_unstaged:
            self.unstage_selection()
        elif key == "=":
            self.expand_patch_or_hunk()
        elif key == "n":
            self.next_at_level()
        elif key == "p":
            self.prev_at_level()
        elif key in ("h", "j", "k", "l"):
            key = dict(h="left", j="down", k="up", l="right")[key]
            return super().keypress(size, key)
        else:
            return super().keypress(size, key)
        return None

    def next_at_level(self) -> None:
        item: urwid.TreeNode = self.tree_widget.focus.get_node()
        if next := item.next_sibling():
            while next.get_widget().is_leaf:
                next = next.next_sibling()
                if next is None:
                    return
            self.tree_widget.body.set_focus(next)

    def prev_at_level(self) -> None:
        item: urwid.TreeNode = self.tree_widget.focus.get_node()
        if next := item.prev_sibling():
            while next.get_widget().is_leaf:
                next = next.prev_sibling()
                if next is None:
                    return
            self.tree_widget.body.set_focus(next)

    def expand_patch_or_hunk(self) -> None:
        item: urwid.TreeWidget = self.tree_widget.focus
        if isinstance(item, LineWidget):
            item = item.get_node().get_parent()
            self.tree_widget.body.set_focus(item)
            item = item.get_widget()

        item.expanded = not item.expanded
        item.update_expanded_icon()

    def show_hunk_data(self, label: str, data: set[dto.DrePatch]) -> None:
        data = sorted(data, key=lambda d: d.header)
        self.topnode = StagingAreaChanges(label, list(data))
        self.walker = urwid.TreeWalker(self.topnode)
        self.tree_widget.body = self.walker

    def commit(self) -> None:
        self.add_operation(dto.GitOperation.commit())

    def amend(self) -> None:
        self.add_operation(dto.GitOperation.amend())

    def get_selected_node(self) -> urwid.TreeNode:
        return self.tree_widget.focus.get_node()

    def stage_patch(self, patch: dto.DrePatch) -> None:
        self.add_operation(dto.GitOperation.stage(patch, None, None))
        self.staged.add(patch)
        self.unstaged.remove(patch)

    def unstage_patch(self, patch: dto.DrePatch) -> None:
        self.add_operation(dto.GitOperation.unstage(patch, None, None))
        self.unstaged.add(patch)
        self.staged.remove(patch)

    def stage_hunk(self, original_patch: dto.DrePatch, hunk: dto.DreHunk) -> None:
        self.add_operation(dto.GitOperation.stage(original_patch, hunk, None))

        self.unstaged.remove(original_patch)
        remaining_patch = helpers.remove_hunk_from_patch(original_patch, hunk)
        if remaining_patch:
            self.unstaged.add(remaining_patch)

        target_patch = helpers.find_matching_patch(original_patch, self.staged)
        if target_patch:
            self.staged.remove(target_patch)
            target_patch = helpers.add_hunk_to_patch(target_patch, hunk)
            self.staged.add(target_patch)

        else:
            new_patch = helpers.duplicate_to_solo_hunk(original_patch, hunk)
            self.staged.add(new_patch)

    def unstage_hunk(self, original_patch: dto.DrePatch, hunk: dto.DreHunk) -> None:
        self.add_operation(dto.GitOperation.unstage(original_patch, hunk, None))

        # TODO: change this so it's just one call to helper function
        # TODO: don't call it hepler, it's just patch logic for this page

        self.staged.remove(original_patch)
        remaining_patch = helpers.remove_hunk_from_patch(original_patch, hunk)
        if remaining_patch:
            self.staged.add(remaining_patch)

        target_patch = helpers.find_matching_patch(original_patch, self.unstaged)
        if target_patch:
            self.unstaged.remove(target_patch)
            target_patch = helpers.add_hunk_to_patch(target_patch, hunk)
            self.unstaged.add(target_patch)

        else:
            new_patch = helpers.duplicate_to_solo_hunk(original_patch, hunk)
            self.unstaged.add(new_patch)

    def stage_selection(self) -> None:
        item = self.get_selected_node()
        if isinstance(item, StagingAreaChanges):
            patches = item.get_value()
            for patch in patches:
                self.stage_patch(patch)

        elif isinstance(item, PatchNode):
            patch = item.get_value()
            self.stage_patch(patch)

        elif isinstance(item, HunkNode):
            hunk: dto.DreHunk = item.get_value()
            patch: dto.DrePatch = item.get_parent().get_value()
            self.stage_hunk(patch, hunk)
        self.refresh_mode()

    def unstage_selection(self) -> None:
        item = self.get_selected_node()
        if isinstance(item, StagingAreaChanges):
            patches: list[dto.DrePatch] = item.get_value()
            for patch in patches:
                self.unstage_patch(patch)

        elif isinstance(item, PatchNode):
            patch: dto.DrePatch = item.get_value()
            self.unstage_patch(patch)

        elif isinstance(item, HunkNode):
            hunk: dto.DreHunk = item.get_value()
            patch: dto.DrePatch = item.get_parent().get_value()
            self.unstage_hunk(patch, hunk)
        self.refresh_mode()


# good resource for staging lines:
#  https://github.com/nodegit/nodegit/pull/678/files
