/*
 * libpaseat: emulation of the *at() calls for IBM i PASE.
 *
 * Under PASE (IBM i 7.5), openat/fstatat/unlinkat... return EINVAL as soon as
 * the directory descriptor is not AT_FDCWD (observed on 2026-10-28 on
 * IBMI). The Rust standard library (remove_dir_all...) and many
 * crates rely on them.
 *
 * Approach: recover the absolute path of the directory referred to by the
 * descriptor, then call the classic function (open, stat, unlink...) on
 * the full path. A descriptor's path comes from a cache filled by
 * our openat, validated by (st_dev, st_ino); failing that, fchdir + getcwd
 * under a lock (the window during which the process current directory changes
 * is very short).
 *
 * Linked BEFORE libc (-lpaseat): the AIX linker then binds these
 * symbols to libpaseat.a(shr_64.o) instead of libc.a(shr_64.o).
 */
#define _ALL_SOURCE
#define _LARGE_FILE_API
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <pthread.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#define NB_CACHE 4096

struct entree { dev_t dev; ino_t ino; char *chemin; };
static struct entree cache[NB_CACHE];
static pthread_mutex_t verrou = PTHREAD_MUTEX_INITIALIZER;

static void memoriser(int fd, const char *chemin)
{
    struct stat st;
    if (fd < 0 || fd >= NB_CACHE || fstat(fd, &st) != 0 || !S_ISDIR(st.st_mode))
        return;
    char *copie = strdup(chemin);
    if (!copie)
        return;
    pthread_mutex_lock(&verrou);
    free(cache[fd].chemin);
    cache[fd].dev = st.st_dev;
    cache[fd].ino = st.st_ino;
    cache[fd].chemin = copie;
    pthread_mutex_unlock(&verrou);
}

/* Absolute path of the directory open on fd (or of the current directory). */
static int chemin_de(int fd, char *buf, size_t n)
{
    if (fd == AT_FDCWD)
        return getcwd(buf, n) ? 0 : -1;
    struct stat st;
    if (fstat(fd, &st) != 0)
        return -1;
    if (!S_ISDIR(st.st_mode)) {
        errno = ENOTDIR;
        return -1;
    }
    int ok = -1;
    pthread_mutex_lock(&verrou);
    if (fd < NB_CACHE && cache[fd].chemin && cache[fd].dev == st.st_dev && cache[fd].ino == st.st_ino) {
        if (strlen(cache[fd].chemin) < n) {
            strcpy(buf, cache[fd].chemin);
            ok = 0;
        } else {
            errno = ENAMETOOLONG;
        }
        pthread_mutex_unlock(&verrou);
        return ok;
    }
    /* fallback: fchdir + getcwd, then back to the original current directory */
    int ici = open(".", O_RDONLY);
    if (ici >= 0) {
        if (fchdir(fd) == 0) {
            if (getcwd(buf, n))
                ok = 0;
            int e = errno;
            fchdir(ici);
            errno = e;
        }
        close(ici);
    }
    pthread_mutex_unlock(&verrou);
    if (ok == 0)
        memoriser(fd, buf);
    return ok;
}

/* Builds the full path; returns the name unchanged if it is absolute. */
static const char *complet(int dirfd, const char *nom, char *buf)
{
    if (nom == NULL) {
        errno = EFAULT;
        return NULL;
    }
    static int trace = -1;
    if (trace < 0)
        trace = getenv("PASEAT_TRACE") != NULL;
    if (nom[0] == '/' || dirfd == AT_FDCWD) {
        if (trace)
            fprintf(stderr, "paseat: fd=%d nom=%s (direct)\n", dirfd, nom);
        return nom;
    }
    char rep[PATH_MAX];
    if (chemin_de(dirfd, rep, sizeof rep) != 0) {
        if (trace)
            fprintf(stderr, "paseat: fd=%d nom=%s -> echec chemin errno=%d\n", dirfd, nom, errno);
        return NULL;
    }
    if (trace)
        fprintf(stderr, "paseat: fd=%d nom=%s -> %s/%s\n", dirfd, nom, rep, nom);
    size_t lr = strlen(rep), ln = strlen(nom);
    if (lr + 1 + ln + 1 > PATH_MAX) {
        errno = ENAMETOOLONG;
        return NULL;
    }
    memcpy(buf, rep, lr);
    if (lr == 0 || rep[lr - 1] != '/')
        buf[lr++] = '/';
    memcpy(buf + lr, nom, ln + 1);
    return buf;
}

static int ouvrir(int dirfd, const char *nom, int flags, mode_t mode, int en64)
{
    char buf[PATH_MAX];
    const char *p = complet(dirfd, nom, buf);
    if (!p)
        return -1;
    struct stat st;
    /* O_DIRECTORY on something other than a directory: ENOTDIR BEFORE opening. Opening
       first blocked on a FIFO (open for reading waits for a writer): a recursive
       Deno.remove of a directory containing a FIFO hung (readableStreamCancelOnFifo). */
    if ((flags & O_DIRECTORY)
        && ((flags & O_NOFOLLOW) ? lstat(p, &st) : stat(p, &st)) == 0
        && !S_ISDIR(st.st_mode)) {
        errno = ENOTDIR;
        return -1;
    }
    int fd = en64 ? open64(p, flags, mode) : open(p, flags, mode);
    /* PASE ignores O_DIRECTORY on a regular file: enforce the standard behavior
       (check kept after opening, in case the file changed in the meantime) */
    if (fd >= 0 && (flags & O_DIRECTORY) && fstat(fd, &st) == 0 && !S_ISDIR(st.st_mode)) {
        close(fd);
        errno = ENOTDIR;
        return -1;
    }
    if (fd >= 0) {
        /* absolute path cached (directories only) for subsequent *at() calls */
        char abs[PATH_MAX];
        if (p[0] == '/')
            memoriser(fd, p);
        else if (getcwd(abs, sizeof abs) && strlen(abs) + strlen(p) + 2 < PATH_MAX) {
            strcat(abs, "/");
            strcat(abs, p);
            memoriser(fd, abs);
        }
    }
    return fd;
}

int openat(int dirfd, const char *nom, int flags, ...)
{
    mode_t mode = 0;
    if (flags & O_CREAT) {
        va_list ap;
        va_start(ap, flags);
        mode = (mode_t)va_arg(ap, int);
        va_end(ap);
    }
    return ouvrir(dirfd, nom, flags, mode, 0);
}

int openat64(int dirfd, const char *nom, int flags, ...)
{
    mode_t mode = 0;
    if (flags & O_CREAT) {
        va_list ap;
        va_start(ap, flags);
        mode = (mode_t)va_arg(ap, int);
        va_end(ap);
    }
    return ouvrir(dirfd, nom, flags, mode, 1);
}

int fstatat(int dirfd, const char *nom, struct stat *st, int flags)
{
    char buf[PATH_MAX];
    const char *p = complet(dirfd, nom, buf);
    if (!p)
        return -1;
    return (flags & AT_SYMLINK_NOFOLLOW) ? lstat(p, st) : stat(p, st);
}

int fstatat64(int dirfd, const char *nom, struct stat64 *st, int flags)
{
    char buf[PATH_MAX];
    const char *p = complet(dirfd, nom, buf);
    if (!p)
        return -1;
    return (flags & AT_SYMLINK_NOFOLLOW) ? lstat64(p, st) : stat64(p, st);
}

int unlinkat(int dirfd, const char *nom, int flags)
{
    char buf[PATH_MAX];
    const char *p = complet(dirfd, nom, buf);
    if (!p)
        return -1;
    return (flags & AT_REMOVEDIR) ? rmdir(p) : unlink(p);
}

int mkdirat(int dirfd, const char *nom, mode_t mode)
{
    char buf[PATH_MAX];
    const char *p = complet(dirfd, nom, buf);
    return p ? mkdir(p, mode) : -1;
}

int renameat(int d1, const char *n1, int d2, const char *n2)
{
    char b1[PATH_MAX], b2[PATH_MAX];
    const char *p1 = complet(d1, n1, b1), *p2 = p1 ? complet(d2, n2, b2) : NULL;
    return (p1 && p2) ? rename(p1, p2) : -1;
}

int linkat(int d1, const char *n1, int d2, const char *n2, int flags)
{
    (void)flags;
    char b1[PATH_MAX], b2[PATH_MAX];
    const char *p1 = complet(d1, n1, b1), *p2 = p1 ? complet(d2, n2, b2) : NULL;
    return (p1 && p2) ? link(p1, p2) : -1;
}

int symlinkat(const char *cible, int dirfd, const char *nom)
{
    char buf[PATH_MAX];
    const char *p = complet(dirfd, nom, buf);
    return p ? symlink(cible, p) : -1;
}

int readlinkat(int dirfd, const char *nom, char *dst, size_t n)
{
    char buf[PATH_MAX];
    const char *p = complet(dirfd, nom, buf);
    return p ? (int)readlink(p, dst, n) : -1;
}

int fchmodat(int dirfd, const char *nom, mode_t mode, int flags)
{
    (void)flags;
    char buf[PATH_MAX];
    const char *p = complet(dirfd, nom, buf);
    return p ? chmod(p, mode) : -1;
}

int fchownat(int dirfd, const char *nom, uid_t u, gid_t g, int flags)
{
    char buf[PATH_MAX];
    const char *p = complet(dirfd, nom, buf);
    if (!p)
        return -1;
    return (flags & AT_SYMLINK_NOFOLLOW) ? lchown(p, u, g) : chown(p, u, g);
}

int faccessat(int dirfd, const char *nom, int mode, int flags)
{
    (void)flags;
    char buf[PATH_MAX];
    const char *p = complet(dirfd, nom, buf);
    return p ? access(p, mode) : -1;
}

/* fcntl: PASE rejects F_DUPFD_CLOEXEC (EINVAL), used by std (try_clone)
 * and by tokio (signal driver). Emulated with F_DUPFD + FD_CLOEXEC. The real
 * fcntl is looked up in libc with dlsym: a direct call to "fcntl" from this
 * module would resolve to this very function. */
#include <dlfcn.h>
static int (*vrai_fcntl)(int, int, ...);
static pthread_once_t fcntl_une_fois = PTHREAD_ONCE_INIT;

static void charger_fcntl(void)
{
    void *h = dlopen("libc.a(shr_64.o)", RTLD_NOW | RTLD_MEMBER);
    if (h)
        vrai_fcntl = (int (*)(int, int, ...))dlsym(h, "fcntl");
}

int fcntl(int fd, int cmd, ...)
{
    va_list ap;
    va_start(ap, cmd);
    long arg = va_arg(ap, long);
    va_end(ap);
    pthread_once(&fcntl_une_fois, charger_fcntl);
    if (!vrai_fcntl) {
        errno = ENOSYS;
        return -1;
    }
    if (cmd == F_DUPFD_CLOEXEC) {
        int r = vrai_fcntl(fd, F_DUPFD, arg);
        if (r >= 0)
            vrai_fcntl(r, F_SETFD, FD_CLOEXEC);
        return r;
    }
    return vrai_fcntl(fd, cmd, arg);
}

/* read: reading a directory fails under PASE with EOPNOTSUPP (64, "Operation not
 * supported on socket") instead of EISDIR (Linux, native AIX): Deno.readFile on a
 * directory returned an unknown error code (readFileIsDirectoryErrorCode). Only the
 * failure path is affected; the real read is looked up in libc with dlsym, like fcntl. */
static ssize_t (*vrai_read)(int, void *, size_t);
static pthread_once_t read_une_fois = PTHREAD_ONCE_INIT;

static void charger_read(void)
{
    void *h = dlopen("libc.a(shr_64.o)", RTLD_NOW | RTLD_MEMBER);
    if (h)
        vrai_read = (ssize_t (*)(int, void *, size_t))dlsym(h, "read");
}

ssize_t read(int fd, void *buf, size_t n)
{
    pthread_once(&read_une_fois, charger_read);
    if (!vrai_read) {
        errno = ENOSYS;
        return -1;
    }
    ssize_t r = vrai_read(fd, buf, n);
    if (r < 0 && errno == EOPNOTSUPP) {
        struct stat st;
        if (fstat(fd, &st) == 0 && S_ISDIR(st.st_mode))
            errno = EISDIR;
        else
            errno = EOPNOTSUPP;
    }
    return r;
}

/* fdopendir is not intercepted: the native PASE one works with a valid
 * descriptor, and the Rust standard library keeps using the original
 * descriptor after the call. */
