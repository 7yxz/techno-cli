import os

from ..utils import session


class HiAnime:
    """Uses a self-hosted aniwatch-api instance (github.com/ghoshRitesh12/aniwatch-api)."""
    name = "hianime"

    def __init__(self):
        base = os.environ.get("HIANIME_API", "http://localhost:4000").rstrip("/")
        self.api = base + "/api/v2/hianime"

    def _j(self, path, **params):
        r = session.get(self.api + path, params=params, timeout=30)
        r.raise_for_status()
        return r.json()["data"]

    def search(self, q):
        d = self._j("/search", q=q)
        return [(f"{a['name']} ({a.get('type', '?')})", a["id"]) for a in d["animes"]]

    def episodes(self, aid):
        d = self._j(f"/anime/{aid}/episodes")
        return [(f"Episode {e['number']}", e["episodeId"]) for e in d["episodes"]]

    def stream(self, _aid, epid, quality):
        d = self._j("/episode/sources", animeEpisodeId=epid, server="hd-1", category="sub")
        src = next((s for s in d["sources"] if s.get("isM3U8")), d["sources"][0])
        return src["url"], d.get("headers") or {"Referer": "https://megacloud.blog/"}
