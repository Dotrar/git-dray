from __future__ import annotations
import dto

import typing
import pygit2 as git
import urwid

LINE_ADDED = "line-added"
LINE_REMOVED = "line-removed"
LINE_NORMAL = "line-normal"
HUNK_HEADER = "hunk-header"
PATCH_FILE = "patch-file"


class LineWidget(urwid.TreeWidget):
    """
    A selectable line, which we can stage
    """

    expanded_icon = urwid.SelectableIcon(" ")
    unexpanded_icon = urwid.SelectableIcon(" ")

    def get_display_text(self) -> str:
        line: dto.DreLine = self.get_node().get_value()
        return f"{line.type}{str(line.content).rstrip()}"

    def load_inner_widget(self) -> urwid.Text:
        line: dto.DreLine = self.get_node().get_value()
        return urwid.AttrMap(
            urwid.Text(self.get_display_text(), wrap="ellipsis"),
            {"-": LINE_REMOVED, "+": LINE_ADDED}.get(line.type, LINE_NORMAL),
        )


class ULineWidget(LineWidget):
    """
    An Unselectable line
    """

    def __init__(self, node: urwid.TreeNode) -> None:
        super().__init__(node)
        self.is_leaf = True


class HunkWidget(urwid.TreeWidget):
    def __init__(self, node: urwid.TreeNode) -> None:
        super().__init__(node)
        self.expanded = False
        self.update_expanded_icon()

    def get_display_text(self) -> str:
        hunk: dto.DreHunk = self.get_node().get_value()
        return hunk.header.rstrip()

    def load_inner_widget(self) -> urwid.Text:
        widget = super().load_inner_widget()
        return urwid.AttrMap(widget, HUNK_HEADER)


class PatchWidget(urwid.TreeWidget):
    def get_display_text(self) -> str:
        patch: dto.DrePatch = self.get_node().get_value()
        return patch.filepath

    def load_inner_widget(self) -> urwid.Text:
        widget = super().load_inner_widget()
        return urwid.AttrMap(widget, PATCH_FILE)


class LineNode(urwid.ParentNode):
    def load_widget(self) -> LineWidget:
        if self.get_value().type in ["+", "-"]:
            return LineWidget(self)
        return ULineWidget(self)

    def load_child_keys(self) -> typing.Iterable[int]:
        return range(0)


class HunkNode(urwid.ParentNode):
    def load_widget(self) -> HunkWidget:
        return HunkWidget(self)

    def load_child_keys(self) -> typing.Iterable[int]:
        hunk: dto.DreHunk = self.get_value()
        return range(len(hunk.lines))

    def load_child_node(self, key: int) -> LineNode:
        hunk: dto.DreHunk = self.get_value()
        line = hunk.lines[key]
        return LineNode(
            line,
            parent=self,
            key=key,
            depth=self.get_depth() + 1,
        )


class PatchNode(urwid.ParentNode):
    def load_widget(self) -> PatchWidget:
        return PatchWidget(self)

    def load_child_keys(self) -> typing.Iterable[int]:
        patch: dto.DrePatch = self.get_value()
        return range(len(patch.hunks))

    def load_child_node(self, key: int) -> HunkNode:
        patch: dto.DrePatch = self.get_value()
        hunk = patch.hunks[key]

        return HunkNode(
            hunk,
            parent=self,
            key=key,
            depth=self.get_depth() + 1,
        )


class StagingAreaChangesWidget(urwid.TreeWidget):
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
        return StagingAreaChangesWidget(self.staging_label, self)

    def load_child_keys(self) -> typing.Iterable[int]:
        patches: list[git.Patch] = self.get_value()
        return range(len(patches))

    def load_child_node(self, key: int) -> HunkNode:
        patches: list[git.Patch] = self.get_value()
        patch = patches[key]

        return PatchNode(
            patch,
            parent=self,
            key=key,
            depth=self.get_depth() + 1,
        )
