import argparse
import sys

from . import __version__
from .providers import DEFAULT, PROVIDERS
from .utils import find_player, pick, play


def build_parser():
    ap = argparse.ArgumentParser(
        prog="techno-cli", add_help=False,
        description="Watch anime from your terminal.",
        epilog="examples:\n  techno-cli naruto\n  techno-cli -p hianime one piece\n"
               "  techno-cli -a -q 720 frieren\n  techno-cli -e 5 bleach\n\n"
               "env:\n  HIANIME_API     aniwatch-api URL (default http://localhost:4000)\n"
               "  PAHE_COOKIE     cookie for animepahe if blocked\n"
               "  TECHNO_PLAYER   player binary (default mpv)",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("query", nargs="*", help="search query")
    ap.add_argument("-p", "--provider", choices=PROVIDERS, default=DEFAULT,
                    help=f"provider to use (default: {DEFAULT})")
    ap.add_argument("-a", "--all", action="store_true", help="search all providers")
    ap.add_argument("-q", "--quality", type=int, default=1080, help="preferred quality (default 1080)")
    ap.add_argument("-e", "--episode", help="start at this episode number")
    ap.add_argument("-v", "--version", action="version", version=f"techno-cli {__version__}")
    ap.add_argument("-h", "-help", "--help", action="help", help="show this help and exit")
    return ap


def choose_episode(eps):
    epid = pick(eps, "episode")
    return next(i for i, e in enumerate(eps) if e[1] == epid)


def main():
    try:
        _run()
    except (KeyboardInterrupt, EOFError):
        print()


def _run():
    a = build_parser().parse_args()
    find_player()

    q = " ".join(a.query) or input("Search anime: ").strip()
    names = list(PROVIDERS) if a.all else [a.provider]

    results = []
    for n in names:
        try:
            for t, i in PROVIDERS[n]().search(q):
                results.append((f"[{n}] {t}", (n, i, t)))
        except Exception as e:
            print(f"{n}: search failed ({e})", file=sys.stderr)
    prov_name, aid, title = pick(results, "anime")
    prov = PROVIDERS[prov_name]()

    eps = prov.episodes(aid)
    if a.episode:
        idx = next((i for i, (l, _) in enumerate(eps) if l.endswith(f" {a.episode}")), 0)
    else:
        idx = choose_episode(eps)

    while True:
        label, epid = eps[idx]
        print(f"\nPlaying {title} - {label}")
        try:
            url, hdrs = prov.stream(aid, epid, a.quality)
            play(url, hdrs, f"{title} - {label}")
        except Exception as e:
            print(f"error: {e}", file=sys.stderr)
        cmd = input("[n]ext [p]rev [r]eplay [s]elect [q]uit: ").strip().lower()
        if cmd == "n" and idx + 1 < len(eps):
            idx += 1
        elif cmd == "p" and idx > 0:
            idx -= 1
        elif cmd == "s":
            idx = choose_episode(eps)
        elif cmd != "r":
            break

