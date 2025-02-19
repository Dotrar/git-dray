import typing

import pygit2 as git


class GitHandler:
    unstaged_changes: set[git.Patch]
    staged_changes: set[git.Patch]

    def __init__(self) -> None:
        self.repo = git.Repository(".")
        self.unstaged_changes = set()
        self.staged_changes = set()

    def get_unstaged_changes(self) -> set[git.Patch]:
        diff: git.Diff = self.repo.index.diff_to_workdir()

        self.unstaged_changes = {patch for patch in diff}
        return self.unstaged_changes

    def get_staged_changes(self) -> list[git.Patch]:
        pass

    def get_commit_log(self) -> typing.Iterable[git.Commit]:
        yield from self.repo.walk(self.repo.head.target)
