#!/bin/bash
# Stands in for running an AIX tool (mksnapshot) under ninja: copies the files it
# produced on IBM i (brought back into ~/v8aix/sorties-ibmi/, tree relative to
# out/aix) to the paths requested by the --*_src / --*-src options.
S="$HOME/v8aix/sorties-ibmi"
rc=0; prev=""
for a in "$@"; do
  case "$prev" in
    --embedded_src|--startup_src|--builtins-effects-src)
      if [ -f "$S/$a" ]; then
        mkdir -p "$(dirname "$a")"; cp "$S/$a" "$a"; echo "replay-ibmi: $a (produced on IBM i)"
      else
        echo "replay-ibmi: $S/$a missing (run the tool on IBM i)" >&2; rc=1
      fi;;
  esac
  prev="$a"
done
exit $rc
