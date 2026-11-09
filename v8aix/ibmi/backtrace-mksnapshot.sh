#!/QOpenSys/usr/bin/sh
# Call stack of mksnapshot at crash time (core file), using dbx64.
exec > /tmp/rustpoc/backtrace-mksnapshot.log 2>&1
export PATH=/QOpenSys/pkgs/bin:/QOpenSys/usr/bin
cd /QOpenSys/opt/denoibmi/v8aix/aix
ls -l core* 2>&1
printf 'where\nthread\nregisters\nlisti\nquit\n' > /tmp/rustpoc/dbx.cmd
timeout 300 /QOpenSys/usr/bin/dbx64 ./mksnapshot core < /tmp/rustpoc/dbx.cmd 2>&1 | grep -v '^$' | cut -c1-220 | head -120
echo DONE
