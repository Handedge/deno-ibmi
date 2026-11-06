/* What PASE provides for Deno.hostname, Deno.osUptime and Deno.memoryUsage().rss */
#define _ALL_SOURCE
#include <errno.h>
#include <procinfo.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/times.h>
#include <time.h>
#include <unistd.h>
#include <utmpx.h>

int main(void)
{
    long hmax = sysconf(_SC_HOST_NAME_MAX);
    char h[300] = "";
    int rh = gethostname(h, sizeof h);
    printf("sysconf(_SC_HOST_NAME_MAX)=%ld errno=%d ; gethostname=%d '%s'\n", hmax, errno, rh, h);

    struct tms t;
    clock_t c = times(&t);
    long tck = sysconf(_SC_CLK_TCK);
    printf("times()=%ld ticks, CLK_TCK=%ld -> %.0f s (%.1f h)\n", (long)c, tck, (double)c / tck, (double)c / tck / 3600);

    struct utmpx *u;
    setutxent();
    while ((u = getutxent()) != NULL)
        if (u->ut_type == BOOT_TIME)
            printf("utmpx BOOT_TIME : %ld -> il y a %.1f h\n", (long)u->ut_tv.tv_sec, (time(NULL) - u->ut_tv.tv_sec) / 3600.0);
    endutxent();

    void *p = malloc(200 << 20);
    memset(p, 1, 200 << 20);
    struct rusage r;
    getrusage(RUSAGE_SELF, &r);
    printf("getrusage : ru_maxrss=%ld Ko, ru_idrss=%ld\n", r.ru_maxrss, r.ru_idrss);

    struct procentry64 pe;
    pid_t idx = getpid();
    int n = getprocs64(&pe, sizeof pe, NULL, 0, &idx, 1);
    if (n == 1)
        printf("getprocs64 : pid=%d pi_size=%llu pi_drss=%llu pi_trss=%llu pi_dvm=%llu (pages de 4 Ko ?) start=%llu\n",
               (int)pe.pi_pid, (unsigned long long)pe.pi_size, (unsigned long long)pe.pi_drss,
               (unsigned long long)pe.pi_trss, (unsigned long long)pe.pi_dvm, (unsigned long long)pe.pi_start);
    else
        printf("getprocs64 -> %d errno=%d\n", n, errno);
    pid_t un = 1;
    if (getprocs64(&pe, sizeof pe, NULL, 0, &un, 1) == 1)
        printf("pid 1 : start=%llu -> il y a %.1f h\n", (unsigned long long)pe.pi_start, (time(NULL) - (double)pe.pi_start) / 3600.0);
    return 0;
}
