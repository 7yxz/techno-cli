import difflib
import re

from .. import config
from rich import box
from rich.table import Table

from ..ui import console, pick, warn
from .anilist import AniList
from .kitsu import Kitsu
from .mal import MAL

TRACKERS = {"anilist": AniList, "mal": MAL, "kitsu": Kitsu}


def _norm(s):
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


def _score(q, cand):
    return max(difflib.SequenceMatcher(None, _norm(q), _norm(t)).ratio() for t in cand["titles"])


def login(name):
    cfg = config.load()
    cls = TRACKERS[name]
    try:
        cfg.setdefault("auth", {})[name] = cls.login(cfg)
        who = cls(cfg).whoami()
    except Exception as e:
        cfg.get("auth", {}).pop(name, None)
        warn(f"{name} login failed: {e}")
        return
    config.save(cfg)
    console.print(f"[green]logged in[/] to {name} as [bold]{who}[/]")


def logout(name):
    cfg = config.load()
    cfg.get("auth", {}).pop(name, None)
    cfg["map"] = {k: v for k, v in cfg.get("map", {}).items() if not k.startswith(name + "|")}
    config.save(cfg)
    console.print(f"logged out of {name}")


def status():
    cfg = config.load()
    t = Table(box=box.SIMPLE_HEAD, header_style="bold cyan")
    t.add_column("tracker")
    t.add_column("status")
    for n, cls in TRACKERS.items():
        if n not in cfg.get("auth", {}):
            t.add_row(n, "[dim]not logged in[/]")
            continue
        try:
            t.add_row(n, f"[green]{cls(cfg).whoami()}[/]")
        except Exception as e:
            t.add_row(n, f"[red]error: {e}[/]")
    console.print(t)


class Syncer:
    """Matches a provider's anime to each logged-in tracker, reads/writes progress."""

    def __init__(self, provider, aid, title, remap=False):
        self.key, self.title, self.remap = f"{provider}|{aid}", title, remap
        self.cfg = config.load()
        auth = self.cfg.get("auth", {})
        self.trackers = [cls(self.cfg) for n, cls in TRACKERS.items() if n in auth]
        self.maps, self.entries = {}, {}

    @property
    def active(self):
        return bool(self.trackers)

    def _drop(self, t, why):
        warn(f"{t.name}: {why}, skipping")
        self.trackers.remove(t)

    def resolve(self):
        for t in list(self.trackers):
            ck = f"{t.name}|{self.key}"
            m = None if self.remap else self.cfg.get("map", {}).get(ck)
            if not m:
                try:
                    with console.status(f"Matching on {t.name}..."):
                        cands = t.search(self.title)
                except Exception as e:
                    self._drop(t, f"search failed ({e})")
                    continue
                if not cands:
                    self._drop(t, "no match found")
                    continue
                cands.sort(key=lambda c: -_score(self.title, c))
                best = cands[0]
                if _score(self.title, best) < 0.9:
                    items = [(f"{c['titles'][0]} ({c.get('total') or '?'} eps)", c) for c in cands]
                    best = pick(items + [(f"skip {t.name}", None)], f"{t.name} match")
                    if best is None:
                        self._drop(t, "skipped")
                        continue
                m = {"id": best["id"], "title": best["titles"][0], "total": best.get("total")}
                self.cfg.setdefault("map", {})[ck] = m
                config.save(self.cfg)
            self.maps[t.name] = m

    def progress(self):
        best = 0
        for t in list(self.trackers):
            try:
                e = self.entries[t.name] = t.entry(self.maps[t.name]["id"])
                best = max(best, e.get("progress") or 0)
            except Exception as ex:
                self._drop(t, f"could not read list ({ex})")
        return best

    def update(self, ep):
        for t in self.trackers:
            m = self.maps[t.name]
            try:
                e = self.entries.get(t.name)
                if e is None:
                    e = t.entry(m["id"])
                if (e.get("progress") or 0) >= ep:
                    console.print(f"[dim]{t.name}: already at episode {e['progress']}[/]")
                    continue
                self.entries[t.name] = t.update(m["id"], ep, m.get("total"), e)
                console.print(f"[green]synced[/] {t.name}: {m['title']} -> episode {ep}")
            except Exception as ex:
                warn(f"{t.name} sync failed: {ex}")
