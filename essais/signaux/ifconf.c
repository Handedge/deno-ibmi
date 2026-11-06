/* Network interfaces under PASE (no getifaddrs): SIOCGIFCONF, netmasks, MAC. */
#define _ALL_SOURCE
#include <arpa/inet.h>
#include <net/if.h>
#include <net/if_dl.h>
#include <netinet/in.h>
#include <netinet/in6_var.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <unistd.h>

int main(void)
{
    printf("sizeof(ifreq)=%zu IFNAMSIZ=%d sizeof(sockaddr)=%zu SIOCGIFCONF=%#lx SIOCGIFNETMASK=%#lx SIOCGIFFLAGS=%#lx\n",
           sizeof(struct ifreq), IFNAMSIZ, sizeof(struct sockaddr), (unsigned long)SIOCGIFCONF,
           (unsigned long)SIOCGIFNETMASK, (unsigned long)SIOCGIFFLAGS);
    printf("sizeof(in6_ifreq)=%zu SIOCGIFNETMASK6=%#lx offsetof(ifr_flags)=%zu sizeof(ifr_flags)=%zu\n",
           sizeof(struct in6_ifreq), (unsigned long)SIOCGIFNETMASK6,
           offsetof(struct ifreq, ifr_flags), sizeof(((struct ifreq *)0)->ifr_flags));
    printf("AF_INET=%d AF_INET6=%d AF_LINK=%d sockaddr_dl: sdl_nlen@%zu sdl_alen@%zu sdl_data@%zu\n",
           AF_INET, AF_INET6, AF_LINK, offsetof(struct sockaddr_dl, sdl_nlen),
           offsetof(struct sockaddr_dl, sdl_alen), offsetof(struct sockaddr_dl, sdl_data));
    int s = socket(AF_INET, SOCK_DGRAM, 0);
    int s6 = socket(AF_INET6, SOCK_DGRAM, 0);
    char buf[16384];
    struct ifconf ifc = {.ifc_len = sizeof buf, .ifc_buf = buf};
    if (ioctl(s, SIOCGIFCONF, &ifc) < 0) { perror("SIOCGIFCONF"); return 1; }
    printf("ifc_len=%d\n", ifc.ifc_len);
    for (char *p = buf; p < buf + ifc.ifc_len;) {
        struct ifreq *r = (struct ifreq *)p;
        struct sockaddr *sa = &r->ifr_addr;
        size_t lg = IFNAMSIZ + (sa->sa_len > sizeof(struct sockaddr) ? sa->sa_len : sizeof(struct sockaddr));
        char a[64] = "", m[64] = "";
        if (sa->sa_family == AF_INET) {
            inet_ntop(AF_INET, &((struct sockaddr_in *)sa)->sin_addr, a, sizeof a);
            struct ifreq q; memset(&q, 0, sizeof q); strncpy(q.ifr_name, r->ifr_name, IFNAMSIZ);
            if (ioctl(s, SIOCGIFNETMASK, &q) == 0) inet_ntop(AF_INET, &((struct sockaddr_in *)&q.ifr_addr)->sin_addr, m, sizeof m);
        } else if (sa->sa_family == AF_INET6) {
            struct sockaddr_in6 *s6a = (struct sockaddr_in6 *)sa;
            inet_ntop(AF_INET6, &s6a->sin6_addr, a, sizeof a);
            struct in6_ifreq q; memset(&q, 0, sizeof q); strncpy(q.ifr_name, r->ifr_name, IFNAMSIZ);
            q.ifr_Addr = *s6a;
            if (ioctl(s6, SIOCGIFNETMASK6, &q) == 0) inet_ntop(AF_INET6, &q.ifr_Addr.sin6_addr, m, sizeof m);
            else snprintf(m, sizeof m, "(masque6 KO)");
            snprintf(a + strlen(a), sizeof a - strlen(a), " scope=%u", s6a->sin6_scope_id);
        } else if (sa->sa_family == AF_LINK) {
            struct sockaddr_dl *d = (struct sockaddr_dl *)sa;
            unsigned char *mac = (unsigned char *)d->sdl_data + d->sdl_nlen;
            for (int i = 0; i < d->sdl_alen && i < 6; i++) snprintf(a + strlen(a), sizeof a - strlen(a), "%02x%s", mac[i], i < 5 ? ":" : "");
        }
        struct ifreq fq; memset(&fq, 0, sizeof fq); strncpy(fq.ifr_name, r->ifr_name, IFNAMSIZ);
        int fl = ioctl(s, SIOCGIFFLAGS, &fq) == 0 ? fq.ifr_flags : -1;
        printf("%-8.16s fam=%2d len=%2d entree=%3zu flags=%#x addr=%s mask=%s\n", r->ifr_name, sa->sa_family, sa->sa_len, lg, fl, a, m);
        p += lg;
    }
    return 0;
}
