from . import config
from .ui import Prompt, console, pick

# key: (default, kind, choices, description)
SCHEMA = {
    "provider": ("animepahe", "choice", ["animepahe", "hianime", "allanime"], "default provider"),
    "quality": (1080, "choice", [360, 480, 720, 1080], "preferred quality"),
    "dub": (False, "bool", None, "dubbed audio by default"),
    "sync_pct": (80, "number", None, "watched % needed to sync trackers"),
    "rpc": (True, "bool", None, "Discord presence (needs --rpc-setup)"),
    "rpc_covers": (True, "bool", None, "AniList cover and info in presence"),
    "watch_page": (True, "bool", None, "info page after each episode"),
    "synopsis": (True, "bool", None, "synopsis on the info page"),
    "update_check": (True, "bool", None, "daily update notice"),
}


def get(key):
    return config.load().get("settings", {}).get(key, SCHEMA[key][0])


def set_(key, val):
    cfg = config.load()
    cfg.setdefault("settings", {})[key] = val
    config.save(cfg)


def _fmt(v):
    return ("on" if v else "off") if isinstance(v, bool) else str(v)


def menu():
    """Full-screen settings page."""
    while True:
        items = [(f"{k:<13} {_fmt(get(k)):<10} {d[3]}", k) for k, d in SCHEMA.items()]
        try:
            key = pick(items + [("done", None)], "settings")
        except SystemExit:
            break
        if key is None:
            break
        _, kind, choices, _ = SCHEMA[key]
        if kind == "bool":
            set_(key, not get(key))
        elif kind == "choice":
            try:
                set_(key, pick([(str(c), c) for c in choices], key))
            except SystemExit:
                continue
        else:
            v = Prompt.ask(key, default=str(get(key)))
            try:
                set_(key, float(v) if "." in v else int(v))
            except ValueError:
                console.print("[red]not a number[/]")
    console.print("[green]settings saved[/]")
