#!/usr/bin/env bash

set -euo pipefail

sudo apt-get update
sudo apt-get install --yes \
  libdbus-1-3 \
  libegl1 \
  libgl1 \
  libxkbcommon-x11-0 \
  libxcb-cursor0 \
  libxcb-xinerama0
