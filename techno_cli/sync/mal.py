import os
import secrets
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests

from .. import config
from ..ui import Prompt, console

AUTH = "https://myanimelist.net/v1/oauth2/authorize"
TOKEN = "https://myanimelist.net/v1/oauth2/token"
API = "https://api.myanimelist.net/v2"
PORT = 8765
REDIRECT = f"http://localhost:{PORT}/callback"


def _wait_for_code(url, state):
    got = {}

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            q = parse_qs(urlparse(self.path).query)
            got["code"] = (q.get("code") or [None])[0]
            got["state"] = (q.get("state") or [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"techno-cli: logged in, you can close this tab.")

        def log_message(self, *a):
            pass

    try:
        srv = HTTPServer(("localhost", PORT), H)
        srv.timeout = 180
        t = threading.Thread(target=srv.handle_request, daemon=True)
        t.start()
        webbrowser.open(url)
        console.print(f"Waiting for browser login (open this if it didn't pop up):\n[cyan]{url}[/]")
        t.join(180)
        srv.server_close()
    except OSError:
        pass
    if not got.get("code"):  # headless / port busy: paste the redirected URL
        pasted = Prompt.ask("Paste the full URL you were redirected to")
        q = parse_qs(urlparse(pasted).query)
        got["code"] = (q.get("code") or [None])[0]
        got["state"] = (q.get("state") or [None])[0]
    if got.get("state") != state or not got.get("code"):
        raise RuntimeError("MAL login failed (state mismatch or no code)")
    return got["code"]


class MAL:
    name = "mal"

    def __init__(self, cfg):
        self.cfg = cfg

    def _client(self):
        d = {"client_id": os.environ.get("MAL_CLIENT_ID") or self.cfg.get("mal_client_id")}
        if os.environ.get("MAL_CLIENT_SECRET"):
            d["client_secret"] = os.environ["MAL_CLIENT_SECRET"]
        return d

    @staticmethod
    def _pack(d):
        return {"access": d["access_token"], "refresh": d["refresh_token"],
                "expires_at": time.time() + d["expires_in"]}

    def _hdr(self):
        a = self.cfg["auth"]["mal"]
        if time.time() > a["expires_at"] - 120:
            r = requests.post(TOKEN, data={**self._client(), "grant_type": "refresh_token",
                                           "refresh_token": a["refresh"]}, timeout=20)
            r.raise_for_status()
            a.update(self._pack(r.json()))
            config.save(self.cfg)
        return {"Authorization": f"Bearer {a['access']}"}

    @staticmethod
    def login(cfg):
        cid = os.environ.get("MAL_CLIENT_ID") or cfg.get("mal_client_id")
        if not cid:
            console.print("Create an app at [cyan]https://myanimelist.net/apiconfig[/]\n"
                          f"App type: other. Redirect URL: [cyan]{REDIRECT}[/]")
            cid = Prompt.ask("Client ID").strip()
        cfg["mal_client_id"] = cid
        verifier, state = secrets.token_urlsafe(64), secrets.token_urlsafe(8)
        url = AUTH + "?" + urlencode({
            "response_type": "code", "client_id": cid, "code_challenge": verifier,
            "code_challenge_method": "plain", "state": state, "redirect_uri": REDIRECT})
        code = _wait_for_code(url, state)
        data = {"client_id": cid, "grant_type": "authorization_code", "code": code,
                "code_verifier": verifier, "redirect_uri": REDIRECT}
        if os.environ.get("MAL_CLIENT_SECRET"):
            data["client_secret"] = os.environ["MAL_CLIENT_SECRET"]
        r = requests.post(TOKEN, data=data, timeout=20)
        r.raise_for_status()
        return MAL._pack(r.json())

    def _get(self, path, **params):
        r = requests.get(API + path, params=params, headers=self._hdr(), timeout=20)
        r.raise_for_status()
        return r.json()

    def whoami(self):
        return self._get("/users/@me")["name"]

    def search(self, title):
        d = self._get("/anime", q=title[:64], limit=6, fields="num_episodes,alternative_titles")
        out = []
        for x in d.get("data", []):
            n = x["node"]
            alt = n.get("alternative_titles") or {}
            titles = [n["title"], alt.get("en")] + (alt.get("synonyms") or [])
            out.append({"id": n["id"], "total": n.get("num_episodes") or None,
                        "titles": [t for t in titles if t]})
        return out

    def entry(self, mid):
        d = self._get(f"/anime/{mid}", fields="my_list_status")
        return {"progress": (d.get("my_list_status") or {}).get("num_episodes_watched") or 0}

    def update(self, mid, ep, total, entry):
        status = "completed" if total and ep >= total else "watching"
        r = requests.put(f"{API}/anime/{mid}/my_list_status", headers=self._hdr(), timeout=20,
                         data={"num_watched_episodes": ep, "status": status})
        r.raise_for_status()
        return {"progress": ep}
