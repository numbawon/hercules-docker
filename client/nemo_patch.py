#!/usr/bin/env python3
"""Apply the four NEMO patches a Hercules client needs to a kRO Ragexe.exe.

A headless port of NEMO's own scripts (gitlab.com/4144/Nemo, GPLv3):
  DisableCDGuard         Disable Cheat Defender Game Guard
  Disable1rag1Params     Disable 1rag1 type parameters
  EnableDNSSupport       Enable DNS support for clientinfo.xml
  ReadDataFolderFirst    Read Data Folder First
The fifth NEMO step, "Copy patched Cheat Defender Game Guard", is just copying
CDClient.dll from NEMO's Input folder next to the exe.

Usage: nemo_patch.py Ragexe.exe Ragexe_patched.exe
"""
import re
import struct
import sys


class PE:
    def __init__(self, data):
        self.d = bytearray(data)
        self.pe = struct.unpack_from('<I', self.d, 0x3c)[0]
        n, = struct.unpack_from('<H', self.d, self.pe + 6)
        opt, = struct.unpack_from('<H', self.d, self.pe + 20)
        self.base, = struct.unpack_from('<I', self.d, self.pe + 52)
        self.opt = self.pe + 24
        self.sec_off = self.opt + opt
        self.secs = []
        for i in range(n):
            nm, vs, va, rs, ro = struct.unpack_from('<8sIIII', self.d, self.sec_off + i * 40)
            self.secs.append((nm.rstrip(b'\0').decode(), va, vs, ro, rs))
        self.text = self.secs[0]
        dllchars, = struct.unpack_from('<H', self.d, self.opt + 70)
        if dllchars & 0x40:
            raise SystemExit('exe has ASLR (DYNAMIC_BASE); absolute-address patches are not safe')

    def raw2va(self, raw):
        for _, va, vs, ro, rs in self.secs:
            if ro <= raw < ro + rs:
                return self.base + va + raw - ro
        raise ValueError(hex(raw))

    def va2raw(self, va):
        rva = va - self.base
        for _, sva, vs, ro, rs in self.secs:
            if sva <= rva < sva + max(vs, rs):
                return ro + rva - sva
        raise ValueError(hex(va))

    def find_all(self, pattern, lo=None, hi=None):
        """pattern is hex with ?? wildcards; searched inside .text unless bounds given."""
        toks = pattern.split()
        rx = b''.join(b'.' if t == '??' else re.escape(bytes([int(t, 16)])) for t in toks)
        if lo is None:
            lo, hi = self.text[3], self.text[3] + self.text[4]
        return [lo + m.start() for m in re.finditer(rx, bytes(self.d[lo:hi + len(toks)]), re.S)]

    def find(self, pattern, lo=None, hi=None):
        r = self.find_all(pattern, lo, hi)
        return r[0] if r else -1

    def string_va(self, s):
        i = self.d.find(b'\0' + s.encode() + b'\0')
        return -1 if i < 0 else self.raw2va(i + 1)

    def hexb(self, h):
        return bytes(int(t, 16) for t in h.split())

    def put(self, raw, h):
        b = self.hexb(h)
        self.d[raw:raw + len(b)] = b

    def import_ptr(self, name, dll, ordinal=None):
        rva, = struct.unpack_from('<I', self.d, self.opt + 96 + 8)
        off = self.va2raw(self.base + rva)
        while True:
            oft, _, _, nm, ft = struct.unpack_from('<IIIII', self.d, off)
            if not nm:
                break
            dname = self.d[self.va2raw(self.base + nm):].split(b'\0')[0].decode().lower()
            if dname == dll.lower():
                thunk = oft or ft
                i = 0
                while True:
                    v, = struct.unpack_from('<I', self.d, self.va2raw(self.base + thunk) + 4 * i)
                    if not v:
                        break
                    if v & 0x80000000:
                        if ordinal is not None and (v & 0xffff) == ordinal:
                            return self.base + ft + 4 * i
                    else:
                        hn = self.d[self.va2raw(self.base + v) + 2:].split(b'\0')[0].decode()
                        if hn == name:
                            return self.base + ft + 4 * i
                    i += 1
            off += 20
        return -1


def le(v):
    return ' '.join('%02X' % b for b in struct.pack('<I', v & 0xffffffff))


def disable_cdguard(p):
    pats = [
        ("8B 0D ?? ?? ?? ?? E8 ?? ?? ?? ?? 3C 01 A1 ?? ?? ?? ?? 0F 94 C1 68 ?? ?? ?? ?? 88 48 05 E8 ?? ?? ?? ?? 8B C8 E8", 12),
        ("8B 0D ?? ?? ?? ?? E8 ?? ?? ?? ?? 3C 01 A1 ?? ?? ?? ?? 68 ?? ?? ?? ?? 0F 94 C1 88 48 05 E8 ?? ?? ?? ?? 8B C8 E8", 12),
    ]
    offs = []
    for pat, cmp_off in pats:
        offs = p.find_all(pat)
        if offs:
            break
    if not 1 <= len(offs) <= 2:
        return 'DisableCDGuard: pattern count %d' % len(offs)
    for o in offs:
        p.put(o + cmp_off, '00')
    mgr = struct.unpack_from('<I', p.d, offs[0] + 2)[0]
    o = p.find("A1 %s C6 40 05 01 B8 ?? ?? ?? 00" % le(mgr), offs[-1], offs[-1] + 0x150)
    if o < 0:
        return 'DisableCDGuard: step 2 not found'
    p.put(o + 8, '00')
    return True


def disable_1rag1(p):
    va = p.string_va('1rag1')
    if va < 0:
        return 'Disable1rag1: string not found'
    s = le(va)
    for pat, jmp in [
        ("68 %s ?? FF ?? 83 C4 08 85 ?? 75" % s, 13),
        ("68 %s ?? E8 ?? ?? ?? ?? 83 C4 08 85 ?? 75" % s, 16),
        ("68 %s ?? C7 05 ?? ?? ?? ?? 01 00 00 00 E8 ?? ?? ?? ?? 83 C4 08 85 ?? 75" % s, 26),
    ]:
        o = p.find(pat)
        if o >= 0:
            p.put(o + jmp, 'EB')
            return True
    return 'Disable1rag1: pattern not found'


def read_data_first(p):
    va = p.string_va('loading')
    if va < 0:
        return 'ReadDataFolderFirst: loading not found'
    s = le(va)
    o = p.find("74 07 C6 05 ?? ?? ?? ?? 01 68 %s" % s)
    repl, gloc, first = '90 90', 4, 0
    if o < 0:
        o = p.find("0F 45 ?? 88 ?? ?? ?? ?? ?? 68 %s" % s)
        repl, gloc, first = '90 8B', 5, 0
    if o < 0:
        o = p.find("0F B6 0D ?? ?? ?? ?? 85 C0 68 %s 0F 45 CE 88 0D" % s)
        repl, gloc, first = '90 8B', 3, 14
    if o < 0:
        return 'ReadDataFolderFirst: loading reference missing'
    p.put(o + first, repl)
    g = struct.unpack_from('<I', p.d, o + gloc)[0]
    offs = p.find_all("80 3D %s 00" % le(g))
    if offs:
        for i, x in enumerate(offs):
            y = p.find("74 ?? E8", x + 7, x + 0x20)
            if y < 0:
                return 'ReadDataFolderFirst: step 2 iteration %d' % i
            p.put(y, '90 90')
        return True
    offs = p.find_all("A0 %s" % le(g))
    if not offs:
        return 'ReadDataFolderFirst: no comparisons'
    for i, x in enumerate(offs):
        y = p.find("0F 84 ?? ?? 00 00", x + 5, x + 0x20)
        if y < 0:
            return 'ReadDataFolderFirst: step 3 iteration %d' % i
        p.put(y, '90 90 90 90 90 90')
    return True


def enable_dns(p):
    va = p.string_va('211.172.247.115')
    if va < 0:
        return 'EnableDNS: IP not found'
    o = p.find("C7 05 ?? ?? ?? 00 %s" % le(va))
    if o < 0:
        return 'EnableDNS: g_accountAddr assignment missing'
    acct = le(struct.unpack_from('<I', p.d, o + 2)[0])
    head = "E8 ?? ?? ?? FF 8B C8 E8 ?? ?? ?? FF 50 B9 ?? ?? ?? ?? E8 ?? ?? ?? FF"
    o = -1
    for tail in ("A1 " + acct, "8B ?? " + acct, "8B 0D ?? ?? ?? ?? E8 ?? ?? ?? FF 8B ?? " + acct,
                 "8B 0D ?? ?? ?? ?? E8 ?? ?? ?? 00 8B ?? " + acct):
        o = p.find(head + " " + tail)
        if o >= 0:
            break
    if o < 0:
        return 'EnableDNS: step 2 pattern not found'
    rel, = struct.unpack_from('<i', p.d, o + 1)
    res_mgr = p.raw2va(o + 5) + rel
    gh = p.import_ptr('gethostbyname', 'ws2_32.dll', 52)
    wsp = p.import_ptr('wsprintfA', 'user32.dll')
    fmt = p.string_va('%d.%d.%d.%d')
    if min(gh, wsp, fmt) < 0:
        return 'EnableDNS: import or format missing (%x %x %x)' % (gh, wsp, fmt)
    text = '127.0.0.1'.encode().hex()
    tail = '00 ' + ' '.join(text[i:i + 2] for i in range(0, len(text), 2)) + ' 00' * 7

    def code(free_va, buf_va):
        return ("E8 %s 60 8B 35 %s 56 FF 15 %s 8B 48 0C 8B 11 89 D0 0F B6 48 03 51 0F B6 48 02 51 "
                "0F B6 48 01 51 0F B6 08 51 68 %s 68 %s FF 15 %s 83 C4 18 C7 05 %s %s 61 C3 %s") % (
            le(res_mgr - (free_va + 5)), acct, le(gh), le(fmt), le(buf_va), le(wsp), acct, le(buf_va), tail)

    size = len(code(0, 0).split())
    tr, tva, tvs, tro, trs = p.text
    # free tail of .text: zero bytes after the real code, up to the raw size
    start = tro + tvs
    end = tro + trs
    start = (start + 15) & ~15
    if end - start < size or any(p.d[start:start + size]):
        return 'EnableDNS: %d bytes needed, %d free in .text' % (size, end - start)
    free_va = p.raw2va(start)
    buf_va = free_va + size - 16
    p.put(start, code(free_va, buf_va))
    p.put(o + 1, le(free_va - p.raw2va(o + 5)))
    # the cave holds the output buffer, so the section must be writable
    flags_off = p.sec_off + 36
    flags, = struct.unpack_from('<I', p.d, flags_off)
    struct.pack_into('<I', p.d, flags_off, flags | 0x80000000)
    return True


def main(src, dst):
    p = PE(open(src, 'rb').read())
    ok = True
    for fn in (disable_cdguard, disable_1rag1, enable_dns, read_data_first):
        r = fn(p)
        print('%-20s %s' % (fn.__name__, 'ok' if r is True else r))
        ok &= r is True
    if not ok:
        raise SystemExit(1)
    open(dst, 'wb').write(p.d)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(*sys.argv[1:])
