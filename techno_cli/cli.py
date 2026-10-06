import argparse
import os
import re
import sys

import time

from rich import box
from rich.table import Table

from . import __version__, config, rpc as rpc_mod
from .providers import DEFAULT, PROVIDERS
from .sync import TRACKERS, Syncer, login, logout, status
from .ui import Confirm, Prompt, banner, console, controls, error, now_playing, pick, warn
from .utils import find_player, play

SYNC_PCT = float(os.environ.get("TECHNO_SYNC_PCT", 80))


def build_parser():
    ap = argparse.ArgumentParser(
        prog="techno-cli", add_help=False,
        description="Watch anime from your terminal.",
        epilog="examples:\n  techno-cli naruto\n  techno-cli -p hianime one piece\n"
               "  techno-cli -a -q 720 frieren\n  techno-cli -e 5 -d bleach\n"
               "  techno-cli --login anilist\n  techno-cli --doctor\n\n"
               "providers: animepahe (default), hianime, allanime (experimental), aniwatch (self-hosted API)\n"
               "trackers:  anilist, mal, kitsu (progress syncs automatically once logged in)\n\n"
               "env (all optional):\n"
               "  PAHE_URL / PAHE_COOKIE   override animepahe mirror / add cookie\n"
               "  HIANIME_URL              override hianime mirror\n"
               "  HIANIME_API              aniwatch-api URL (default http://localhost:4000)\n"
               "  TECHNO_PLAYER            player binary (default mpv)\n"
               "  TECHNO_SYNC_PCT          watched % needed to sync (default 80)",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("query", nargs="*", help="search query")
    ap.add_argument("-p", "--provider", choices=PROVIDERS, default=DEFAULT,
                    help=f"provider to use (default: {DEFAULT})")
    ap.add_argument("-a", "--all", action="store_true", help="search all providers")
    ap.add_argument("-d", "--dub", action="store_true", help="play dubbed audio")
    ap.add_argument("-q", "--quality", type=int, default=1080, help="preferred quality (default 1080)")
    ap.add_argument("-e", "--episode", help="start at this episode number")
    ap.add_argument("--login", choices=TRACKERS, metavar="TRACKER", help="log in to anilist, mal or kitsu")
    ap.add_argument("--logout", choices=TRACKERS, metavar="TRACKER", help="log out of a tracker")
    ap.add_argument("--rpc-setup", action="store_true", help="set up Discord Rich Presence")
    ap.add_argument("--no-rpc", action="store_true", help="disable Discord Rich Presence this run")
    ap.add_argument("--doctor", action="store_true", help="test every provider and show what works")
    ap.add_argument("--status", action="store_true", help="show tracker login status")
    ap.add_argument("--no-sync", action="store_true", help="do not update trackers this run")
    ap.add_argument("--remap", action="store_true", help="re-pick the tracker match for this anime")
    ap.add_argument("-v", "--version", action="version", version=f"techno-cli {__version__}")
    ap.add_argument("-h", "-help", "--help", action="help", help="show this help and exit")
    return ap


def ep_num(label):
    m = re.search(r"(\d+)(?:\.\d+)?$", label)
    return int(m.group(1)) if m else None


def choose_episode(eps):
    epid = pick(eps, "episode")
    return next(i for i, e in enumerate(eps) if e[1] == epid)


def _step(fn):
    t0 = time.time()
    try:
        return True, fn(), time.time() - t0
    except (Exception, SystemExit) as e:
        msg = e.code if isinstance(e, SystemExit) else e
        return False, str(msg or type(e).__name__), time.time() - t0


def doctor():
    """Runs search -> episodes -> stream against every provider."""
    t = Table(title="provider check", box=box.SIMPLE_HEAD, header_style="bold cyan")
    for c in ("provider", "search", "episodes", "stream", "notes"):
        t.add_column(c)
    for name, cls in PROVIDERS.items():
        if name == "aniwatch" and not os.environ.get("HIANIME_API"):
            t.add_row(name, "-", "-", "-", "[dim]skipped (HIANIME_API not set)[/]")
            continue
        cells, note, state = [], "", {}
        with console.status(f"Testing {name}..."):
            p = cls()
            ok, res, dt = _step(lambda: p.search("naruto"))
            cells.append(f"[green]ok[/] {dt:.1f}s" if ok and res else "[red]fail[/]")
            if not ok or not res:
                note = res if not ok else "no results"
            else:
                state["aid"] = res[0][1]
                ok, res, dt = _step(lambda: p.episodes(state["aid"]))
                cells.append(f"[green]ok[/] {dt:.1f}s" if ok and res else "[red]fail[/]")
                if not ok or not res:
                    note = res if not ok else "no episodes"
                else:
                    state["ep"] = res[0][1]
                    ok, res, dt = _step(lambda: p.stream(state["aid"], state["ep"], 720, False))
                    cells.append(f"[green]ok[/] {dt:.1f}s" if ok else "[red]fail[/]")
                    if not ok:
                        note = res
        while len(cells) < 3:
            cells.append("[dim]-[/]")
        t.add_row(name, *cells, note[:90])
    console.print(t)


def rpc_setup():
    cfg = config.load()
    console.print("Create an app at [cyan]https://discord.com/developers/applications[/], name it what "
                  "you want shown as 'Watching'.\nOptional: upload an image named [cyan]techno-cli[/] under "
                  "Rich Presence > Art Assets.")
    cfg["discord_client_id"] = Prompt.ask("Application ID").strip()
    config.save(cfg)
    console.print("[green]saved[/], Discord must be running while you watch")


def _run():
    a = build_parser().parse_args()
    if a.rpc_setup:
        return rpc_setup()
    if a.doctor:
        return doctor()
    if a.login:
        return login(a.login)
    if a.logout:
        return logout(a.logout)
    if a.status:
        return status()

    find_player()
    banner(sorted(config.load().get("auth", {})) or None)
    q = " ".join(a.query) or Prompt.ask("[bold magenta]search anime[/]").strip()
    names = [n for n, c in PROVIDERS.items() if c.in_all] if a.all else [a.provider]

    results = []
    for n in names:
        try:
            with console.status(f"Searching {n}..."):
                found = PROVIDERS[n]().search(q)
            results += [(f"[{n}] {t}", (n, i, t)) for t, i in found]
        except (Exception, SystemExit) as e:
            warn(f"{n}: search failed ({e})")
    prov_name, aid, title = pick(results, "anime")
    prov = PROVIDERS[prov_name]()

    with console.status("Loading episodes..."):
        eps = prov.episodes(aid)
    if not eps:
        error("no episodes found")
        return

    rpc = None if a.no_rpc else rpc_mod.get(config.load())
    sy = None if a.no_sync else Syncer(prov_name, aid, title, a.remap)
    if sy and not sy.active:
        sy = None
    idx = None
    if sy:
        sy.resolve()
        last = sy.progress() if sy.active else 0
        if last and not a.episode:
            nxt = next((i for i, (l, _) in enumerate(eps) if ep_num(l) == last + 1), None)
            if nxt is not None and Confirm.ask(f"Continue from episode {last + 1}?", default=True):
                idx = nxt
    if idx is None:
        if a.episode:
            idx = next((i for i, (l, _) in enumerate(eps) if ep_num(l) == int(a.episode)), 0)
        else:
            idx = choose_episode(eps)

    while True:
        label, epid = eps[idx]
        console.rule(style="dim")
        now_playing(title, label, prov_name, a.quality, a.dub)
        try:
            with console.status("Fetching stream..."):
                url, hdrs, sub = prov.stream(aid, epid, a.quality, a.dub)
            if rpc:
                rpc.update(title, label, prov_name)
            pct = play(url, hdrs, f"{title} - {label}", sub)
            if rpc:
                rpc.clear()
            n = ep_num(label)
            if sy and sy.active and n and (pct < 0 or pct >= SYNC_PCT):
                sy.update(n)
            elif sy and sy.active and pct >= 0:
                console.print(f"[dim]watched {pct:.0f}%, not synced (needs {SYNC_PCT:.0f}%)[/]")
        except SystemExit as e:
            error(e.code if isinstance(e.code, str) else "failed")
        except Exception as e:
            error(e)
        cmd = controls()
        if cmd == "n" and idx + 1 < len(eps):
            idx += 1
        elif cmd == "n":
            console.print("[dim]that was the last episode[/]")
            break
        elif cmd == "p" and idx > 0:
            idx -= 1
        elif cmd == "s":
            idx = choose_episode(eps)
        elif cmd == "q":
            break


def main():
    try:
        _run()
    except (KeyboardInterrupt, EOFError):
        print()
