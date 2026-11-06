#!/bin/bash
# Prepares the tarball used to link and run mksnapshot on IBM i: objects + archives from
# mksnapshot.entrees, and mksnapshot.args = exact arguments of the ninja action
# run_mksnapshot_default (taken from ninja.log, after "./mksnapshot").
set -e
cd ~/v8aix/rusty_v8/out/aix
LOG=${1:-$HOME/v8aix/ninja.log}
grep -A1 "^FAILED: .*gen/v8/snapshot.cc" "$LOG" | grep "run.py ./mksnapshot" | head -1 \
  | sed 's/.*run.py \.\/mksnapshot //' > mksnapshot.args
[ -s mksnapshot.args ] || { echo "arguments de mksnapshot introuvables dans $LOG" >&2; exit 1; }
cat mksnapshot.args
tar czf ~/v8aix/transfert/mks.tar.gz mksnapshot.entrees mksnapshot.lien mksnapshot.args \
  $(tr " " "\n" < mksnapshot.entrees | grep -E "\.(o|a)$")
ls -l ~/v8aix/transfert/mks.tar.gz
