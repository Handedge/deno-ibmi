#!/QOpenSys/usr/bin/sh
# deno launcher for IBM i (PASE), installed as /QOpenSys/pkgs/bin/deno by the deno RPM.
#   XPG_SUS_ENV=ON       direct MAP_FIXED mmap (needed by V8 on AIX); without it, deno re-executes
#                        itself at startup to set it (+0.1 s)
#   DENO_NO_UPDATE_CHECK no outbound call at startup ("deno upgrade" does not apply: install with yum)
# Both can be overridden by the caller.
: "${XPG_SUS_ENV:=ON}"
: "${DENO_NO_UPDATE_CHECK:=1}"
export XPG_SUS_ENV DENO_NO_UPDATE_CHECK
exec /QOpenSys/pkgs/lib/deno/deno "$@"
