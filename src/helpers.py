from dto import DrePatch, DreHunk, DreLine


class NonRelatedHunk(Exception):
    "Hunk and patch don't relate"


def remove_hunk_from_patch(p: DrePatch, h: DreHunk) -> DrePatch | None:
    """
    Remove the hunk from the patch, return a new patch
    object, or None if the patch is now empty
    """
    if h not in p.hunks:
        raise NonRelatedHunk

    if len(p.hunks) == 1:
        return None

    return DrePatch(p.header, p.filepath, tuple(hh for hh in p.hunks if hh != h))


def duplicate_to_solo_hunk(p: DrePatch, h: DreHunk) -> DrePatch:
    return DrePatch(p.header, p.filepath, (h,))


def add_hunk_to_patch(p: DrePatch, h: DreHunk) -> DrePatch:
    return DrePatch(p.header, p.filepath, tuple(hh for hh in [*p.hunks, h]))


def find_matching_patch(p: DrePatch, container: set[DrePatch]) -> DrePatch | None:
    for pp in list(container):
        if pp.header == p.header:
            return pp
    return None
