#!/bin/bash
cd ~/v8aix/rusty_v8
export PATH=~/v8aix/bin:~/v8aix/outils/gn:~/v8aix/outils/ninja:$PATH
date
ninja -C out/aix -k 0 -j 28 rusty_v8 > ~/v8aix/ninja.log 2>&1
echo "ninja rc=$?"; date
grep -c "^FAILED" ~/v8aix/ninja.log
