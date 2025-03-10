import typing

import pygit2 as git
from dto import GitOperation, GitOperationType
import re


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
        filepath = operation.patch.filepath

        if not operation.hunk:
            # add all hunks / just add the whole change
            index.add(filepath)
            index.write()
            return
        # just add the whole hunk.
        # 1. read the file from commit as blob
        index.read()
        old_entry = index[filepath]
        old_blob = self.repo[old_entry.id]

        # get hunk area
        match = re.match(r"@@ -(\d),(\d)", operation.hunk.header)
        if match is None:
            raise ValueError("problem with git")
        start, end = (int(n) for n in match.groups())
        end += start

        # make a new blob data
        new_data = []

        old_data = old_blob.data.decode().splitlines()
        new_data.extend(old_data[:start])
        for line in operation.hunk.lines:
            if line.type == "-":
                continue
            content = line.content
            if content.endswith("\n"):
                content = content[:-1]
            new_data.append(content)
        new_data.extend(old_data[end:])

        new_blob_id = self.repo.create_blob("\n".join(new_data).encode())
        entry = git.IndexEntry(filepath, new_blob_id, git.enums.FileMode.BLOB)
        index.remove(filepath)
        index.write()
        index.add(entry)
        index.write()

    def commit(self) -> None:
        breakpoint()
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
