#!/QOpenSys/usr/bin/sh
# Starts the Deno CRUD API (HTTPS, port 3091) under DENOAPP, in subsystem DENOIBMI/DENOWS:
#   SBMJOB CMD(CALL PGM(QP2SHELL) PARM('/QOpenSys/usr/bin/sh' '/QOpenSys/opt/denoibmi/api/api.sh'))
#          JOB(DENOAPI) JOBD(DENOIBMI/DENOWS) USER(DENOAPP) JOBQ(DENOIBMI/DENOWS) ALWMLTTHD(*YES)
# Stop: kill (SIGTERM) the deno process; it closes the Db2 sessions and exits.
A=/QOpenSys/opt/denoibmi/api
exec >> $A/logs/api.log 2>&1
. /QOpenSys/opt/rust/rustenv.sh
ulimit -d 8388608; ulimit -s unlimited      # 8 GB at most (ASP incident of 2026-11-03)
export HOME=/home/DENOAPP DENO_DIR=$A/cache DENO_NO_UPDATE_CHECK=1 NO_COLOR=1 XPG_SUS_ENV=ON
echo "$(date '+%F %T') API starting as $(id -un)"
/QOpenSys/opt/denoibmi/bin/deno run --allow-net --allow-ffi --allow-sys \
  --allow-read=/QOpenSys/opt/denoibmi/tls --allow-env=DENOAPI_CLIENTS $A/api.ts
echo "$(date '+%F %T') API stopped rc=$?"
