// SIGILL on normal exit after a non-blocking FFI call (item 3).
// Usage: deno run --allow-ffi ffi_exit.ts <blocking|nonblocking|nonblocking-exit>
const mode = Deno.args[0] ?? "nonblocking";
const lib = Deno.dlopen("libc.a(shr_64.o)", {
  getpid: { parameters: [], result: "i32", nonblocking: mode !== "blocking" },
});
const pid = mode === "blocking" ? lib.symbols.getpid() : await lib.symbols.getpid();
console.log(mode, "pid", pid);
if (mode === "nonblocking-exit") Deno.exit(0);
