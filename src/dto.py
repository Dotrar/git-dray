from __future__ import annotations
import pygit2 as git
import enum
from attrs import frozen


class GitOperationType(enum.Enum):
    STAGE = "STAGE"
    UNSTAGE = "UNSTAGE"
    RESET = "RESET"
    COMMIT = "COMMIT"
    AMEND = "AMEND"
    FIXUP = "FIXUP"


@frozen
class GitOperation:
    type: GitOperationType
    patch: git.Patch | None
    hunk: git.DiffHunk | None
    lines: list[git.DiffLine]
    target: str

    @classmethod
    def commit(cls) -> GitOperation:
        return cls(GitOperationType.COMMIT, None, None, [], "")

    @classmethod
    def amend(cls) -> GitOperation:
        return cls(GitOperationType.AMEND, None, None, [], "")

    @classmethod
    def fixup(cls, target: str) -> GitOperation:
        return cls(GitOperationType.AMEND, None, None, [], target)
