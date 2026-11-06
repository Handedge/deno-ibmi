# Reads and rewrites the import table (.loader section) of an XCOFF64 executable.
# Usage: xcoff_imports.py FILE                          -> prints the imports
#        xcoff_imports.py FILE base:member=base:member ... [--libpath PATH]
# The table is rebuilt at the same length: the difference is absorbed
# by padding the search path (entry 0) with trailing ':' characters.
import struct
import sys


def lire(d):
    magic, nscns, _, _, opthdr, _, _ = struct.unpack_from(">HHIQHHI", d, 0)
    if magic != 0x01F7:
        sys.exit(f"pas un XCOFF64 (magic {magic:#x})")
    pos = 24 + opthdr
    for _ in range(nscns):
        nom = d[pos:pos + 8].rstrip(b"\0")
        scnptr = struct.unpack_from(">Q", d, pos + 32)[0]
        if nom == b".loader":
            ver, nsyms, nreloc, istlen, nimpid, stlen, impoff = struct.unpack_from(">IIIIIIQ", d, scnptr)
            debut = scnptr + impoff
            brut = bytes(d[debut:debut + istlen])
            champs = brut.split(b"\0")
            ids = [champs[i * 3:i * 3 + 3] for i in range(nimpid)]
            return debut, istlen, ids
        pos += 72
    sys.exit("pas de section .loader")


def main():
    fichier = sys.argv[1]
    d = bytearray(open(fichier, "rb").read())
    debut, istlen, ids = lire(d)
    remplacements, libpath = {}, None
    args = sys.argv[2:]
    while args:
        a = args.pop(0)
        if a == "--libpath":
            libpath = args.pop(0).encode()
        else:
            g, dr = a.split("=")
            remplacements[tuple(g.encode().split(b":"))] = dr.encode().split(b":")
    for i, (p, b, m) in enumerate(ids):
        print(i, p.decode()[:90], b.decode(), m.decode())
    if not remplacements and libpath is None:
        return
    nouv = [list(x) for x in ids]
    for x in nouv[1:]:
        cle = (x[1], x[2])
        if cle in remplacements:
            x[1], x[2] = remplacements[cle]
    if libpath is not None:
        nouv[0][0] = libpath
    # each import: path (empty here) \0 base \0 member \0
    corps = b"".join(b"\0".join(x) + b"\0" for x in nouv[1:])
    reste = istlen - len(corps) - len(nouv[0][1]) - len(nouv[0][2]) - 3
    if reste < len(nouv[0][0]):
        sys.exit(f"table trop longue de {len(nouv[0][0]) - reste} octets")
    tete = nouv[0][0] + b":" * (reste - len(nouv[0][0]))
    table = tete + b"\0" + nouv[0][1] + b"\0" + nouv[0][2] + b"\0" + corps
    assert len(table) == istlen
    d[debut:debut + istlen] = table
    open(fichier, "wb").write(d)
    print("--- apres modification")
    for i, (p, b, m) in enumerate(lire(d)[2]):
        print(i, p.decode()[:90], b.decode(), m.decode())


if __name__ == "__main__":
    main()
