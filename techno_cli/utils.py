import os
import re
import shutil
import subprocess
import sys

import requests

UA = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"
session = requests.Session()
session.headers["User-Agent"] = UA


def hint_install(tool):
    if sys.platform == "darwin":
        return f"brew install {tool}"
    if shutil.which("pacman"):
        return f"sudo pacman -S {tool}"
    return f"sudo apt install {tool}"


def pick(items, label):
    """items: list of (text, value). Returns the chosen value."""
    if not items:
        sys.exit("nothing found")
    if shutil.which("fzf"):
        lines = [f"{i}\t{t}" for i, (t, _) in enumerate(items)]
        p = subprocess.run(["fzf", "--with-nth=2..", "--delimiter=\t", "--prompt", label + "> "],
                           input="\n".join(lines), text=True, stdout=subprocess.PIPE)
        if not p.stdout.strip():
            sys.exit(0)
        return items[int(p.stdout.split("\t")[0])][1]
    for i, (t, _) in enumerate(items, 1):
        print(f"{i:>3}. {t}")
    while True:
        n = input(f"{label} #: ").strip()
        if n.isdigit() and 1 <= int(n) <= len(items):
            return items[int(n) - 1][1]


def unpack_packer(src):
    """Unpack Dean Edwards p.a.c.k.e.r JS (used by kwik)."""
    m = re.search(r"}\('(.*)',(\d+),(\d+),'(.*?)'\.split\('\|'\)", src, re.S)
    if not m:
        return ""
    p, a, c, k = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4).split("|")
    digits = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

    def enc(n):
        return ("" if n < a else enc(n // a)) + digits[n % a]

    d = {enc(i): (k[i] or enc(i)) for i in range(c)}
    return re.sub(r"\b\w+\b", lambda x: d.get(x.group(0), x.group(0)), p)


def find_player():
    player = os.environ.get("TECHNO_PLAYER", "mpv")
    if not shutil.which(player):
        sys.exit(f"{player} not found. Install it: {hint_install('mpv')}")
    return player


def play(url, headers, title):
    cmd = [find_player(), f"--force-media-title={title}", url]
    if headers:
        hf = ",".join(f"{k}: {v}" for k, v in headers.items())
        cmd.insert(1, f"--http-header-fields={hf}")
    subprocess.run(cmd)
