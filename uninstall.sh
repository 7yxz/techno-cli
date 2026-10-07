#!/usr/bin/env bash
# remove command aliases made from --config
for a in tcli t-cli; do
  p="$(command -v "$a" 2>/dev/null)"
  [ -L "$p" ] && rm -f "$p"
done
pipx uninstall techno-cli
