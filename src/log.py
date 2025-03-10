import pygit2 as git
import typing
import pyperclip
import urwid as u
from dto import GitOperation


class CommitButton(u.SelectableIcon):
    pass


class CommitWidget(u.LineBox):
    extended: bool
    commit: git.Commit

    def __init__(self, log: git.Commit):
        self.commit = log
        self.extended = False
        self.pile = u.Pile(
            [
                ("pack", CommitButton(log.message)),
            ]
        )
        super().__init__(
            self.pile,
            log.id,
            "left",
        )

    def expand(self) -> None:
        # TODO: this whole page needs to be a tree widget
        if self.extended:
            return
        self.extended = True
        (head,) = self.pile.contents
        self.pile.contents = [
            head,
            *list(
                (u.Text(f"This is a much bigger thing {n}"), ("pack", None))
                for n in range(10)
            ),
        ]

    def contract(self) -> None:
        if not self.extended:
            return
        self.extended = False
        (head, *_) = self.pile.contents
        self.pile.contents = [head]

    def keypress(self, size, key) -> str | None:
        if key == "e":
            self.expand()
            return None
        elif key == "c":
            self.contract()
            return None
        return key


def _nop(_: GitOperation) -> None:
    pass


class LogPage(u.Pile):
    add_operation: typing.Callable[[GitOperation], None] = _nop

    def __init__(
        self,
    ) -> None:
        self.listbox = u.ListBox([])
        super().__init__(
            [
                ("pack", u.Text("on branch main")),
                self.listbox,
            ]
        )

    def give_operation_to(
        self, callable: typing.Callable[[GitOperation], None]
    ) -> None:
        self.add_operation = callable

    def load_commit_data(self, data: git.Commit) -> None:
        self.listbox.body.append(CommitWidget(data))

    def keypress(self, size, key) -> str | None:
        key = super().keypress(size, key)
        item: CommitWidget = self.listbox.focus
        if key == "f":
            self.assign_fixup(item.commit)
        if key == "y":
            self.copy_commit_id(item.commit)
        else:
            return key

    def assign_fixup(self, commit: git.Commit) -> None:
        first_line = commit.message.splitlines()[0]
        self.add_operation(GitOperation.fixup(first_line))

    def copy_commit_id(self, commit: git.Commit) -> None:
        pyperclip.copy(commit.id)
