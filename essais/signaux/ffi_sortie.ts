// SIGILL on normal exit after a non-blocking FFI call (item 3).
// Usage: deno run --allow-ffi ffi_sortie.ts <bloquant|nonbloquant|nonbloquant-exit>
const mode = Deno.args[0] ?? "nonbloquant";
const lib = Deno.dlopen("libc.a(shr_64.o)", {
  getpid: { parameters: [], result: "i32", nonblocking: mode !== "bloquant" },
});
const pid = mode === "bloquant" ? lib.symbols.getpid() : await lib.symbols.getpid();
console.log(mode, "pid", pid);
if (mode === "nonbloquant-exit") Deno.exit(0);
