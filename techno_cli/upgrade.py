import os
import re
import shutil
import subprocess
import sys
import time

import requests

from . import __version__, config
from .ui import console, error, warn

REPO = "7yxz/techno-cli"
RAW = f"https://raw.githubusercontent.com/{REPO}/main/techno_cli/__init__.py"
ZIP = f"https://github.com/{REPO}/archive/refs/heads/main.zip"


def _key(v):
    return tuple(int(x) for x in re.findall(r"\d+", v))


def latest(timeout=15):
    r = requests.get(RAW, timeout=timeout)
    r.raise_for_status()
    return re.search(r'__version__\s*=\s*"([^"]+)"', r.text).group(1)


def upgrade(force=False):
    try:
        new = latest()
    except Exception as e:
        error(f"could not check for updates ({e})")
        return
    if _key(new) <= _key(__version__) and not force:
        console.print(f"[green]already up to date[/] (v{__version__})")
        return
    console.print(f"updating [dim]v{__version__}[/] -> [bold]v{new}[/]")
    if "pipx" in sys.prefix and shutil.which("pipx"):
        cmd = ["pipx", "install", "--force", ZIP]
    else:
        cmd = [sys.executable, "-m", "pip", "install", "--upgrade", ZIP]
    if subprocess.run(cmd).returncode == 0:
        console.print("[green]done[/], run techno-cli -v to confirm")
    else:
        warn("upgrade failed. Try manually: pipx install --force " + ZIP)


def notice():
    """Once a day, tell the user if a newer version exists (silent on any error)."""
    if os.environ.get("TECHNO_NO_UPDATE_CHECK"):
        return
    try:
        cfg = config.load()
        c = cfg.get("update_check", {})
        if time.time() - c.get("t", 0) > 86400:
            c = {"t": time.time(), "v": latest(timeout=3)}
            cfg["update_check"] = c
            config.save(cfg)
        if c.get("v") and _key(c["v"]) > _key(__version__):
            console.print(f"[yellow]update available:[/] v{c['v']} (you have v{__version__}), "
                          "run [cyan]techno-cli --upgrade[/]")
    except Exception:
        pass
