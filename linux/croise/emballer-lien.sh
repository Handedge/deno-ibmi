#!/bin/bash
# Packages everything referenced by the link command recorded by lien-rust.sh:
# objects and archives (absolute LINUXBUILD paths), the saved rustc temporary files,
# and the command itself. Gzip output on stdout (streamed to IBM i through the PC).
# Usage: emballer-lien.sh <file.lien>
set -e
L=$1
D=$(dirname "$L")
liste=$(mktemp)
{
  echo "$L"
  echo "$L.d"
  grep -vE '^-' "$L" | grep -v '@GARDE@' | while read -r f; do [ -e "$f" ] && echo "$f"; done
  # -L directories (C libraries of the crates): archives only
  awk 'p=="-L"{print} {p=$0}' "$L" | while read -r d; do
    [ -d "$d" ] && find "$d" -maxdepth 1 -name '*.a'
  done
} | grep -v '^/usr/lib' | grep -v '^/QOpenSys/opt/rust' | sort -u > "$liste"
tar cf - -P -T "$liste" | gzip -1
rm -f "$liste"
