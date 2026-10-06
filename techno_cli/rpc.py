"""Discord Rich Presence. Needs your own Discord application id (see --rpc-setup)."""
import os
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

    def update(self, title, label, provider):
        if not self._connect():
            return
        try:
            self.rpc.update(
                details=title[:128], state=f"{label} on {provider}"[:128], start=int(time.time()),
                large_image=os.environ.get("TECHNO_RPC_IMAGE", "techno-cli"), large_text="techno-cli",
                buttons=[{"label": "Get techno-cli", "url": REPO}])
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
