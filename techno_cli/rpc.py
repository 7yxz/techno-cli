"""Discord Rich Presence. Needs your own Discord application id (see --rpc-setup)."""
import os
import re
import time

REPO = "https://github.com/7yxz/techno-cli"


class Presence:
    def __init__(self, client_id):
        self.client_id, self.rpc = client_id, None

    def _connect(self):
        if self.rpc:
            return True
        try:
            from pypresence import Presence as P
            self.rpc = P(self.client_id)
            self.rpc.connect()
            return True
        except Exception:  # discord not running, retried on next update
            self.rpc = None
            return False

    def update(self, title, label, provider, info=None):
        if not self._connect():
            return
        info = info or {}
        m = re.search(r"(\d+)(?:\.\d+)?$", label)
        total = info.get("episodes")
        state = (f"Episode {m.group(1)}" + (f" of {total}" if total else "")) if m else label
        asset = os.environ.get("TECHNO_RPC_IMAGE", "techno-cli")
        bits = ([f"{info['score'] / 10:.1f}/10"] if info.get("score") else []) + (info.get("genres") or [])[:3]
        buttons = ([{"label": "View on AniList", "url": info["url"]}] if info.get("url") else [])
        buttons.append({"label": "Get techno-cli", "url": REPO})
        now = int(time.time())
        kw = dict(details=(info.get("title") or title)[:128], state=state[:128], start=now,
                  large_image=info.get("cover") or asset, large_text=(" | ".join(bits) or "techno-cli")[:128],
                  small_image=asset, small_text=f"via {provider}", buttons=buttons)
        if info.get("duration"):
            kw["end"] = now + int(info["duration"]) * 60  # shows time left
        try:
            from pypresence import ActivityType
            kw["activity_type"] = ActivityType.WATCHING
        except Exception:
            pass
        try:
            self.rpc.update(**kw)
        except Exception:
            self.rpc = None

    def clear(self):
        try:
            self.rpc and self.rpc.clear()
        except Exception:
            self.rpc = None

    def close(self):
        try:
            self.rpc and self.rpc.close()
        except Exception:
            pass


def get(cfg):
    cid = os.environ.get("DISCORD_CLIENT_ID") or cfg.get("discord_client_id")
    return Presence(cid) if cid else None
