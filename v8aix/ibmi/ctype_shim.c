/* Temporary shim: the PASE ctype.h has no extern "C" block; compiled as
 * C++ by clang (AIX target), it yields calls to the mangled names
 * _Z7toupperi... This file provides those names and forwards to the libc C functions.
 * Remove once the LINUXBUILD sysroot ships the patched ctype.h. */
extern int toupper(int), tolower(int), isprint(int), isascii(int), isalpha(int), isalnum(int);
int _Z7toupperi(int c) { return toupper(c); }
int _Z7toloweri(int c) { return tolower(c); }
int _Z7isprinti(int c) { return isprint(c); }
int _Z7isasciii(int c) { return isascii(c); }
int _Z7isalphai(int c) { return isalpha(c); }
int _Z7isalnumi(int c) { return isalnum(c); }
