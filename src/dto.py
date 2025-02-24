from __future__ import annotations
import pygit2 as git
import enum
import typing
from attrs import frozen


class GitOperationType(enum.Enum):
    STAGE = "STAGE"
    UNSTAGE = "UNSTAGE"
    RESET = "RESET"
    COMMIT = "COMMIT"
    AMEND = "AMEND"
    FIXUP = "FIXUP"


@frozen
class DreLine:
    content: str
    type: str

    @classmethod
    def from_line(cls, line: git.DiffLine) -> DreLine:
        return DreLine(line.content, line.origin)


@frozen
class DreHunk:
    header: str
    lines: tuple[DreLine]

    @classmethod
    def from_hunk(cls, hunk: git.DiffHunk) -> DreHunk:
        return DreHunk(hunk.header, tuple(DreLine.from_line(l) for l in hunk.lines))


@frozen
class DrePatch:
    """fake patch like object, which indicates what real patch to use"""

    header: str
    filepath: str
    hunks: tuple[DreHunk]

    @classmethod
    def from_patch(cls, patch: git.Patch) -> DrePatch:
        patch_header = "\n".join(patch.text.splitlines()[:4])
        filepath = patch.delta.new_file.path
        return DrePatch(patch_header, filepath, tuple(DreHunk.from_hunk(h) for h in patch.hunks))


@frozen
class GitOperation:
    type: GitOperationType
    patch: DrePatch | None
    hunk: DreHunk | None
    lines: list[DreLine]
    target: str

    @classmethod
    def commit(cls) -> GitOperation:
        return cls(GitOperationType.COMMIT, None, None, [], "")

    @classmethod
    def amend(cls) -> GitOperation:
        return cls(GitOperationType.AMEND, None, None, [], "")

    @classmethod
    def fixup(cls, target: str) -> GitOperation:
        return cls(GitOperationType.FIXUP, None, None, [], target)

    @classmethod
    def stage(
        cls, patch: DrePatch | None, hunk: DreHunk | None, lines: list[DreLine]
    ) -> GitOperation:
        return cls(GitOperationType.STAGE, patch, hunk, lines or [], "")

    @classmethod
    def unstage(
        cls, patch: DrePatch | None, hunk: DreHunk | None, lines: list[DreLine]
    ) -> GitOperation:
        return cls(GitOperationType.UNSTAGE, patch, hunk, lines or [], "")
