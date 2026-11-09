#!/bin/bash
# Fetches rusty_v8 v150.4.0 (V8 15.0.245.2) sources and submodules, shallow clone
set -x
cd ~/v8aix
[ -d rusty_v8 ] || git clone --depth 1 --branch v150.4.0 https://github.com/denoland/rusty_v8.git
cd rusty_v8
git submodule update --init --recursive --depth 1 --jobs 28
du -sh . ; git submodule status | head -40
echo DONE
