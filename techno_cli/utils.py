import os
import shutil
import subprocess
import sys

try:
    # impersonates a real Chrome TLS/HTTP2 fingerprint, gets past most Cloudflare checks
    from curl_cffi import requests as _cr
    session = _cr.Session(impersonate="chrome")
    IMPERSONATE = True
except Exception:
    import requests
    session = requests.Session()
    session.headers["User-Agent"] = (
        "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0")
    IMPERSONATE = False


def hint_install(tool):
    if sys.platform == "darwin":
        return f"brew install {tool}"
    if shutil.which("pacman"):
        return f"sudo pacman -S {tool}"
    return f"sudo apt install {tool}"


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


def _poll_percent(sock, proc, box):
    """Ask mpv for percent-pos every 2s over its IPC socket; keeps the last value."""
    import json
    import socket
    import time
    while proc.poll() is None:
        try:
            c = socket.socket(socket.AF_UNIX)
            c.settimeout(1)
            c.connect(sock)
            c.sendall(b'{"command":["get_property","percent-pos"]}\n')
            for line in c.recv(4096).decode().splitlines():
                d = json.loads(line)
                if isinstance(d.get("data"), (int, float)):
                    box[0] = float(d["data"])
            c.close()
        except Exception:
            pass
        time.sleep(2)


def play(url, headers, title, sub=None):
    """Plays and returns watched percent (0-100), or -1 if the player can't report it."""
    import threading
    player = find_player()
    cmd = [player, f"--force-media-title={title}", url]
    if headers:
        hf = ",".join(f"{k}: {v}" for k, v in headers.items())
        cmd.insert(1, f"--http-header-fields={hf}")
    if sub:
        cmd.insert(1, f"--sub-file={sub}")
    import shlex
    from . import settings
    cmd[1:1] = shlex.split(settings.get("mpv_args") or "")
    if not os.path.basename(player).startswith("mpv"):
        subprocess.run(cmd)
        return -1.0
    sock = f"/tmp/techno-cli-{os.getpid()}.sock"
    cmd.insert(1, f"--input-ipc-server={sock}")
    proc = subprocess.Popen(cmd)
    pct = [0.0]
    threading.Thread(target=_poll_percent, args=(sock, proc, pct), daemon=True).start()
    proc.wait()
    try:
        os.remove(sock)
    except OSError:
        pass
    return pct[0]
