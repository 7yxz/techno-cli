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
| -p, --provider | animepahe (default) or hianime |
| -a, --all | search all providers |
| -q, --quality | preferred quality, default 1080 |
| -e, --episode | start at episode number |

Playback controls: n next, p previous, r replay, s select episode, q quit.

## Providers

- animepahe: works directly. If blocked, set `PAHE_COOKIE` to a cookie from your browser.
- hianime: needs a self-hosted [aniwatch-api](https://github.com/ghoshRitesh12/aniwatch-api). Set `HIANIME_API` (default http://localhost:4000).

Add a provider: create a class in `techno_cli/providers/` with `search`, `episodes`, `stream`, then register it in `providers/__init__.py`.

## Env

- `HIANIME_API`, `PAHE_COOKIE`, `TECHNO_PLAYER` (default mpv)

## Uninstall

    ./uninstall.sh
