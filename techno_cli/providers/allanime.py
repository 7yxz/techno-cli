"""AllAnime provider (experimental). Logic ported from anipy-cli (GPL-3.0).

The API signs source requests with rotating keys, which are published as a small
JSON file by the anipy-cli project; we fetch it at runtime.
"""
import base64
import hashlib
import json
import re
import sys
import time
from urllib.parse import urljoin

import requests
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEYGEN_URL = ("https://raw.githubusercontent.com/sdaqo/anipy-cli/refs/heads/"
              "key-gen/scripts/keygen/keygen.json")
API = "https://api.mkissa.net/api"
SITE = "https://mkissa.to"
SEARCH_HASH = "a24c500a1b765c68ae1d8dd85174931f661c71369c89b92b88b75a725afc471c"
SHOW_HASH = "043448386c7a686bc2aabfbb6b80f6074e795d350df48015023b079527b0848a"
WANTED = ["Yt-mp4", "S-Mp4", "Uv-mp4", "Luf-Mp4", "Ak", "Default", "Mp4"]


def _ext(h, **extra):
    return json.dumps({"persistedQuery": {"version": 1, "sha256Hash": h}, **extra})


def decode_path(src):
    """Provider ids are hex pairs XOR 56."""
    src = src.replace("--", "")
    return "".join(chr(int(src[i:i + 2], 16) ^ 56) for i in range(0, len(src), 2))


def _res_from_url(u):
    m = re.search(r"(\d{3,4})p", u)
    return int(m.group(1)) if m else 1080


class AllAnime:
    name = "allanime"
    in_all = False  # experimental, opt in with -p allanime
    _keys = None

    def __init__(self):
        self.s = requests.Session()
        self.s.headers["User-Agent"] = (
            "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0")

    # -- crypto --
    def keygen(self, refresh=False):
        if self._keys is None or refresh:
            r = self.s.get(KEYGEN_URL, timeout=20)
            r.raise_for_status()
            self._keys = r.json()
        return self._keys

    def _source_request(self):
        k = self.keygen()
        ts = int(time.time() * 1000) // 300000 * 300000
        payload = {"v": 1, "ts": ts, "epoch": k["epoch"], "buildId": k["build_id"],
                   "qh": k["query_hash"], "k": k["lane"]}
        iv = hashlib.sha256(f"{k['epoch']}:{k['query_hash']}:{ts}".encode()).digest()[:12]
        ct = AESGCM(bytes.fromhex(k["key"])).encrypt(
            iv, json.dumps(payload, separators=(",", ":")).encode(), None)
        return k["query_hash"], base64.b64encode(b"\x01" + iv + ct).decode(), k["lane"], k["build_id"]

    def _decode_tbp(self, tbp):
        k = self.keygen()
        raw = base64.b64decode(tbp)
        iv, body = raw[1:13], raw[13:]
        for key in (bytes.fromhex(k["key"]), k["static_key"].encode()):
            try:
                return json.loads(AESGCM(key).decrypt(iv, body, None).decode())
            except Exception:
                continue
        raise RuntimeError("could not decrypt sources (keys rotated, try again later)")

    # -- api --
    def _check(self, r):
        r.raise_for_status()
        d = r.json()
        if d.get("errors"):
            raise RuntimeError(d["errors"][0].get("message", "allanime error"))
        return d

    def search(self, q):
        variables = {"search": {"query": q}, "limit": 26, "page": 1,
                     "translationType": "sub", "countryOrigin": "ALL"}
        r = self.s.post(API, params={"variables": json.dumps(variables)},
                        json={"variables": variables, "extensions": _ext(SEARCH_HASH)},
                        headers={"Referer": "https://allmanga.to/"}, timeout=20)
        edges = self._check(r)["data"]["shows"]["edges"]
        out = []
        for a in edges:
            eps = a.get("availableEpisodes") or {}
            out.append((f"{a['name']} ({eps.get('sub', 0)} sub, {eps.get('dub', 0)} dub)", a["_id"]))
        return out

    def episodes(self, sid):
        r = self.s.post(API, json={"variables": json.dumps({"_id": sid}),
                                   "extensions": _ext(SHOW_HASH)},
                        headers={"Referer": "https://allmanga.to/"}, timeout=20)
        d = self._check(r)["data"]["show"]["availableEpisodesDetail"]
        eps = d.get("sub") or d.get("dub") or []
        eps = sorted(set(eps), key=lambda e: float(e))
        return [(f"Episode {e}", f"{sid}|{e}") for e in eps]

    def stream(self, _sid, epid, quality, dub=False):
        sid, ep = epid.split("|", 1)
        tt = "dub" if dub else "sub"
        qh, aareq, lane, build = self._source_request()
        r = self.s.get(API, timeout=20, params={
            "variables": json.dumps({"showId": sid, "translationType": tt, "episodeString": ep}),
            "extensions": _ext(qh, aaReq=aareq, k=lane)},
            headers={"Referer": SITE, "Origin": SITE, "x-build-id": build})
        data = self._check(r).get("data") or {}
        if "tobeparsed" in data:
            try:
                data = self._decode_tbp(data["tobeparsed"])
            except RuntimeError:
                self._keys = None
                raise
        if not data.get("episode"):
            sys.exit(f"allanime: no {tt} sources for this episode")

        found = []  # (resolution, url, referer)
        for p in data["episode"]["sourceUrls"]:
            if p["sourceName"] not in WANTED:
                continue
            src = p["sourceUrl"]
            try:
                if p["sourceName"] == "Mp4":
                    t = self.s.get(src, timeout=20).text
                    m = re.search(r'src:\s*"([^"]+)"', t)
                    if m:
                        found.append((1080, m.group(1), "https://www.mp4upload.com"))
                    continue
                if "tools.fast4speed.rsvp" in src:
                    found.append((1080, src, SITE))
                    continue
                path = decode_path(src).replace("clock", "clock.json")
                j = None
                for _ in range(3):
                    rr = self.s.get(f"https://allanime.day{path}", timeout=20,
                                    headers={"Referer": "https://allanime.day/"})
                    if rr.text:
                        j = rr.json()
                        break
                for l in (j or {}).get("links", []):
                    link = l["link"]
                    if "repackager.wixmp.com" in link:
                        parts = link.split(".urlset")[0].replace("repackager.wixmp.com/", "").split(",")
                        for qual in parts[1:-1]:
                            found.append((int(qual.replace("p", "")), parts[0] + qual + parts[-1], SITE))
                        continue
                    ref = (l.get("headers") or {}).get("Referer", SITE)
                    res = _res_from_url(link)
                    try:
                        txt = self.s.get(link, headers={"Referer": ref}, timeout=20).text
                        vs = re.findall(r"RESOLUTION=\d+x(\d+)[^\n]*\n([^\n#]+)", txt)
                        if vs:
                            found += [(int(h), urljoin(link, u.strip()), ref) for h, u in vs]
                            continue
                    except Exception:
                        pass
                    found.append((res, link, ref))
            except Exception:
                continue
        if not found:
            sys.exit("allanime: no playable sources found")
        res, url, ref = min(found, key=lambda f: abs(f[0] - quality))
        return url, {"Referer": ref}, None
