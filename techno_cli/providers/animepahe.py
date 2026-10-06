import os
import re
import sys

from ..utils import session, unpack_packer


class AnimePahe:
    name = "animepahe"
    base = "https://animepahe.ru"

    def _get(self, url, **kw):
        # DDoS-Guard cookie, if needed: export PAHE_COOKIE="__ddg1_=...; ..."
        h = {"Referer": self.base + "/"}
        if os.environ.get("PAHE_COOKIE"):
            h["Cookie"] = os.environ["PAHE_COOKIE"]
        r = session.get(url, headers=h, timeout=20, **kw)
        r.raise_for_status()
        return r

    def search(self, q):
        d = self._get(f"{self.base}/api", params={"m": "search", "q": q}).json()
        return [(f"{a['title']} ({a.get('year', '?')}, {a.get('episodes', '?')} eps)", a["session"])
                for a in d.get("data", [])]

    def episodes(self, sid):
        out, page = [], 1
        while True:
            d = self._get(f"{self.base}/api", params={
                "m": "release", "id": sid, "sort": "episode_asc", "page": page}).json()
            out += [(f"Episode {e['episode']}", f"{sid}/{e['session']}") for e in d["data"]]
            if page >= d.get("last_page", 1):
                break
            page += 1
        return out

    def stream(self, _sid, epid, quality):
        html = self._get(f"{self.base}/play/{epid}").text
        opts = re.findall(
            r'data-src="(https://kwik[^"]+)"[^>]*data-resolution="(\d+)"[^>]*data-audio="(\w+)"', html)
        if not opts:
            sys.exit("no kwik sources found (blocked or layout changed)")
        # prefer sub (jpn), then closest to requested quality
        opts.sort(key=lambda o: (o[2] != "jpn", abs(int(o[1]) - quality)))
        page = session.get(opts[0][0], headers={"Referer": self.base + "/"}, timeout=20).text
        m = re.search(r"https?://[^'\"\s]+\.m3u8", unpack_packer(page))
        if not m:
            sys.exit("could not extract m3u8 from kwik")
        return m.group(0), {"Referer": "https://kwik.si/"}
