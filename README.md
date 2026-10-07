# techno-cli

Watch anime from your terminal. Like [ani-cli](https://github.com/pystardust/ani-cli), but with multiple providers, automatic fallback, tracker sync and Discord presence.

Works on Arch Linux, Debian, Ubuntu and macOS.

## Features

- **Multiple providers**: animepahe (default), hianime, allanime (experimental)
- **Automatic fallback**: if a provider fails, the others are tried before you see an error
- **Tracker sync**: AniList, MyAnimeList and Kitsu update after every episode
- **Continue watching**: offers to resume from your last watched episode
- **Discord Rich Presence**: show what you are watching
- **Pretty terminal**: panels, spinners and fzf menus
- **Sub or dub**, quality selection, subtitles when the provider has them
- **Self-diagnosing**: `techno-cli --doctor` tests every provider
- **Self-updating**: `techno-cli --upgrade`

## Install

```
git clone https://github.com/7yxz/techno-cli
cd techno-cli
bash install.sh
```

The script installs python, pipx, mpv and fzf with pacman, apt or brew, then installs techno-cli with pipx. Check it with `techno-cli -v`.

Manual install: `pipx install .` (needs mpv, fzf is optional).

## Usage

```
techno-cli naruto
techno-cli -p hianime one piece
techno-cli -a -q 720 frieren
techno-cli -e 5 -d bleach
techno-cli -help
```

Controls after each episode: `n` next (default, just press Enter), `p` previous, `r` replay, `s` select episode, `q` quit.

| Flag | Meaning |
|------|---------|
| `-p, --provider` | animepahe (default), hianime, allanime, aniwatch |
| `-a, --all` | search animepahe and hianime together |
| `-d, --dub` | dubbed audio |
| `-q, --quality` | preferred quality, default 1080 |
| `-e, --episode` | start at this episode number |
| `--login / --logout TRACKER` | anilist, mal or kitsu |
| `--status` | show tracker login status |
| `--no-sync` | skip tracker updates for this run |
| `--remap` | re-pick the tracker match for this anime |
| `--rpc-setup` / `--no-rpc` | set up or disable Discord presence |
| `--doctor` | test every provider |
| `--upgrade` | update to the latest version |
| `-v, --version` | show version |

## Providers

| Provider | Notes |
|----------|-------|
| animepahe | Default. Finds a working mirror and handles cookies by itself. Often behind Cloudflare, so it may fail. |
| hianime | Direct scraping, no server needed. Uses `curl_cffi` to look like Chrome. |
| allanime | Experimental, use with `-p allanime`. Uses rotating keys published by anipy-cli. |
| aniwatch | Optional. Needs a self-hosted [aniwatch-api](https://github.com/ghoshRitesh12/aniwatch-api), set `HIANIME_API`. |

If the provider you choose fails, techno-cli tries the others and only shows an error when all of them fail. Working mirrors are remembered in the config.

## Tracker sync

Log in once, then progress updates automatically after you watch 80% of an episode (change it with `TECHNO_SYNC_PCT`).

```
techno-cli --login anilist
techno-cli --login mal
techno-cli --login kitsu
techno-cli --status
```

| Tracker | What you need |
|---------|---------------|
| AniList | An app from anilist.co/settings/developer with redirect `https://anilist.co/api/v2/oauth/pin`. Paste the token it shows, or use `--token`. |
| MAL | An app from myanimelist.net/apiconfig, type other, redirect `http://localhost:8765/callback`. Login opens your browser. |
| Kitsu | Email and password, only used once to get a token. |

Progress only moves forward, and the last episode marks the entry completed. Percent tracking needs mpv. Tokens are stored in `~/.config/techno-cli/config.json` (chmod 600).

## Discord Rich Presence

```
techno-cli --rpc-setup
```

Paste a Discord application ID from discord.com/developers/applications. While you watch, Discord shows the anime, episode and provider. The Discord desktop app must be running. For a logo, upload an image named `techno-cli` under Rich Presence, then Art Assets.

## Upgrade and uninstall

```
techno-cli --upgrade      # latest version from GitHub
pipx uninstall techno-cli # remove
rm -rf ~/.config/techno-cli  # remove saved logins and settings
```

## Troubleshooting

- **Everything fails**: run `techno-cli --doctor` and look at which step breaks for each provider.
- **Cloudflare blocks**: make sure `curl_cffi` is installed (`pipx inject techno-cli curl_cffi`). Providers change often, so a different one may work better today.
- **Old version after updating**: run `which -a techno-cli` and delete any copy that is not the pipx one.
- **`./install.sh` not executable**: run it with `bash install.sh`.
- **Wrong tracker match**: run again with `--remap`.

## Environment variables

All optional: `PAHE_URL`, `PAHE_COOKIE`, `HIANIME_URL`, `HIANIME_API`, `TECHNO_PLAYER` (default mpv), `TECHNO_SYNC_PCT`, `DISCORD_CLIENT_ID`, `TECHNO_NO_UPDATE_CHECK`.

## Adding a provider

Create a class in `techno_cli/providers/` with these methods, then register it in `providers/__init__.py`:

```python
class MySite:
    name = "mysite"
    in_all = True
    def search(self, q): ...                          # -> [(title, id)]
    def episodes(self, id): ...                       # -> [("Episode 1", ep_id)]
    def stream(self, id, ep_id, quality, dub=False):  # -> (url, headers, subtitle_or_None)
        ...
```

## Credits and license

hianime logic is ported from [ani-cli](https://github.com/pystardust/ani-cli) and allanime logic from [anipy-cli](https://github.com/sdaqo/anipy-cli). Both are GPL-3.0, so techno-cli is GPL-3.0 too (see `LICENSE`).

## Disclaimer

techno-cli does not host or store any video. It only fetches links from third-party sites. You are responsible for how you use it and for following the laws where you live. Please support the official releases.
