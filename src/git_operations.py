import typing

import pygit2 as git
from dto import GitOperation, GitOperationType


class GitHandler:
    unstaged_changes: set[git.Patch]
    staged_changes: set[git.Patch]
    operation_feed: typing.Callable | None

    def __init__(self, editor_callback) -> None:
        self.repo = git.Repository(".")
        self.unstaged_changes = set()
        self.staged_changes = set()
        self.operation_feed = None

        self.editor_callback = editor_callback

    def get_unstaged_changes(self) -> set[git.Patch]:
        diff: git.Diff = self.repo.index.diff_to_workdir()

        self.unstaged_changes = set(diff)
        return self.unstaged_changes

    def get_staged_changes(self) -> list[git.Patch]:
        head_commit: git.Commit = self.repo[self.repo.head.target]
        diff: git.Diff = self.repo.index.diff_to_tree(head_commit.tree)

        self.staged_changes = set(diff)
        return self.staged_changes

    def get_commit_log(self) -> typing.Iterable[git.Commit]:
        yield from self.repo.walk(self.repo.head.target)

    def do_operation(self, operation: GitOperation) -> None:
        if operation.type == GitOperationType.COMMIT:
            self.commit()
        elif operation.type == GitOperationType.AMEND:
            self.amend()
        elif operation.type == GitOperationType.FIXUP:
            self.fixup(operation.target)
        elif operation.type == GitOperationType.STAGE:
            self.stage(operation)

    def unstage(self, operation: GitOperation) -> None:
        index: git.Index = self.repo.index

        if not operation.hunk:
            index.remove(operation.patch.filepath)
            index.write()
            return

    def stage(self, operation: GitOperation) -> None:
        index: git.Index = self.repo.index

        if not operation.hunk:
            # add all hunks / just add the whole change
            index.add(operation.patch.filepath)
            index.write()
            return

    def _load_template(self) -> str:
        config = self.repo.config
        if "commit.template" not in config:
            return
        template_file = Path(config["commit.template"])
        if not template_file.exists():
            return
        msg_file = Path(f"{self.repo.path}") / "COMMIT_EDITMSG"
        with template_file.open("r") as tf:
            with msg_file.open("w") as mf:
                mf.write(tf.read())

    def external_editor_git_message(self) -> str:
        msg_file = Path(f"{self.repo.path}") / "COMMIT_EDITMSG"
        if not self._load_template():
            msg_file.open("w").write("")
        self.editor_callback(str(msg_file))
        return self._read_from_msg_file()

    def _read_from_msg_file(self) -> str:
        msg_file = Path(f"{self.repo.path}") / "COMMIT_EDITMSG"
        return "\n".join(
            line.strip() for line in msg_file.open("r").splitlines() if not line.startswith("#")
        )

    def commit(self) -> None:
        message = self.external_editor_git_message()
        if not message:
            return
        index: git.Index = self.repo.index
        author = git.Signature("Drebot", "dre.westcook@kraken.tech")
        tree = index.write_tree()
        parents = [self.repo.head.target]
        self.repo.create_commit(self.repo.head.name, author, author, message, tree, parents)
        self.staged_changes = set()

    def amend(self) -> None:
        index: git.Index = self.repo.index
        tree = index.write_tree()
        last_commit = self.repo[self.repo.head.target]
        self.repo.amend_commit(last_commit, self.repo.head.name, tree=tree)
        self.staged_changes = set()

    def fixup(self, target: str) -> None:
        index: git.Index = self.repo.index
        author = git.Signature("Drebot", "dre.westcook@kraken.tech")
        tree = index.write_tree()
        parents = [self.repo.head.target]
        self.repo.create_commit(
            self.repo.head.name,
            author,
            author,
            f"fixup! {target}",
            tree,
            parents,
        )
        self.staged_changes = set()
