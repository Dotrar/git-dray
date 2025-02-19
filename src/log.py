import pygit2 as git
import urwid as u


class CommitButton(u.SelectableIcon):
    pass


class CommitWidget(u.LineBox):
    extended: bool

    def __init__(self, log: git.Commit):
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
        if self.extended:
            return
        self.extended = True
        (head,) = self.pile.contents
        self.pile.contents = [
            head,
            (u.Text("This is a much bigger thing"), ("pack", None)),
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


class LogPage(u.Pile):
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

    def load_commit_data(self, data: git.Commit) -> None:
        self.listbox.body.append(CommitWidget(data))
