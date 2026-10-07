"""Lets you pick the command name (techno-cli, tcli or t-cli) by adding a symlink next to it."""
import os
import shutil

ALIASES = ["tcli", "t-cli"]


def apply(name):
    """Returns (ok, message). techno-cli itself always keeps working."""
    main = shutil.which("techno-cli")
    if not main:
        return False, "could not find techno-cli on your PATH"
    d = os.path.dirname(main)
    try:
        for a in ALIASES:  # drop alias links we made before
            link = os.path.join(d, a)
            if a != name and os.path.islink(link) and os.readlink(link) == main:
                os.remove(link)
        if name in ALIASES:
            link = os.path.join(d, name)
            if os.path.lexists(link):
                if not (os.path.islink(link) and os.readlink(link) == main):
                    return False, f"{link} already exists and is not ours"
            else:
                os.symlink(main, link)
            return True, f"you can now run [bold]{name}[/] (techno-cli still works too)"
        return True, "using [bold]techno-cli[/]"
    except OSError as e:
        return False, f"could not create the alias ({e})"
