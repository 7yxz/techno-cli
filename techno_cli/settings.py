from . import alias, config
from .ui import Prompt, console, pick

# key: (default, kind, choices, description)
SCHEMA = {
    "command": ("techno-cli", "choice", ["techno-cli", "tcli", "t-cli"], "command name to run it with"),
    "provider": ("animepahe", "choice", ["animepahe", "hianime", "allanime"], "default provider"),
    "quality": (1080, "choice", [360, 480, 720, 1080], "preferred quality"),
    "dub": (False, "bool", None, "dubbed audio by default"),
    "sync_pct": (80, "number", None, "watched % needed to sync trackers"),
    "rpc": (True, "bool", None, "Discord presence (needs --rpc-setup)"),
    "rpc_covers": (True, "bool", None, "AniList cover and info in presence"),
    "watch_page": (True, "bool", None, "info page after each episode"),
    "synopsis": (True, "bool", None, "synopsis on the info page"),
    "mpv_args": ("", "text", None, "extra player args, e.g. --hwdec=no --vo=gpu"),
    "update_check": (True, "bool", None, "daily update notice"),
}


def get(key):
    return config.load().get("settings", {}).get(key, SCHEMA[key][0])


def set_(key, val):
    cfg = config.load()
    cfg.setdefault("settings", {})[key] = val
    config.save(cfg)


def _fmt(v):
    return ("on" if v else "off") if isinstance(v, bool) else (str(v) or "-")


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
                v = pick([(str(c), c) for c in choices], key)
            except SystemExit:
                continue
            if key == "command":
                ok, msg = alias.apply(v)
                console.print(("[green]ok[/] " if ok else "[red]failed[/] ") + msg)
                if not ok:
                    continue
            set_(key, v)
        elif kind == "text":
            set_(key, Prompt.ask(key, default=str(get(key)), show_default=True).strip())
        else:
            v = Prompt.ask(key, default=str(get(key)))
            try:
                set_(key, float(v) if "." in v else int(v))
            except ValueError:
                console.print("[red]not a number[/]")
    console.print("[green]settings saved[/]")
