# techno-cli

ani-cli style anime player for the terminal, with multiple providers.

Supported: Arch Linux, Debian, Ubuntu, macOS.

## Install

    git clone https://github.com/7yxz/techno-cli
    cd techno-cli
    ./install.sh

The script installs python, pipx, mpv and fzf with pacman, apt or brew, then installs techno-cli with pipx.
Manual install: `pipx install .` (needs mpv, fzf optional).

## Usage

    techno-cli naruto
    techno-cli -p hianime one piece
    techno-cli -a -q 720 frieren
    techno-cli -e 5 bleach
    techno-cli -help

| Flag | Meaning |
|------|---------|
| -p, --provider | animepahe (default), hianime, aniwatch |
| -a, --all | search animepahe + hianime together |
| -d, --dub | dubbed audio |
| -q, --quality | preferred quality, default 1080 |
| -e, --episode | start at episode number |
| --login / --logout TRACKER | anilist, mal or kitsu |
| --status | show tracker login status |
| --doctor | test every provider and show what works |
| --no-sync | skip tracker updates this run |
| --remap | re-pick the tracker match for this anime |

Playback controls: n next, p previous, r replay, s select episode, q quit.

## Tracker sync (AniList, MAL, Kitsu)

Log in once, then progress updates automatically after each episode (once you have watched 80%, change with `TECHNO_SYNC_PCT`). Starting an anime offers to continue from your last watched episode.

    techno-cli --login anilist   # needs an app: anilist.co/settings/developer, redirect https://anilist.co/api/v2/oauth/pin
    techno-cli --login mal       # needs an app: myanimelist.net/apiconfig, type other, redirect http://localhost:8765/callback
    techno-cli --login kitsu     # email + password, only used once to get a token
    techno-cli --status

Tokens live in `~/.config/techno-cli/config.json` (chmod 600). Progress only moves forward, and the last episode marks the entry completed. Percent tracking needs mpv; other players sync when they exit.

## Discord Rich Presence

    techno-cli --rpc-setup    # paste your Discord application id once

While playing, Discord shows the anime, episode and provider with a button to this repo. Needs the Discord desktop app running. `--no-rpc` turns it off for a run.

## Providers

- animepahe: finds a working mirror and handles the DDoS-Guard cookie by itself.
- hianime: scrapes directly (logic ported from ani-cli), no server needed. Uses curl_cffi to look like Chrome so Cloudflare lets it through.
- allanime: experimental (`-p allanime`). Ported from anipy-cli; its API uses rotating keys that anipy-cli publishes, so it may break now and then.
- aniwatch: optional, uses a self-hosted [aniwatch-api](https://github.com/ghoshRitesh12/aniwatch-api) via `HIANIME_API`.

Add a provider: create a class in `techno_cli/providers/` with `search`, `episodes`, `stream` (returns `url, headers, subtitle_or_None`), then register it in `providers/__init__.py`.

## Env (all optional)

`PAHE_URL`, `PAHE_COOKIE`, `HIANIME_URL`, `HIANIME_API`, `TECHNO_PLAYER` (default mpv)

## Uninstall

    ./uninstall.sh

## Credits and license

hianime logic is ported from [ani-cli](https://github.com/pystardust/ani-cli) and allanime logic from [anipy-cli](https://github.com/sdaqo/anipy-cli), both GPL-3.0, so techno-cli is released under GPL-3.0 too (see LICENSE).
