"""AniList info (no login needed) used for Discord presence and the watch page."""
import re

import requests

from . import config

API = "https://graphql.anilist.co"
Q = """query($s:String){Media(search:$s,type:ANIME){id siteUrl episodes duration status format
seasonYear averageScore genres description(asHtml:false) title{romaji english}
coverImage{extraLarge large} studios(isMain:true){nodes{name}}}}"""


def clean(title):
    return re.sub(r"\s*\([^)]*\)\s*$", "", title).strip()


_mem = {}


def fetch(title):
    key = clean(title).lower()
    if key in _mem:
        return _mem[key]
    cfg = config.load()
    info = cfg.get("meta", {}).get(key)
    if info is None:
        try:
            r = requests.post(API, json={"query": Q, "variables": {"s": clean(title)}}, timeout=6)
            m = r.json()["data"]["Media"]
        except Exception:
            return None
        t = m["title"]
        studios = (m.get("studios") or {}).get("nodes") or []
        info = {"id": m["id"], "url": m["siteUrl"], "title": t.get("english") or t.get("romaji"),
                "romaji": t.get("romaji"), "episodes": m.get("episodes"), "duration": m.get("duration"),
                "status": (m.get("status") or "").replace("_", " ").title(), "format": m.get("format"),
                "year": m.get("seasonYear"), "score": m.get("averageScore"), "genres": m.get("genres") or [],
                "studio": studios[0]["name"] if studios else None,
                "synopsis": re.sub(r"<[^>]+>", "", m.get("description") or "").strip()[:500],
                "cover": (m.get("coverImage") or {}).get("extraLarge") or (m.get("coverImage") or {}).get("large")}
        cache = cfg.setdefault("meta", {})
        cache[key] = info
        while len(cache) > 100:
            cache.pop(next(iter(cache)))
        config.save(cfg)
    _mem[key] = info
    return info
