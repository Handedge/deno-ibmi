# Standalone extractor for AIX installp images (BFF "backup by name" format).
# Layout: 0x48-byte file header (big-endian, magic 0x09006BEA),
# then per record: 0x44-byte header (little-endian), NUL-terminated name
# aligned on 8, 0x28-byte trailer, data.
# Record magic: 0xEA6B (raw), 0xEA6C (pack(1)-style Huffman), 0xEA6D.
# Records start on an 8-byte boundary: after each entry, we scan for the
# next header (symbolic links have a different layout from
# regular files).
import os
import stat
import struct
import sys

ENTETE_FICHIER = ">IIIII8sII8sII8sIII"
ENTETE_ENREG = "<HHIIIIIIIIIIIIIII"
FIN_ENREG = "<IIIIIIIIII"
MAGICS = (0xEA6B, 0xEA6C, 0xEA6D)
T_ENREG = struct.calcsize(ENTETE_ENREG)
T_FIN = struct.calcsize(FIN_ENREG)


def depack(donnees, taille_sortie):
    """Canonical Huffman of pack(1): levels, number of leaves per level,
    leaves, then the bit stream (most significant bit first)."""
    pos = 0
    niveaux = donnees[pos]; pos += 1
    feuilles = list(donnees[pos:pos + niveaux]); pos += niveaux
    feuilles[-1] += 1                       # the last level carries the end marker
    arbre = []
    for n in feuilles:
        arbre.append(donnees[pos:pos + n]); pos += n
    feuilles[-1] += 1
    # internal nodes per level, computed bottom-up
    internes = [0] * niveaux
    for niv in range(niveaux - 2, -1, -1):
        internes[niv] = (internes[niv + 1] + feuilles[niv + 1]) // 2
    sortie = bytearray()
    niv = code = 0
    for octet in donnees[pos:]:
        for i in range(7, -1, -1):
            code = (code << 1) | ((octet >> i) & 1)
            if code >= internes[niv]:
                idx = code - internes[niv]
                if idx >= len(arbre[niv]):          # end marker
                    return bytes(sortie)
                sortie.append(arbre[niv][idx])
                if len(sortie) == taille_sortie:
                    return bytes(sortie)
                code = niv = 0
            else:
                niv += 1
    return bytes(sortie)


def lire_nom(d, pos):
    fin = d.index(b"\0", pos)
    return d[pos:fin].decode("latin-1"), (fin + 8) & ~7


def prochain_entete(d, pos):
    pos = (pos + 7) & ~7
    while pos + 4 <= len(d):
        if struct.unpack_from("<H", d, pos + 2)[0] in MAGICS and d[pos + 1] == 0x0B:
            return pos
        pos += 8
    return len(d)


def extraire(src, sortie=None):
    d = open(src, "rb").read()
    if struct.unpack_from(">I", d, 0)[0] != 0x09006BEA:
        sys.exit("pas un fichier BFF")
    pos = struct.calcsize(ENTETE_FICHIER)
    while pos + T_ENREG <= len(d):
        h = struct.unpack_from(ENTETE_ENREG, d, pos)
        magic, mode, taille, taille_c = h[1], h[4], h[7], h[15]
        if magic not in MAGICS:
            break
        nom, p = lire_nom(d, pos + T_ENREG)
        p += T_FIN
        print(f"{magic:#x}\t{mode:o}\t{taille}\t{taille_c}\t{nom}")
        if (mode & 0o170000) == stat.S_IFREG and taille > 0:
            brut = d[p:p + taille_c]
            contenu = depack(brut, taille) if magic == 0xEA6C else brut
            if len(contenu) != taille:
                print(f"  ATTENTION : {len(contenu)} octets au lieu de {taille}")
            if sortie:
                cible = os.path.normpath(os.path.join(sortie, nom.lstrip("./")))
                if cible.startswith(os.path.normpath(sortie)):
                    os.makedirs(os.path.dirname(cible), exist_ok=True)
                    open(cible, "wb").write(contenu)
            p += taille_c
        pos = prochain_entete(d, p)


if __name__ == "__main__":
    extraire(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
