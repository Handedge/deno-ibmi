#!/bin/bash
# Generates the rusty_v8 Rust bindings (src_binding.rs) for powerpc64-ibm-aix, with the
# same bindgen settings as build_binding() in rusty_v8/build.rs, but targeting
# AIX (PASE headers, __PASE__, standard #pragma pack semantics).
# Requirements: libclang 19+ (/usr/lib/llvm-19), bindgen-cli 0.72 (rusty_v8 version).
set -e
R=~/v8aix/rusty_v8
SORTIE=${1:-$HOME/v8aix/src_binding_aix.rs}
export PATH=~/v8aix/bin:~/v8aix/outils/gn:~/v8aix/outils/ninja:~/.cargo/bin:$PATH
export LIBCLANG_PATH=/usr/lib/llvm-19/lib
cd $R
gn gen out/aix --ide=json > /dev/null          # project.json for get_bindgen_args.py
DEFINES=$(python3 tools/get_bindgen_args.py --gn-out out/aix | tr '\0' '\n')
mapfile -t DEFS <<< "$DEFINES"
bindgen src/binding.hpp -o "$SORTIE" \
  --generate-cstr \
  --rustified-enum '.*UseCounterFeature' --rustified-enum '.*ModuleImportPhase' \
  --rustified-enum '.*Intercepted' \
  --bitfield-enum '.*GCType' --bitfield-enum '.*GCCallbackFlags' \
  --allowlist-item 'v8__.*' --allowlist-item 'cppgc__.*' --allowlist-item 'RustObj' \
  --allowlist-item 'memory_span_t' --allowlist-item 'const_memory_span_t' \
  --allowlist-item 'ExternalConstOneByteStringResource' \
  --blocklist-item 'cppgc.*Visitor' --blocklist-item 'RustObj.*Trace' \
  -- \
  -x c++ -std=c++20 -nostdinc++ -Iv8/include -I. \
  -isystembuildtools/third_party/libc++ \
  -isystemthird_party/libc++/src/include \
  -isystemthird_party/libc++abi/src/include \
  -resource-dir $HOME/v8aix/clang/lib/clang/23 \
  --target=powerpc64-ibm-aix7.2 --sysroot=$HOME/v8aix/sysroot \
  -fno-xl-pragma-pack -D__PASE__ -D__COMPATMATH__ -D_ALL_SOURCE=1 -D_THREAD_SAFE \
  "${DEFS[@]}"
wc -l "$SORTIE"
grep -c "pub fn v8__" "$SORTIE"
