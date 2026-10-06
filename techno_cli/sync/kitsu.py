import time

import requests

from .. import config
from ..ui import Prompt, console

BASE = "https://kitsu.io/api"
JSONAPI = {"Accept": "application/vnd.api+json", "Content-Type": "application/vnd.api+json"}


class Kitsu:
    name = "kitsu"

    def __init__(self, cfg):
        self.cfg = cfg

    @staticmethod
    def _pack(d):
        return {"access": d["access_token"], "refresh": d["refresh_token"],
                "expires_at": time.time() + d["expires_in"]}

    def _hdr(self):
        a = self.cfg["auth"]["kitsu"]
        if time.time() > a["expires_at"] - 120:
            r = requests.post(f"{BASE}/oauth/token", timeout=20, data={
                "grant_type": "refresh_token", "refresh_token": a["refresh"]})
            r.raise_for_status()
            a.update(self._pack(r.json()))
            config.save(self.cfg)
        return {**JSONAPI, "Authorization": f"Bearer {a['access']}"}

    @staticmethod
    def login(cfg):
        console.print("Kitsu login (password is only used once to get a token, it is not stored)")
        user = Prompt.ask("Email or username").strip()
        pw = Prompt.ask("Password", password=True)
        r = requests.post(f"{BASE}/oauth/token", timeout=20,
                          data={"grant_type": "password", "username": user, "password": pw})
        if r.status_code >= 400:
            raise RuntimeError("Kitsu login failed (check credentials)")
        auth = Kitsu._pack(r.json())
        me = requests.get(f"{BASE}/edge/users", params={"filter[self]": "true"}, timeout=20,
                          headers={**JSONAPI, "Authorization": f"Bearer {auth['access']}"}).json()
        auth["user_id"] = me["data"][0]["id"]
        return auth

    def _get(self, path, **params):
        r = requests.get(f"{BASE}/edge{path}", params=params, headers=self._hdr(), timeout=20)
        r.raise_for_status()
        return r.json()

    def whoami(self):
        return self._get("/users", **{"filter[self]": "true"})["data"][0]["attributes"]["name"]

    def search(self, title):
        d = self._get("/anime", **{"filter[text]": title, "page[limit]": 6})
        out = []
        for x in d.get("data", []):
            a = x["attributes"]
            titles = [a.get("canonicalTitle")] + list((a.get("titles") or {}).values())
            out.append({"id": x["id"], "total": a.get("episodeCount"),
                        "titles": [t for t in titles if t]})
        return out

    def entry(self, mid):
        uid = self.cfg["auth"]["kitsu"]["user_id"]
        d = self._get("/library-entries", **{"filter[userId]": uid, "filter[animeId]": mid})
        if d["data"]:
            e = d["data"][0]
            return {"progress": e["attributes"].get("progress") or 0, "entry_id": e["id"]}
        return {"progress": 0}

    def update(self, mid, ep, total, entry):
        status = "completed" if total and ep >= total else "current"
        attrs = {"progress": ep, "status": status}
        if entry.get("entry_id"):
            eid = entry["entry_id"]
            body = {"data": {"id": eid, "type": "libraryEntries", "attributes": attrs}}
            r = requests.patch(f"{BASE}/edge/library-entries/{eid}", json=body,
                               headers=self._hdr(), timeout=20)
        else:
            uid = self.cfg["auth"]["kitsu"]["user_id"]
            body = {"data": {"type": "libraryEntries", "attributes": attrs, "relationships": {
                "user": {"data": {"type": "users", "id": uid}},
                "media": {"data": {"type": "anime", "id": str(mid)}}}}}
            r = requests.post(f"{BASE}/edge/library-entries", json=body,
                              headers=self._hdr(), timeout=20)
        r.raise_for_status()
        return {"progress": ep, "entry_id": r.json()["data"]["id"]}
