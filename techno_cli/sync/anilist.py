import os
import re

import requests

from ..ui import Prompt, console

API = "https://graphql.anilist.co"


class AniList:
    name = "anilist"

    def __init__(self, cfg):
        self.cfg = cfg

    @property
    def token(self):
        return self.cfg["auth"]["anilist"]["token"]

    def _q(self, query, **variables):
        r = requests.post(API, json={"query": query, "variables": variables},
                          headers={"Authorization": f"Bearer {self.token}"}, timeout=20)
        d = r.json()
        if d.get("errors"):
            raise RuntimeError(d["errors"][0].get("message", "anilist error"))
        return d["data"]

    @staticmethod
    def login(cfg):
        cid = os.environ.get("ANILIST_CLIENT_ID") or cfg.get("anilist_client_id")
        if not cid:
            console.print("Create an app at [cyan]https://anilist.co/settings/developer[/]\n"
                          "Redirect URL: [cyan]https://anilist.co/api/v2/oauth/pin[/]")
            cid = Prompt.ask("Client ID").strip()
        cfg["anilist_client_id"] = cid
        console.print("\nOpen this URL, approve, and copy the token shown:\n"
                      f"[cyan]https://anilist.co/api/v2/oauth/authorize?client_id={cid}&response_type=token[/]\n")
        raw = os.environ.get("TECHNO_TOKEN") or Prompt.ask("Token (visible so pasting works)")
        m = re.search(r"access_token=([^&\s]+)", raw)  # also accepts the full redirect URL
        return {"token": (m.group(1) if m else raw).strip().strip("\"'")}

    def whoami(self):
        return self._q("query { Viewer { name } }")["Viewer"]["name"]

    def search(self, title):
        d = self._q("""query($s:String){Page(perPage:6){media(search:$s,type:ANIME){
            id episodes title{romaji english}}}}""", s=title)
        return [{"id": m["id"], "total": m["episodes"],
                 "titles": [t for t in (m["title"]["romaji"], m["title"]["english"]) if t]}
                for m in d["Page"]["media"]]

    def entry(self, mid):
        d = self._q("query($id:Int){Media(id:$id){mediaListEntry{progress status}}}", id=mid)
        e = d["Media"]["mediaListEntry"] or {}
        return {"progress": e.get("progress") or 0}

    def update(self, mid, ep, total, entry):
        status = "COMPLETED" if total and ep >= total else "CURRENT"
        self._q("""mutation($id:Int,$p:Int,$s:MediaListStatus){
            SaveMediaListEntry(mediaId:$id,progress:$p,status:$s){id}}""", id=mid, p=ep, s=status)
        return {"progress": ep}
