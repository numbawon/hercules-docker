#!/usr/bin/env python3
"""Write the patch file the installers apply, from an original exe and a NEMO-patched one.

NEMO adds a code section, so the patched exe is longer: the file records the
changed bytes in the original's range (offset, old, new) and the appended tail.
Usage: make_patch.py Ragexe.exe Ragexe_nemo.exe ragexe-2020-02-19.patch
"""
import hashlib
import sys


def main(src, dst, out):
    a = open(src, 'rb').read()
    b = open(dst, 'rb').read()
    n = len(a)
    if len(b) < n:
        raise SystemExit('patched exe is shorter than the original')
    runs = []
    i = 0
    while i < n:
        if a[i] != b[i]:
            j = i
            while j < n and (a[j] != b[j] or (j + 8 < n and any(a[k] != b[k] for k in range(j + 1, j + 8)))):
                j += 1
            runs.append((i, a[i:j], b[i:j]))
            i = j
        else:
            i += 1
    lines = ['# Hercules client patch for kRO Ragexe.exe (2020-02-19 build, Ragnarok_200304.zip)',
             '# offset(hex) old-bytes new-bytes; then the bytes appended to the file; made by make_patch.py',
             'source-sha256 ' + hashlib.sha256(a).hexdigest(),
             'result-sha256 ' + hashlib.sha256(b).hexdigest()]
    lines += ['%x %s %s' % (o, x.hex(), y.hex()) for o, x, y in runs]
    if len(b) > n:
        lines.append('append ' + b[n:].hex())
    open(out, 'w').write('\n'.join(lines) + '\n')
    print(len(runs), 'runs,', len(b) - n, 'bytes appended')


if __name__ == '__main__':
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    main(*sys.argv[1:])
