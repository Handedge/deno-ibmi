# Third-party licenses of the deno 2.9.8 package for IBM i

The deno-ibmi scripts, patches and libpaseat are under the MIT license (`LICENSE`). The deno binary
and the libraries of this package contain the following third-party components, each under its own
license. Their sources are available from the links below and from crates.io.

## Native components

| Component | Project | License | Notes |
|---|---|---|---|
| Deno | https://github.com/denoland/deno | MIT | the runtime itself (Rust and JavaScript sources) |
| V8 15.0.245.2 | https://v8.dev | BSD-3-Clause | JavaScript engine, through rusty_v8 150.4.0 |
| Chromium libc++ / libc++abi | https://libcxx.llvm.org | Apache-2.0 WITH LLVM-exception | C++ library built with V8 |
| ICU data (big-endian) | https://icu.unicode.org | Unicode-3.0 | Intl data, embedded |
| simdutf | https://github.com/simdutf/simdutf | Apache-2.0 OR MIT | built with rusty_v8 |
| AWS-LC | https://github.com/aws/aws-lc | ISC AND (Apache-2.0 OR ISC) | cryptography (crate aws-lc-sys) |
| zlib-ng | https://github.com/zlib-ng/zlib-ng | Zlib | compression (crate libz-sys) |
| libffi | https://github.com/libffi/libffi | MIT | FFI (crate libffi-sys) |
| SQLite | https://sqlite.org | blessing (public domain) | crate libsqlite3-sys |
| nghttp2 | https://github.com/nghttp2/nghttp2 | MIT | HTTP/2 (crate libnghttp2) |
| libuv | https://github.com/libuv/libuv | MIT | crate libuv-sys-lite |
| libpaseat | https://github.com/Handedge/deno-ibmi | MIT | /QOpenSys/pkgs/lib/deno/libpaseat.a, *at() functions for PASE (this project) |
| IBM XL C/C++ for AIX 17.1.3 Runtime Environment: libunwind | https://www.ibm.com/products/open-xl-cpp-aix-compiler-power | IBM License Information (Redistributable) | /QOpenSys/pkgs/lib/deno/libunwind.a, object code, unmodified, notices kept (see below) |

## IBM runtime component

`libunwind.a` comes, unmodified and in object-code form, from the IBM XL C/C++ for AIX 17.1.3
Runtime Environment (programs 5765-J16, 5765-J18, 5725-C72), whose License Information lists
`libunwind.rte` among its Redistributables. It is (C) Copyright IBM Corp. and others; its copyright
notices are kept. It is redistributed only as part of this package, which uses it at run time, and
only to support the use of this package.

IBM, its suppliers and distributors provide this component without obligation of support and "AS IS",
WITH NO WARRANTY OF ANY KIND, EITHER EXPRESS OR IMPLIED, INCLUDING THE WARRANTY OF TITLE,
NON-INFRINGEMENT OR NON-INTERFERENCE AND THE IMPLIED WARRANTIES AND CONDITIONS OF MERCHANTABILITY
AND FITNESS FOR A PARTICULAR PURPOSE. IBM, its suppliers and distributors accept no liability for any
use of this component as part of this package. This package is not affiliated with or endorsed by IBM.

## Rust crates linked into the deno binary (861)

| Crate | Version | License |
|---|---|---|
| Inflector | 0.11.4 | BSD-2-Clause |
| adler | 1.0.2 | 0BSD OR MIT OR Apache-2.0 |
| adler2 | 2.0.0 | 0BSD OR MIT OR Apache-2.0 |
| aead | 0.5.2 | MIT OR Apache-2.0 |
| aead-gcm-stream | 0.4.0 | MIT |
| aes | 0.8.3 | MIT OR Apache-2.0 |
| aes-gcm | 0.10.3 | Apache-2.0 OR MIT |
| aes-kw | 0.2.1 | MIT OR Apache-2.0 |
| ahash | 0.8.11 | MIT OR Apache-2.0 |
| aho-corasick | 1.1.3 | Unlicense OR MIT |
| alloc-no-stdlib | 3.0.0 | BSD-3-Clause |
| alloc-stdlib | 0.3.0 | BSD-3-Clause |
| allocator-api2 | 0.2.21 | MIT OR Apache-2.0 |
| anstream | 0.6.15 | MIT OR Apache-2.0 |
| anstyle | 1.0.8 | MIT OR Apache-2.0 |
| anstyle-parse | 0.2.3 | MIT OR Apache-2.0 |
| anstyle-query | 1.0.2 | MIT OR Apache-2.0 |
| anyhow | 1.0.98 | MIT OR Apache-2.0 |
| ar_archive_writer | 0.5.3 | Apache-2.0 WITH LLVM-exception |
| arbitrary | 1.4.1 | MIT OR Apache-2.0 |
| arc-swap | 1.7.1 | MIT OR Apache-2.0 |
| argon2 | 0.6.0-rc.8 | MIT OR Apache-2.0 |
| arrayvec | 0.7.4 | MIT OR Apache-2.0 |
| ascii | 1.1.0 | Apache-2.0 OR MIT |
| ash | 0.38.0+1.3.281 | MIT OR Apache-2.0 |
| asn1-rs | 0.5.2 | MIT/Apache-2.0 |
| asn1-rs-derive | 0.4.0 | MIT/Apache-2.0 |
| asn1-rs-impl | 0.1.0 | MIT/Apache-2.0 |
| ast_node | 5.0.0 | Apache-2.0 |
| async-compression | 0.4.51 | MIT OR Apache-2.0 |
| async-once-cell | 0.5.4 | MIT OR Apache-2.0 |
| async-stream | 0.3.5 | MIT |
| async-stream-impl | 0.3.5 | MIT |
| async-trait | 0.1.88 | MIT OR Apache-2.0 |
| atomic-waker | 1.1.2 | Apache-2.0 OR MIT |
| auto_impl | 1.2.0 | MIT OR Apache-2.0 |
| autocfg | 1.3.0 | Apache-2.0 OR MIT |
| aws-lc-rs | 1.18.2 | ISC AND (Apache-2.0 OR ISC) |
| aws-lc-sys | 0.46.0 | ISC AND (Apache-2.0 OR ISC) AND Apache-2.0 AND MIT AND BSD-3-Clause AND (Apache-2.0 OR ISC OR MIT) AND (Apache-2.0 OR ISC OR MIT-0) |
| backhand | 0.25.1 | MIT OR Apache-2.0 |
| base16ct | 0.2.0 | Apache-2.0 OR MIT |
| base16ct | 1.0.0 | Apache-2.0 OR MIT |
| base64 | 0.21.7 | MIT OR Apache-2.0 |
| base64 | 0.22.1 | MIT OR Apache-2.0 |
| base64-simd | 0.8.0 | MIT |
| base64ct | 1.8.3 | Apache-2.0 OR MIT |
| better_scoped_tls | 1.0.1 | Apache-2.0 |
| bincode | 1.3.3 | MIT |
| bindgen | 0.70.1 | BSD-3-Clause |
| bindgen | 0.71.1 | BSD-3-Clause |
| bindgen | 0.72.1 | BSD-3-Clause |
| bit-set | 0.8.0 | Apache-2.0 OR MIT |
| bit-set | 0.9.1 | Apache-2.0 OR MIT |
| bit-vec | 0.8.0 | Apache-2.0 OR MIT |
| bit-vec | 0.9.1 | Apache-2.0 OR MIT |
| bitflags | 1.3.2 | MIT/Apache-2.0 |
| bitflags | 2.9.3 | MIT OR Apache-2.0 |
| bitvec | 1.0.1 | MIT |
| blake2 | 0.10.6 | MIT OR Apache-2.0 |
| blake2 | 0.11.0-rc.6 | MIT OR Apache-2.0 |
| block-buffer | 0.10.4 | MIT OR Apache-2.0 |
| block-buffer | 0.12.0 | MIT OR Apache-2.0 |
| block-padding | 0.3.3 | MIT OR Apache-2.0 |
| borrow-or-share | 0.2.4 | MIT-0 |
| boxed_error | 0.2.3 | MIT |
| brotli | 9.1.0 | BSD-3-Clause AND MIT |
| brotli-decompressor | 6.2.0 | BSD-3-Clause/MIT |
| bsdiff | 0.2.1 | BSD-2-Clause |
| bstr | 1.9.1 | MIT OR Apache-2.0 |
| bumpalo | 3.19.0 | MIT OR Apache-2.0 |
| bytemuck | 1.24.0 | Zlib OR Apache-2.0 OR MIT |
| bytemuck_derive | 1.10.2 | Zlib OR Apache-2.0 OR MIT |
| byteorder | 1.5.0 | Unlicense OR MIT |
| byteorder-lite | 0.1.0 | Unlicense OR MIT |
| bytes | 1.11.1 | MIT |
| bytes-str | 0.2.7 | Apache-2.0 |
| bzip2 | 0.6.1 | MIT OR Apache-2.0 |
| cab | 0.6.0 | MIT |
| calendrical_calculations | 0.2.4 | Apache-2.0 |
| capacity_builder | 0.5.0 | MIT |
| capacity_builder_macros | 0.3.0 | MIT |
| caseless | 0.2.1 | MIT |
| castaway | 0.2.3 | MIT |
| cbc | 0.1.2 | MIT OR Apache-2.0 |
| cc | 1.2.56 | MIT OR Apache-2.0 |
| cdivsufsort | 2.0.0 | MIT |
| cexpr | 0.6.0 | Apache-2.0/MIT |
| cfb | 0.14.0 | MIT |
| cfg-if | 1.0.3 | MIT OR Apache-2.0 |
| cfg_aliases | 0.2.1 | MIT |
| chacha20 | 0.10.1 | MIT OR Apache-2.0 |
| chrono | 0.4.42 | MIT OR Apache-2.0 |
| cipher | 0.4.4 | MIT OR Apache-2.0 |
| clang-sys | 1.8.1 | Apache-2.0 |
| cmake | 0.1.57 | MIT OR Apache-2.0 |
| cmov | 0.5.4 | Apache-2.0 OR MIT |
| codespan-reporting | 0.13.1 | Apache-2.0 |
| color-print | 0.3.5 | MIT OR Apache-2.0 |
| color-print-proc-macro | 0.3.5 | MIT OR Apache-2.0 |
| color_quant | 1.1.0 | MIT |
| colorchoice | 1.0.0 | MIT OR Apache-2.0 |
| compact_str | 0.7.1 | MIT |
| compression-codecs | 0.4.46 | MIT OR Apache-2.0 |
| compression-core | 0.4.34 | MIT OR Apache-2.0 |
| comrak | 0.29.0 | BSD-2-Clause |
| console_static_text | 0.8.3 | MIT |
| const-hex | 1.19.1 | MIT OR Apache-2.0 |
| const-oid | 0.10.2 | Apache-2.0 OR MIT |
| const-oid | 0.9.6 | Apache-2.0 OR MIT |
| convert_case | 0.4.0 | MIT |
| cooked-waker | 5.0.0 | MPL-2.0 |
| core_maths | 0.1.1 | MIT |
| countme | 3.0.1 | MIT OR Apache-2.0 |
| cpubits | 0.1.0 | MIT OR Apache-2.0 |
| cpufeatures | 0.2.12 | MIT OR Apache-2.0 |
| cpufeatures | 0.3.0 | MIT OR Apache-2.0 |
| cranelift | 0.117.2 | Apache-2.0 WITH LLVM-exception |
| cranelift-assembler-x64 | 0.117.2 | Apache-2.0 WITH LLVM-exception |
| cranelift-assembler-x64-meta | 0.117.2 | Apache-2.0 WITH LLVM-exception |
| cranelift-bforest | 0.117.2 | Apache-2.0 WITH LLVM-exception |
| cranelift-bitset | 0.117.2 | Apache-2.0 WITH LLVM-exception |
| cranelift-codegen | 0.117.2 | Apache-2.0 WITH LLVM-exception |
| cranelift-codegen-meta | 0.117.2 | Apache-2.0 WITH LLVM-exception |
| cranelift-codegen-shared | 0.117.2 | Apache-2.0 WITH LLVM-exception |
| cranelift-control | 0.117.2 | Apache-2.0 WITH LLVM-exception |
| cranelift-entity | 0.117.2 | Apache-2.0 WITH LLVM-exception |
| cranelift-frontend | 0.117.2 | Apache-2.0 WITH LLVM-exception |
| cranelift-isle | 0.117.2 | Apache-2.0 WITH LLVM-exception |
| cranelift-native | 0.117.2 | Apache-2.0 WITH LLVM-exception |
| crc32fast | 1.4.2 | MIT OR Apache-2.0 |
| critical-section | 1.2.0 | MIT OR Apache-2.0 |
| crossbeam-channel | 0.5.15 | MIT OR Apache-2.0 |
| crossbeam-deque | 0.8.5 | MIT OR Apache-2.0 |
| crossbeam-epoch | 0.9.18 | MIT OR Apache-2.0 |
| crossbeam-utils | 0.8.21 | MIT OR Apache-2.0 |
| crossterm | 0.28.1 | MIT |
| crunchy | 0.2.4 | MIT |
| crypto-bigint | 0.5.5 | Apache-2.0 OR MIT |
| crypto-bigint | 0.7.0-rc.28 | Apache-2.0 OR MIT |
| crypto-common | 0.1.6 | MIT OR Apache-2.0 |
| crypto-common | 0.2.1 | MIT OR Apache-2.0 |
| cssparser | 0.36.0 | MPL-2.0 |
| cssparser-macros | 0.6.1 | MPL-2.0 |
| ctr | 0.9.2 | MIT OR Apache-2.0 |
| ctutils | 0.4.0 | Apache-2.0 OR MIT |
| curve25519-dalek | 4.1.3 | BSD-3-Clause |
| curve25519-dalek-derive | 0.1.1 | MIT/Apache-2.0 |
| darling | 0.20.10 | MIT |
| darling | 0.21.3 | MIT |
| darling_core | 0.20.10 | MIT |
| darling_core | 0.21.3 | MIT |
| darling_macro | 0.20.10 | MIT |
| darling_macro | 0.21.3 | MIT |
| dashmap | 5.5.3 | MIT |
| data-encoding | 2.5.0 | MIT |
| data-url | 0.3.1 | MIT OR Apache-2.0 |
| debugid | 0.8.0 | Apache-2.0 |
| deku | 0.20.3 | MIT OR Apache-2.0 |
| deku_derive | 0.20.3 | MIT OR Apache-2.0 |
| deno-tower-lsp-macros | 0.12.0 | MIT OR Apache-2.0 |
| deno_ast | 0.53.3 | MIT |
| deno_bundle_runtime | 0.47.0 | MIT |
| deno_cache | 0.193.0 | MIT |
| deno_cache_dir | 0.52.0 | MIT |
| deno_canvas | 0.122.0 | MIT |
| deno_cli_parser | 0.10.0 | MIT |
| deno_config | 0.110.0 | MIT |
| deno_core | 0.413.0 | MIT |
| deno_core_icudata | 0.77.0 | MIT |
| deno_cron | 0.140.0 | MIT |
| deno_crypto | 0.274.0 | MIT |
| deno_crypto_provider | 0.54.0 | MIT |
| deno_doc | 0.207.0 | MIT |
| deno_dotenv | 0.29.0 | MIT |
| deno_error | 0.7.1 | MIT |
| deno_error_macro | 0.7.1 | MIT |
| deno_features | 0.57.0 | MIT |
| deno_fetch | 0.284.0 | MIT |
| deno_ffi | 0.247.0 | MIT |
| deno_fs | 0.170.0 | MIT |
| deno_graph | 0.111.1 | MIT |
| deno_http | 0.258.0 | MIT |
| deno_http_h1 | 0.11.0 | MIT |
| deno_image | 0.36.0 | MIT |
| deno_inspector_server | 0.34.0 | MIT |
| deno_io | 0.170.0 | MIT |
| deno_kv | 0.168.0 | MIT |
| deno_lib | 0.78.0 | MIT |
| deno_lint | 0.84.1 | MIT |
| deno_lockfile | 0.62.0 | MIT |
| deno_maybe_sync | 0.47.0 | MIT |
| deno_media_type | 0.4.0 | MIT |
| deno_napi | 0.191.0 | MIT |
| deno_native_certs | 0.3.0 | MIT |
| deno_net | 0.252.0 | MIT |
| deno_node | 0.198.0 | MIT |
| deno_node_crypto | 0.30.0 | MIT |
| deno_node_sqlite | 0.30.0 | MIT |
| deno_npm | 0.72.0 | MIT |
| deno_npm_cache | 0.79.0 | MIT |
| deno_npm_installer | 0.55.0 | MIT |
| deno_npmrc | 0.21.0 | MIT |
| deno_ops | 0.289.0 | MIT |
| deno_os | 0.77.0 | MIT |
| deno_package_json | 0.62.0 | MIT |
| deno_path_util | 0.6.4 | MIT |
| deno_permissions | 0.119.0 | MIT |
| deno_print | 0.8.0 | MIT |
| deno_process | 0.75.0 | MIT |
| deno_resolver | 0.91.0 | MIT |
| deno_runtime | 0.268.0 | MIT |
| deno_semver | 0.10.1 | MIT |
| deno_signals | 0.51.0 | MIT |
| deno_snapshots | 0.75.0 | MIT |
| deno_subprocess_windows | 0.55.0 | MIT |
| deno_task_shell | 0.33.3 | MIT |
| deno_telemetry | 0.82.0 | MIT |
| deno_terminal | 0.2.3 | MIT |
| deno_tls | 0.247.0 | MIT |
| deno_tower_lsp | 0.5.0 | MIT |
| deno_tunnel | 0.8.1 | MIT |
| deno_unsync | 0.4.4 | MIT |
| deno_v8 | 0.5.0 | MIT |
| deno_web | 0.291.0 | MIT |
| deno_webgpu | 0.227.0 | MIT |
| deno_webidl | 0.260.0 | MIT |
| deno_websocket | 0.265.0 | MIT |
| deno_webstorage | 0.255.0 | MIT |
| deno_whoami | 0.1.0 | MIT |
| denokv_proto | 0.14.0 | MIT |
| denokv_remote | 0.14.0 | MIT |
| denokv_sqlite | 0.14.0 | MIT |
| denort_helper | 0.58.0 | MIT |
| der | 0.7.9 | Apache-2.0 OR MIT |
| der | 0.8.0 | Apache-2.0 OR MIT |
| der-parser | 8.2.0 | MIT/Apache-2.0 |
| der_derive | 0.7.3 | Apache-2.0 OR MIT |
| deranged | 0.5.6 | MIT OR Apache-2.0 |
| derive-io | 0.4.1 | MIT OR Apache-2.0 |
| derive-io-macros | 0.4.1 | MIT OR Apache-2.0 |
| derive_builder | 0.20.2 | MIT OR Apache-2.0 |
| derive_builder_core | 0.20.2 | MIT OR Apache-2.0 |
| derive_builder_macro | 0.20.2 | MIT OR Apache-2.0 |
| derive_more | 0.99.17 | MIT |
| des | 0.8.1 | MIT OR Apache-2.0 |
| deunicode | 1.4.3 | BSD-3-Clause |
| diff | 0.1.13 | MIT OR Apache-2.0 |
| digest | 0.10.7 | MIT OR Apache-2.0 |
| digest | 0.11.1 | MIT OR Apache-2.0 |
| diplomat | 0.15.0 | MIT OR Apache-2.0 |
| diplomat-runtime | 0.15.1 | MIT OR Apache-2.0 |
| diplomat_core | 0.15.0 | MIT OR Apache-2.0 |
| displaydoc | 0.2.4 | MIT OR Apache-2.0 |
| dlib | 0.5.3 | MIT |
| dlopen2 | 0.6.1 | MIT |
| dlopen2_derive | 0.4.0 | MIT |
| document-features | 0.2.10 | MIT OR Apache-2.0 |
| dprint-core | 0.67.4 | MIT |
| dprint-core-macros | 0.1.0 | MIT |
| dprint-plugin-json | 0.21.3 | MIT |
| dprint-plugin-jupyter | 0.2.2 | MIT |
| dprint-plugin-markdown | 0.20.0 | MIT |
| dprint-plugin-typescript | 0.96.1 | MIT |
| dprint-swc-ext | 0.26.0 | MIT |
| dsa | 0.6.3 | Apache-2.0 OR MIT |
| dtoa | 1.0.10 | MIT OR Apache-2.0 |
| dtoa-short | 0.3.5 | MPL-2.0 |
| dunce | 1.0.5 | CC0-1.0 OR MIT-0 OR Apache-2.0 |
| ecb | 0.1.2 | MIT |
| ecdsa | 0.16.9 | Apache-2.0 OR MIT |
| ecow | 0.2.3 | MIT OR Apache-2.0 |
| ed25519 | 2.2.3 | Apache-2.0 OR MIT |
| ed25519-dalek | 2.1.1 | BSD-3-Clause |
| ed448 | 0.5.0-rc.5 | Apache-2.0 OR MIT |
| ed448-goldilocks | 0.14.0-pre.10 | Apache-2.0 OR MIT |
| either | 1.10.0 | MIT OR Apache-2.0 |
| elliptic-curve | 0.13.8 | Apache-2.0 OR MIT |
| elliptic-curve | 0.14.0-rc.28 | Apache-2.0 OR MIT |
| encoding_rs | 0.8.35 | (Apache-2.0 OR MIT) AND BSD-3-Clause |
| endian-type | 0.1.2 | MIT |
| entities | 1.0.1 | MIT |
| enum-as-inner | 0.6.0 | MIT/Apache-2.0 |
| enum-display-derive | 0.1.1 | MIT/Apache-2.0 |
| enum-primitive-derive | 0.3.0 | MIT |
| env_filter | 0.1.3 | MIT OR Apache-2.0 |
| env_home | 0.1.0 | MIT OR Apache-2.0 |
| env_logger | 0.11.6 | MIT OR Apache-2.0 |
| equivalent | 1.0.1 | Apache-2.0 OR MIT |
| errno | 0.3.14 | MIT OR Apache-2.0 |
| error_reporter | 1.0.0 | MIT OR Apache-2.0 |
| esbuild_client | 0.7.2 | MIT |
| eszip | 0.138.0 | MIT |
| fallible-iterator | 0.3.0 | MIT/Apache-2.0 |
| fallible-streaming-iterator | 0.1.9 | MIT/Apache-2.0 |
| fastbloom | 0.17.0 | MIT OR Apache-2.0 |
| faster-hex | 0.10.0 | MIT |
| fastrand | 2.3.0 | Apache-2.0 OR MIT |
| fastwebsockets | 0.8.1 | Apache-2.0 |
| fd-lock | 4.0.2 | MIT OR Apache-2.0 |
| fdeflate | 0.3.4 | MIT OR Apache-2.0 |
| ff | 0.13.0 | MIT/Apache-2.0 |
| filetime | 0.2.23 | MIT/Apache-2.0 |
| find-msvc-tools | 0.1.9 | MIT OR Apache-2.0 |
| fips203 | 0.4.3 | MIT OR Apache-2.0 |
| fips205 | 0.4.1 | MIT OR Apache-2.0 |
| flate2 | 1.1.10 | MIT OR Apache-2.0 |
| fluent-uri | 0.4.1 | MIT |
| fnv | 1.0.7 | Apache-2.0 / MIT |
| foldhash | 0.1.4 | Zlib |
| foldhash | 0.2.0 | Zlib |
| foreign-types | 0.5.0 | MIT/Apache-2.0 |
| foreign-types-macros | 0.2.3 | MIT/Apache-2.0 |
| foreign-types-shared | 0.3.1 | MIT/Apache-2.0 |
| form_urlencoded | 1.2.2 | MIT OR Apache-2.0 |
| fqdn | 0.5.2 | MIT |
| from_variant | 3.0.0 | Apache-2.0 |
| fs_extra | 1.3.0 | MIT |
| fslock | 0.2.1 | MIT |
| funty | 2.0.0 | MIT |
| futures | 0.3.31 | MIT OR Apache-2.0 |
| futures-channel | 0.3.31 | MIT OR Apache-2.0 |
| futures-core | 0.3.31 | MIT OR Apache-2.0 |
| futures-executor | 0.3.31 | MIT OR Apache-2.0 |
| futures-io | 0.3.31 | MIT OR Apache-2.0 |
| futures-macro | 0.3.31 | MIT OR Apache-2.0 |
| futures-sink | 0.3.31 | MIT OR Apache-2.0 |
| futures-task | 0.3.31 | MIT OR Apache-2.0 |
| futures-util | 0.3.31 | MIT OR Apache-2.0 |
| generic-array | 0.14.7 | MIT |
| getrandom | 0.2.17 | MIT OR Apache-2.0 |
| getrandom | 0.3.4 | MIT OR Apache-2.0 |
| getrandom | 0.4.1 | MIT OR Apache-2.0 |
| ghash | 0.5.1 | Apache-2.0 OR MIT |
| gif | 0.13.1 | MIT/Apache-2.0 |
| gimli | 0.31.1 | MIT OR Apache-2.0 |
| glob | 0.3.1 | MIT OR Apache-2.0 |
| globset | 0.4.14 | Unlicense OR MIT |
| glow | 0.17.0 | MIT OR Apache-2.0 OR Zlib |
| gpu-allocator | 0.28.0 | MIT OR Apache-2.0 |
| gpu-descriptor | 0.3.2 | MIT OR Apache-2.0 |
| gpu-descriptor-types | 0.2.0 | MIT OR Apache-2.0 |
| group | 0.13.0 | MIT/Apache-2.0 |
| gzip-header | 1.0.0 | MIT/Apache-2.0 |
| h2 | 0.4.19 | MIT |
| half | 2.7.1 | MIT OR Apache-2.0 |
| handlebars | 6.1.0 | MIT |
| hash2curve | 0.14.0-rc.10 | Apache-2.0 OR MIT |
| hash32 | 0.3.1 | MIT OR Apache-2.0 |
| hashbrown | 0.14.5 | MIT OR Apache-2.0 |
| hashbrown | 0.15.5 | MIT OR Apache-2.0 |
| hashbrown | 0.16.1 | MIT OR Apache-2.0 |
| hashbrown | 0.17.1 | MIT OR Apache-2.0 |
| hashlink | 0.12.0 | MIT OR Apache-2.0 |
| hashlink | 0.8.4 | MIT OR Apache-2.0 |
| hdrhistogram | 7.5.4 | MIT/Apache-2.0 |
| heapless | 0.8.0 | MIT OR Apache-2.0 |
| heck | 0.4.1 | MIT OR Apache-2.0 |
| heck | 0.5.0 | MIT OR Apache-2.0 |
| hex | 0.4.3 | MIT OR Apache-2.0 |
| hexf-parse | 0.2.1 | CC0-1.0 |
| hickory-proto | 0.25.2 | MIT OR Apache-2.0 |
| hickory-resolver | 0.25.2 | MIT OR Apache-2.0 |
| hipstr | 0.6.0 | MIT OR Apache-2.0 |
| hkdf | 0.12.4 | MIT OR Apache-2.0 |
| hmac | 0.12.1 | MIT OR Apache-2.0 |
| home | 0.5.9 | MIT OR Apache-2.0 |
| hostname | 0.3.1 | MIT |
| hstr | 3.0.3 | Apache-2.0 |
| html-escape | 0.2.13 | MIT |
| http | 1.4.0 | MIT OR Apache-2.0 |
| http-body | 1.0.0 | MIT |
| http-body-util | 0.1.3 | MIT |
| httparse | 1.10.0 | MIT OR Apache-2.0 |
| httpdate | 1.0.3 | MIT OR Apache-2.0 |
| hybrid-array | 0.4.7 | MIT OR Apache-2.0 |
| hyper | 1.11.1 | MIT |
| hyper-rustls | 0.27.2 | Apache-2.0 OR ISC OR MIT |
| hyper-util | 0.1.21 | MIT |
| icu_calendar | 2.2.1 | Unicode-3.0 |
| icu_calendar_data | 2.2.0 | Unicode-3.0 |
| icu_collections | 1.5.0 | Unicode-3.0 |
| icu_collections | 2.2.0 | Unicode-3.0 |
| icu_locale | 2.2.0 | Unicode-3.0 |
| icu_locale_core | 2.2.0 | Unicode-3.0 |
| icu_locale_data | 2.2.0 | Unicode-3.0 |
| icu_locid | 1.5.0 | Unicode-3.0 |
| icu_locid_transform | 1.5.0 | Unicode-3.0 |
| icu_locid_transform_data | 1.5.0 | Unicode-3.0 |
| icu_normalizer | 1.5.0 | Unicode-3.0 |
| icu_normalizer_data | 1.5.0 | Unicode-3.0 |
| icu_properties | 1.5.1 | Unicode-3.0 |
| icu_properties | 2.2.0 | Unicode-3.0 |
| icu_properties_data | 1.5.0 | Unicode-3.0 |
| icu_properties_data | 2.2.0 | Unicode-3.0 |
| icu_provider | 1.5.0 | Unicode-3.0 |
| icu_provider | 2.2.0 | Unicode-3.0 |
| icu_provider_macros | 1.5.0 | Unicode-3.0 |
| ident_case | 1.0.1 | MIT/Apache-2.0 |
| idna | 1.1.0 | MIT OR Apache-2.0 |
| idna_adapter | 1.2.0 | Apache-2.0 OR MIT |
| if_chain | 1.0.2 | MIT/Apache-2.0 |
| ignore | 0.4.20 | Unlicense OR MIT |
| image | 0.25.4 | MIT OR Apache-2.0 |
| image-webp | 0.2.4 | MIT OR Apache-2.0 |
| imara-diff | 0.2.0 | Apache-2.0 |
| import_map | 0.25.0 | MIT |
| indexmap | 2.12.0 | Apache-2.0 OR MIT |
| inotify | 0.11.1 | ISC |
| inotify-sys | 0.1.5 | ISC |
| inout | 0.1.3 | MIT OR Apache-2.0 |
| inventory | 0.3.21 | MIT OR Apache-2.0 |
| ipnet | 2.9.0 | MIT OR Apache-2.0 |
| is-macro | 0.3.5 | Apache-2.0 |
| is_terminal_polyfill | 1.70.1 | MIT OR Apache-2.0 |
| itertools | 0.10.5 | MIT/Apache-2.0 |
| itertools | 0.14.0 | MIT OR Apache-2.0 |
| itoa | 1.0.15 | MIT OR Apache-2.0 |
| ixdtf | 0.6.4 | Unicode-3.0 |
| jobserver | 0.1.35 | MIT OR Apache-2.0 |
| jsonc-parser | 0.32.1 | MIT |
| k256 | 0.13.3 | Apache-2.0 OR MIT |
| keccak | 0.1.6 | Apache-2.0 OR MIT |
| keccak | 0.2.0-rc.2 | Apache-2.0 OR MIT |
| keyring | 3.6.3 | MIT OR Apache-2.0 |
| khronos-egl | 6.0.0 | MIT/Apache-2.0 |
| lax-core | 0.3.0 | MIT |
| lax-css | 0.3.0 | MIT |
| lax-markup | 0.3.2 | MIT |
| lax-sql | 0.3.0 | MIT |
| lazy-regex | 3.1.0 | MIT |
| lazy-regex-proc_macros | 3.1.0 | MIT |
| lazy_static | 1.5.0 | MIT OR Apache-2.0 |
| lcms2 | 6.1.0 | MIT |
| lcms2-sys | 4.0.5 | MIT |
| libbz2-rs-sys | 0.2.5 | bzip2-1.0.6 |
| libc | 0.2.186 | MIT OR Apache-2.0 |
| libdeflate-sys | 1.25.2 | Apache-2.0 |
| libdeflater | 1.25.2 | Apache-2.0 |
| libffi | 5.1.0 | MIT/Apache-2.0 |
| libffi-sys | 4.1.0 | MIT/Apache-2.0 |
| libloading | 0.7.4 | ISC |
| libloading | 0.8.5 | ISC |
| liblzma | 0.4.6 | MIT OR Apache-2.0 |
| liblzma-sys | 0.4.6 | MIT OR Apache-2.0 |
| libm | 0.2.8 | MIT OR Apache-2.0 |
| libnghttp2 | 1.68.0 | Apache-2.0 |
| libsqlite3-sys | 0.38.1 | MIT |
| libsui | 0.16.4 | MIT |
| libuv-sys-lite | 1.48.4 | see the crate |
| libz-sys | 1.1.20 | MIT OR Apache-2.0 |
| linux-raw-sys | 0.4.13 | Apache-2.0 WITH LLVM-exception OR Apache-2.0 OR MIT |
| litemap | 0.7.3 | Unicode-3.0 |
| litemap | 0.8.0 | Unicode-3.0 |
| litrs | 0.4.1 | MIT/Apache-2.0 |
| lock_api | 0.4.11 | MIT OR Apache-2.0 |
| locked-tripwire | 0.1.1 | MIT OR Apache-2.0 |
| log | 0.4.32 | MIT OR Apache-2.0 |
| lru-slab | 0.1.2 | MIT OR Apache-2.0 OR Zlib |
| ls-types | 0.0.3 | MIT |
| lzxd | 0.2.6 | MIT OR Apache-2.0 |
| macro_rules_attribute | 0.2.2 | Apache-2.0 OR MIT OR Zlib |
| macro_rules_attribute-proc_macro | 0.2.2 | Apache-2.0 OR MIT OR Zlib |
| match_cfg | 0.1.0 | MIT/Apache-2.0 |
| md-5 | 0.10.6 | MIT OR Apache-2.0 |
| md4 | 0.10.2 | MIT OR Apache-2.0 |
| memchr | 2.8.1 | Unlicense OR MIT |
| memmap2 | 0.9.5 | MIT OR Apache-2.0 |
| memoffset | 0.9.1 | MIT |
| mime | 0.3.17 | MIT OR Apache-2.0 |
| minimal-lexical | 0.2.1 | MIT/Apache-2.0 |
| miniz_oxide | 0.7.2 | MIT OR Zlib OR Apache-2.0 |
| miniz_oxide | 0.8.8 | MIT OR Zlib OR Apache-2.0 |
| miniz_oxide | 0.9.0 | MIT OR Zlib OR Apache-2.0 |
| mio | 1.2.4 | MIT |
| moka | 0.12.10 | MIT OR Apache-2.0 |
| monch | 0.6.0 | MIT |
| msi | 0.10.0 | MIT |
| naga | 29.0.3 | MIT OR Apache-2.0 |
| napi_sym | 0.190.0 | MIT |
| netif | 0.1.6 | ISC |
| new_debug_unreachable | 1.0.6 | MIT |
| nibble_vec | 0.1.0 | MIT |
| nix | 0.29.0 | MIT |
| nix | 0.30.1 | MIT |
| no_std_io2 | 0.9.4 | Apache-2.0 OR MIT |
| node_resolver | 0.98.0 | MIT |
| node_shim | 0.35.0 | MIT |
| nom | 7.1.3 | MIT |
| nom | 8.0.0 | MIT |
| notify | 8.2.0 | CC0-1.0 |
| notify-types | 2.1.0 | MIT OR Apache-2.0 |
| num | 0.4.2 | MIT OR Apache-2.0 |
| num-bigint | 0.4.6 | MIT OR Apache-2.0 |
| num-bigint-dig | 0.8.6 | MIT/Apache-2.0 |
| num-complex | 0.4.6 | MIT OR Apache-2.0 |
| num-conv | 0.2.0 | MIT OR Apache-2.0 |
| num-derive | 0.4.2 | MIT OR Apache-2.0 |
| num-integer | 0.1.46 | MIT OR Apache-2.0 |
| num-iter | 0.1.44 | MIT OR Apache-2.0 |
| num-rational | 0.4.2 | MIT OR Apache-2.0 |
| num-traits | 0.2.19 | MIT OR Apache-2.0 |
| num_cpus | 1.16.0 | MIT OR Apache-2.0 |
| object | 0.36.3 | Apache-2.0 OR MIT |
| object | 0.39.1 | Apache-2.0 OR MIT |
| ocb3 | 0.1.0 | Apache-2.0 OR MIT |
| oid-registry | 0.6.1 | MIT/Apache-2.0 |
| once_cell | 1.21.3 | MIT OR Apache-2.0 |
| opaque-debug | 0.3.1 | MIT OR Apache-2.0 |
| open | 5.1.2 | MIT |
| openssl-probe | 0.1.5 | MIT/Apache-2.0 |
| opentelemetry | 0.32.0 | Apache-2.0 |
| opentelemetry-http | 0.32.0 | Apache-2.0 |
| opentelemetry-otlp | 0.32.0 | Apache-2.0 |
| opentelemetry-proto | 0.32.0 | Apache-2.0 |
| opentelemetry-semantic-conventions | 0.32.1 | Apache-2.0 |
| opentelemetry_sdk | 0.32.1 | Apache-2.0 |
| ordered-float | 4.6.0 | MIT |
| os_pipe | 1.2.1 | MIT |
| outref | 0.5.1 | MIT |
| p12 | 0.6.3 | MIT OR Apache-2.0 |
| p224 | 0.13.2 | Apache-2.0 OR MIT |
| p256 | 0.13.2 | Apache-2.0 OR MIT |
| p384 | 0.13.0 | Apache-2.0 OR MIT |
| p521 | 0.13.3 | Apache-2.0 OR MIT |
| par-core | 2.0.0 | Apache-2.0 |
| parking_lot | 0.12.3 | MIT OR Apache-2.0 |
| parking_lot_core | 0.9.9 | MIT OR Apache-2.0 |
| paste | 1.0.15 | MIT OR Apache-2.0 |
| path-clean | 0.1.0 | MIT OR Apache-2.0 |
| path-dedot | 3.1.1 | MIT |
| pathdiff | 0.2.1 | MIT/Apache-2.0 |
| pbkdf2 | 0.12.2 | MIT OR Apache-2.0 |
| pem-rfc7468 | 0.7.0 | Apache-2.0 OR MIT |
| percent-encoding | 2.3.2 | MIT OR Apache-2.0 |
| pest | 2.7.15 | MIT OR Apache-2.0 |
| pest_derive | 2.7.15 | MIT OR Apache-2.0 |
| pest_generator | 2.7.15 | MIT OR Apache-2.0 |
| pest_meta | 2.7.15 | MIT OR Apache-2.0 |
| phf | 0.11.2 | MIT |
| phf | 0.13.1 | MIT |
| phf_generator | 0.11.2 | MIT |
| phf_generator | 0.13.1 | MIT |
| phf_macros | 0.11.2 | MIT |
| phf_macros | 0.13.1 | MIT |
| phf_shared | 0.11.2 | MIT |
| phf_shared | 0.13.1 | MIT |
| pin-project | 1.1.5 | Apache-2.0 OR MIT |
| pin-project-internal | 1.1.5 | Apache-2.0 OR MIT |
| pin-project-lite | 0.2.14 | Apache-2.0 OR MIT |
| pin-utils | 0.1.0 | MIT OR Apache-2.0 |
| pkcs1 | 0.7.5 | Apache-2.0 OR MIT |
| pkcs5 | 0.7.1 | Apache-2.0 OR MIT |
| pkcs8 | 0.10.2 | Apache-2.0 OR MIT |
| pkcs8 | 0.11.0-rc.11 | Apache-2.0 OR MIT |
| pkg-config | 0.3.34 | MIT OR Apache-2.0 |
| plist | 1.9.0 | MIT |
| png | 0.17.13 | MIT OR Apache-2.0 |
| polyval | 0.6.2 | Apache-2.0 OR MIT |
| portable-atomic | 1.14.0 | Apache-2.0 OR MIT |
| potential_utf | 0.1.3 | Unicode-3.0 |
| powerfmt | 0.2.0 | MIT OR Apache-2.0 |
| ppv-lite86 | 0.2.17 | MIT/Apache-2.0 |
| presser | 0.3.1 | MIT OR Apache-2.0 |
| pretty_assertions | 1.4.1 | MIT OR Apache-2.0 |
| pretty_yaml | 0.5.0 | MIT |
| prettyplease | 0.2.37 | MIT OR Apache-2.0 |
| primeorder | 0.13.6 | Apache-2.0 OR MIT |
| proc-macro-crate | 3.4.0 | MIT OR Apache-2.0 |
| proc-macro2 | 1.0.101 | MIT OR Apache-2.0 |
| profiling | 1.0.15 | MIT OR Apache-2.0 |
| prost | 0.14.4 | Apache-2.0 |
| prost-derive | 0.14.4 | Apache-2.0 |
| psm | 0.1.32 | MIT OR Apache-2.0 |
| pulldown-cmark | 0.11.2 | MIT |
| qbsdiff | 1.4.4 | MIT |
| quick-error | 1.2.3 | MIT/Apache-2.0 |
| quick-error | 2.0.1 | MIT/Apache-2.0 |
| quick-xml | 0.39.4 | MIT |
| quinn | 0.11.8 | MIT OR Apache-2.0 |
| quinn-proto | 0.11.19 | MIT OR Apache-2.0 |
| quinn-udp | 0.5.9 | MIT OR Apache-2.0 |
| quote | 1.0.45 | MIT OR Apache-2.0 |
| radium | 0.7.0 | MIT |
| radix_trie | 0.2.1 | MIT |
| rand | 0.10.2 | MIT OR Apache-2.0 |
| rand | 0.8.5 | MIT OR Apache-2.0 |
| rand | 0.9.3 | MIT OR Apache-2.0 |
| rand_chacha | 0.3.1 | MIT OR Apache-2.0 |
| rand_chacha | 0.9.0 | MIT OR Apache-2.0 |
| rand_core | 0.10.0 | MIT OR Apache-2.0 |
| rand_core | 0.6.4 | MIT OR Apache-2.0 |
| rand_core | 0.9.3 | MIT OR Apache-2.0 |
| rand_pcg | 0.10.2 | MIT OR Apache-2.0 |
| raw-window-handle | 0.6.2 | MIT OR Apache-2.0 OR Zlib |
| rayon | 1.11.0 | MIT OR Apache-2.0 |
| rayon-core | 1.13.0 | MIT OR Apache-2.0 |
| rc2 | 0.8.1 | MIT OR Apache-2.0 |
| ref-cast | 1.0.22 | MIT OR Apache-2.0 |
| ref-cast-impl | 1.0.22 | MIT OR Apache-2.0 |
| regalloc2 | 0.11.1 | Apache-2.0 WITH LLVM-exception |
| regex | 1.12.2 | MIT OR Apache-2.0 |
| regex-automata | 0.4.13 | MIT OR Apache-2.0 |
| regex-syntax | 0.8.8 | MIT OR Apache-2.0 |
| resb | 0.1.2 | Unicode-3.0 |
| resolv-conf | 0.7.0 | MIT/Apache-2.0 |
| rfc6979 | 0.4.0 | Apache-2.0 OR MIT |
| ripemd | 0.1.3 | MIT OR Apache-2.0 |
| ron | 0.12.0 | MIT OR Apache-2.0 |
| rowan | 0.15.15 | MIT OR Apache-2.0 |
| rpm | 0.25.1 | Apache-2.0 OR MIT |
| rpm-version | 0.5.0 | MIT |
| rsa | 0.9.10 | MIT OR Apache-2.0 |
| rusqlite | 0.40.1 | MIT |
| rustc-hash | 1.1.0 | Apache-2.0/MIT |
| rustc-hash | 2.1.1 | Apache-2.0 OR MIT |
| rustc_version | 0.4.0 | MIT/Apache-2.0 |
| rustcrypto-ff | 0.14.0-rc.0 | MIT/Apache-2.0 |
| rustcrypto-group | 0.14.0-rc.0 | MIT/Apache-2.0 |
| rusticata-macros | 4.1.0 | MIT/Apache-2.0 |
| rustix | 0.38.34 | Apache-2.0 WITH LLVM-exception OR Apache-2.0 OR MIT |
| rustix | 1.1.6 | Apache-2.0 WITH LLVM-exception OR Apache-2.0 OR MIT |
| rustls | 0.23.46 | Apache-2.0 OR ISC OR MIT |
| rustls-native-certs | 0.7.0 | Apache-2.0 OR ISC OR MIT |
| rustls-pemfile | 2.1.2 | Apache-2.0 OR ISC OR MIT |
| rustls-pki-types | 1.12.0 | MIT OR Apache-2.0 |
| rustls-tokio-stream | 0.8.0 | MIT |
| rustls-webpki | 0.103.16 | ISC |
| rustversion | 1.0.22 | MIT OR Apache-2.0 |
| rustyline | 17.0.0 | MIT |
| rustyline-derive | 0.11.1 | MIT |
| ryu | 1.0.17 | Apache-2.0 OR BSL-1.0 |
| ryu-js | 1.0.1 | Apache-2.0 OR BSL-1.0 |
| sacabase | 2.0.0 | MIT |
| safe_arch | 0.7.4 | Zlib OR Apache-2.0 OR MIT |
| salsa20 | 0.10.2 | MIT OR Apache-2.0 |
| same-file | 1.0.6 | Unlicense/MIT |
| scoped-tls | 1.0.1 | MIT/Apache-2.0 |
| scopeguard | 1.2.0 | MIT OR Apache-2.0 |
| scrypt | 0.11.0 | MIT OR Apache-2.0 |
| sec1 | 0.7.3 | Apache-2.0 OR MIT |
| sec1 | 0.8.0-rc.13 | Apache-2.0 OR MIT |
| semver | 1.0.25 | MIT OR Apache-2.0 |
| seq-macro | 0.3.6 | MIT OR Apache-2.0 |
| serde | 1.0.228 | MIT OR Apache-2.0 |
| serde_bytes | 0.11.14 | MIT OR Apache-2.0 |
| serde_core | 1.0.228 | MIT OR Apache-2.0 |
| serde_derive | 1.0.228 | MIT OR Apache-2.0 |
| serde_json | 1.0.140 | MIT OR Apache-2.0 |
| serde_repr | 0.1.19 | MIT OR Apache-2.0 |
| serde_v8 | 0.322.0 | MIT |
| serdect | 0.2.0 | Apache-2.0 OR MIT |
| sha1 | 0.10.6 | MIT OR Apache-2.0 |
| sha1_smol | 1.0.1 | BSD-3-Clause |
| sha2 | 0.10.8 | MIT OR Apache-2.0 |
| sha3 | 0.10.8 | MIT OR Apache-2.0 |
| sha3 | 0.11.0-rc.8 | MIT OR Apache-2.0 |
| shlex | 1.3.0 | MIT OR Apache-2.0 |
| signal-hook | 0.3.18 | Apache-2.0/MIT |
| signal-hook-mio | 0.2.5 | MIT OR Apache-2.0 |
| signal-hook-registry | 1.4.8 | MIT OR Apache-2.0 |
| signature | 2.2.0 | Apache-2.0 OR MIT |
| signature | 3.0.0-rc.10 | Apache-2.0 OR MIT |
| simd-adler32 | 0.3.7 | MIT |
| simdutf8 | 0.1.5 | MIT OR Apache-2.0 |
| similar | 2.7.0 | Apache-2.0 |
| siphasher | 0.3.11 | MIT/Apache-2.0 |
| siphasher | 1.0.1 | MIT/Apache-2.0 |
| slab | 0.4.9 | MIT |
| slug | 0.1.5 | MIT/Apache-2.0 |
| sm3 | 0.4.2 | MIT OR Apache-2.0 |
| smallvec | 1.15.1 | MIT OR Apache-2.0 |
| smartstring | 1.0.1 | MPL-2.0+ |
| socket2 | 0.5.10 | MIT OR Apache-2.0 |
| socket2 | 0.6.5 | MIT OR Apache-2.0 |
| solana-nohash-hasher | 0.2.1 | Apache-2.0 OR MIT |
| sourcemap | 9.2.0 | BSD-3-Clause |
| spin | 0.9.8 | MIT |
| spirv | 0.4.0+sdk-1.4.341.0 | Apache-2.0 |
| spki | 0.7.3 | Apache-2.0 OR MIT |
| spki | 0.8.0-rc.4 | Apache-2.0 OR MIT |
| sptr | 0.3.2 | MIT OR Apache-2.0 |
| stable_deref_trait | 1.2.0 | MIT/Apache-2.0 |
| stacker | 0.1.25 | MIT OR Apache-2.0 |
| static_assertions | 1.1.0 | MIT OR Apache-2.0 |
| strck | 1.0.0 | MIT |
| string_enum | 1.0.2 | Apache-2.0 |
| stringcase | 0.4.0 | MIT |
| strsim | 0.11.1 | MIT |
| strum | 0.27.1 | MIT |
| strum_macros | 0.27.1 | MIT |
| subtle | 2.6.1 | BSD-3-Clause |
| suffix_array | 0.5.0 | MIT |
| swc_allocator | 4.0.1 | Apache-2.0 |
| swc_atoms | 9.0.0 | Apache-2.0 |
| swc_common | 17.0.1 | Apache-2.0 |
| swc_config | 3.1.2 | Apache-2.0 |
| swc_config_macro | 1.0.1 | Apache-2.0 |
| swc_ecma_ast | 18.0.0 | Apache-2.0 |
| swc_ecma_codegen | 20.0.2 | Apache-2.0 |
| swc_ecma_codegen_macros | 2.0.2 | Apache-2.0 |
| swc_ecma_lexer | 26.0.0 | Apache-2.0 |
| swc_ecma_loader | 17.0.0 | Apache-2.0 |
| swc_ecma_parser | 27.0.7 | Apache-2.0 |
| swc_ecma_transforms_base | 30.0.1 | Apache-2.0 |
| swc_ecma_transforms_classes | 30.0.0 | Apache-2.0 |
| swc_ecma_transforms_macros | 1.0.1 | Apache-2.0 |
| swc_ecma_transforms_proposal | 30.0.0 | Apache-2.0 |
| swc_ecma_transforms_react | 33.0.0 | Apache-2.0 |
| swc_ecma_transforms_typescript | 33.0.0 | Apache-2.0 |
| swc_ecma_utils | 24.0.0 | Apache-2.0 |
| swc_ecma_visit | 18.0.1 | Apache-2.0 |
| swc_eq_ignore_macros | 1.0.1 | Apache-2.0 |
| swc_macros_common | 1.0.1 | Apache-2.0 |
| swc_sourcemap | 9.3.4 | BSD-3-Clause |
| swc_ts_fast_strip | 36.0.0 | Apache-2.0 |
| swc_visit | 2.0.1 | Apache-2.0 |
| syn | 1.0.109 | MIT OR Apache-2.0 |
| syn | 2.0.117 | MIT OR Apache-2.0 |
| syn | 3.0.10 | MIT OR Apache-2.0 |
| syn-match | 0.3.1 | MIT |
| sync_wrapper | 1.0.2 | Apache-2.0 |
| synstructure | 0.12.6 | MIT |
| synstructure | 0.13.1 | MIT |
| sys_traits | 0.1.28 | MIT |
| sys_traits_macros | 0.1.0 | MIT |
| tagptr | 0.2.0 | MIT/Apache-2.0 |
| tap | 1.0.1 | MIT |
| tar | 0.4.46 | MIT OR Apache-2.0 |
| target-lexicon | 0.13.2 | Apache-2.0 WITH LLVM-exception |
| tempfile | 3.10.1 | MIT OR Apache-2.0 |
| temporal_capi | 0.2.3 | MIT OR Apache-2.0 |
| temporal_rs | 0.2.3 | MIT OR Apache-2.0 |
| termcolor | 1.4.1 | Unlicense OR MIT |
| text-size | 1.1.1 | MIT OR Apache-2.0 |
| text_lines | 0.6.0 | MIT |
| thiserror | 1.0.69 | MIT OR Apache-2.0 |
| thiserror | 2.0.12 | MIT OR Apache-2.0 |
| thiserror-impl | 1.0.69 | MIT OR Apache-2.0 |
| thiserror-impl | 2.0.12 | MIT OR Apache-2.0 |
| thread_local | 1.1.8 | MIT OR Apache-2.0 |
| time | 0.3.47 | MIT OR Apache-2.0 |
| time-core | 0.1.8 | MIT OR Apache-2.0 |
| time-macros | 0.2.27 | MIT OR Apache-2.0 |
| timezone_provider | 0.2.3 | MIT OR Apache-2.0 |
| tiny-keccak | 2.0.2 | CC0-1.0 |
| tiny_pretty | 0.2.0 | MIT |
| tinystr | 0.7.6 | Unicode-3.0 |
| tinystr | 0.8.3 | Unicode-3.0 |
| tinyvec | 1.6.0 | Zlib OR Apache-2.0 OR MIT |
| tinyvec_macros | 0.1.1 | MIT OR Apache-2.0 OR Zlib |
| tokio | 1.54.1 | MIT |
| tokio-eld | 0.3.0 | MIT OR Apache-2.0 |
| tokio-macros | 2.7.2 | MIT |
| tokio-metrics | 0.3.1 | MIT |
| tokio-rustls | 0.26.0 | MIT/Apache-2.0 |
| tokio-socks | 0.5.3 | MIT |
| tokio-stream | 0.1.16 | MIT |
| tokio-util | 0.7.16 | MIT |
| tokio-vsock | 0.7.1 | Apache-2.0 |
| toml_datetime | 0.7.5+spec-1.1.0 | MIT OR Apache-2.0 |
| toml_edit | 0.23.5 | MIT OR Apache-2.0 |
| toml_parser | 1.0.9+spec-1.1.0 | MIT OR Apache-2.0 |
| tower | 0.5.2 | MIT |
| tower-layer | 0.3.3 | MIT |
| tower-service | 0.3.3 | MIT |
| tracing | 0.1.44 | MIT |
| tracing-attributes | 0.1.31 | MIT |
| tracing-core | 0.1.36 | MIT |
| triomphe | 0.1.13 | MIT OR Apache-2.0 |
| try-lock | 0.2.5 | MIT |
| twox-hash | 1.6.3 | MIT |
| twox-hash | 2.1.2 | MIT |
| typed-arena | 2.0.2 | MIT |
| typeid | 1.0.3 | MIT OR Apache-2.0 |
| typenum | 1.17.0 | MIT OR Apache-2.0 |
| ucd-trie | 0.1.6 | MIT OR Apache-2.0 |
| unicase | 2.7.0 | MIT/Apache-2.0 |
| unicode-general-category | 1.1.0 | Apache-2.0 |
| unicode-id-start | 1.4.0 | (MIT OR Apache-2.0) AND Unicode-3.0 |
| unicode-ident | 1.0.12 | (MIT OR Apache-2.0) AND Unicode-DFS-2016 |
| unicode-normalization | 0.1.23 | MIT/Apache-2.0 |
| unicode-segmentation | 1.11.0 | MIT/Apache-2.0 |
| unicode-width | 0.1.13 | MIT OR Apache-2.0 |
| unicode-width | 0.2.2 | MIT OR Apache-2.0 |
| unicode-xid | 0.2.6 | MIT OR Apache-2.0 |
| unicode_categories | 0.1.1 | MIT OR Apache-2.0 |
| universal-hash | 0.5.1 | MIT OR Apache-2.0 |
| untrusted | 0.7.1 | ISC |
| untrusted | 0.9.0 | ISC |
| url | 2.5.7 | MIT OR Apache-2.0 |
| urlpattern | 0.4.2 | MIT |
| utf-8 | 0.7.6 | MIT OR Apache-2.0 |
| utf16_iter | 1.0.5 | Apache-2.0 OR MIT |
| utf8-width | 0.1.7 | MIT |
| utf8_iter | 1.0.4 | Apache-2.0 OR MIT |
| utf8parse | 0.2.1 | Apache-2.0 OR MIT |
| uuid | 1.21.0 | Apache-2.0 OR MIT |
| v8 | 150.4.0 | MIT |
| v8_valueserializer | 0.1.2 | MIT |
| vcpkg | 0.2.15 | MIT/Apache-2.0 |
| version_check | 0.9.4 | MIT/Apache-2.0 |
| vsimd | 0.8.0 | MIT |
| vsock | 0.5.1 | Apache-2.0 |
| vte | 0.13.1 | Apache-2.0 OR MIT |
| vte_generate_state_changes | 0.1.1 | Apache-2.0 OR MIT |
| walkdir | 2.5.0 | Unlicense/MIT |
| want | 0.3.1 | MIT |
| wasm_dep_analyzer | 0.4.0 | MIT |
| wasmparser | 0.244.0 | Apache-2.0 WITH LLVM-exception OR Apache-2.0 OR MIT |
| wayland-sys | 0.31.11 | MIT |
| web-time | 1.1.0 | MIT OR Apache-2.0 |
| web-transport-proto | 0.2.7 | MIT OR Apache-2.0 |
| webpki-root-certs | 1.0.10 | CDLA-Permissive-2.0 |
| webpki-roots | 1.0.10 | CDLA-Permissive-2.0 |
| weezl | 0.1.8 | MIT OR Apache-2.0 |
| wgpu-core | 29.0.1 | MIT OR Apache-2.0 |
| wgpu-core-deps-windows-linux-android | 29.0.3 | MIT OR Apache-2.0 |
| wgpu-hal | 29.0.3 | MIT OR Apache-2.0 |
| wgpu-naga-bridge | 29.0.3 | MIT OR Apache-2.0 |
| wgpu-types | 29.0.1 | MIT OR Apache-2.0 |
| which | 6.0.1 | MIT |
| which | 8.0.0 | MIT |
| wide | 0.7.33 | Zlib OR Apache-2.0 OR MIT |
| winnow | 0.6.26 | MIT |
| winnow | 0.7.14 | MIT |
| write16 | 1.0.0 | Apache-2.0 OR MIT |
| writeable | 0.5.5 | Unicode-3.0 |
| writeable | 0.6.2 | Unicode-3.0 |
| wtf8 | 0.1.0 | MIT |
| wyz | 0.5.1 | MIT |
| x25519-dalek | 2.0.1 | BSD-3-Clause |
| x509-parser | 0.15.1 | MIT OR Apache-2.0 |
| xattr | 1.3.1 | MIT/Apache-2.0 |
| xxhash-rust | 0.8.16 | BSL-1.0 |
| yaml_parser | 0.2.1 | MIT |
| yansi | 1.0.1 | MIT OR Apache-2.0 |
| yasna | 0.5.2 | MIT OR Apache-2.0 |
| yoke | 0.7.4 | Unicode-3.0 |
| yoke | 0.8.2 | Unicode-3.0 |
| yoke-derive | 0.7.4 | Unicode-3.0 |
| yoke-derive | 0.8.2 | Unicode-3.0 |
| zerocopy | 0.7.32 | BSD-2-Clause OR Apache-2.0 OR MIT |
| zerocopy | 0.8.27 | BSD-2-Clause OR Apache-2.0 OR MIT |
| zerocopy-derive | 0.7.32 | BSD-2-Clause OR Apache-2.0 OR MIT |
| zerocopy-derive | 0.8.27 | BSD-2-Clause OR Apache-2.0 OR MIT |
| zerofrom | 0.1.7 | Unicode-3.0 |
| zerofrom-derive | 0.1.7 | Unicode-3.0 |
| zeroize | 1.8.1 | Apache-2.0 OR MIT |
| zeroize_derive | 1.4.2 | Apache-2.0 OR MIT |
| zerotrie | 0.2.4 | Unicode-3.0 |
| zerovec | 0.10.4 | Unicode-3.0 |
| zerovec | 0.11.6 | Unicode-3.0 |
| zerovec-derive | 0.10.3 | Unicode-3.0 |
| zerovec-derive | 0.11.3 | Unicode-3.0 |
| zip | 2.4.1 | MIT |
| zoneinfo64 | 0.3.0 | Unicode-3.0 |
| zstd | 0.13.2 | MIT |
| zstd-safe | 7.2.4 | MIT OR Apache-2.0 |
| zstd-sys | 2.0.15+zstd.1.5.7 | MIT/Apache-2.0 |
| zune-core | 0.4.12 | MIT OR Apache-2.0 OR Zlib |
| zune-jpeg | 0.4.13 | MIT OR Apache-2.0 OR Zlib |
