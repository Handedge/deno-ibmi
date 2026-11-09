// Application served over HTTPS by LINUXBUILD (port 5180); /api calls are proxied to the
// Deno API on IBMI (HTTPS 3091), whose certificate is VERIFIED against the deno-ibmi CA.
// The browser only talks to LINUXBUILD: no CORS, and IBMI only accepts LINUXBUILD.
import { readFileSync } from "node:fs";
import https from "node:https";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const certs = new URL("./certs/", import.meta.url);
const tls = {
  cert: readFileSync(new URL("linuxbuild.crt", certs)),
  key: readFileSync(new URL("linuxbuild.key", certs)),
};
const proxy = {
  "/api": {
    target: "https://192.0.2.82:3091",
    changeOrigin: true,
    secure: true,
    agent: new https.Agent({ ca: readFileSync(new URL("ca.crt", certs)) }),
  },
};

export default defineConfig({
  plugins: [react()],
  // IBM Plex fonts referenced by Carbon as "~@ibm/plex/…" (webpack convention)
  resolve: { alias: [{ find: /^~(.+)$/, replacement: "$1" }] },
  server: { host: "0.0.0.0", port: 5180, https: tls, proxy },
  preview: { host: "0.0.0.0", port: 5180, https: tls, proxy },
  css: { preprocessorOptions: { scss: { api: "modern-compiler", quietDeps: true } } },
});
