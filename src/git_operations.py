import typing

import pygit2 as git
from dto import GitOperation, GitOperationType


class GitHandler:
    operation_feed: typing.Callable | None

    def __init__(self, editor_callback) -> None:
        self.repo = git.Repository(".")
        self.operation_feed = None

        self.editor_callback = editor_callback

    def get_unstaged_changes(self) -> set[git.Patch]:
        diff: git.Diff = self.repo.index.diff_to_workdir()
        return set(diff)

    def get_staged_changes(self) -> list[git.Patch]:
        head_commit: git.Commit = self.repo[self.repo.head.target]
        diff: git.Diff = self.repo.index.diff_to_tree(head_commit.tree)
        return set(diff)

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

    def commit(self) -> None:
        self.editor_callback()

    def amend(self) -> None:
        index: git.Index = self.repo.index
        tree = index.write_tree()
        last_commit = self.repo[self.repo.head.target]
        self.repo.amend_commit(last_commit, self.repo.head.name, tree=tree)

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
