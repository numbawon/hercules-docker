#!/usr/bin/env python3
"""Write NEMO profiles (patch list plus saved inputs) for the 2020-02-19 client.

NEMO's Save Profile / Load Profile use two files side by side: <name>.log,
the selected patches as "<id> <name>" lines, and <name>_inputs.db, the values
typed into the patches' parameter boxes, as a Qt QDataStream of
(name, QByteArray, QVariant) records. This writes both, so a font size can be
tried by loading a profile instead of ticking about forty boxes.

The patch set is the one that produced the working English exe (Ragexe_nemo.exe)
plus the font patches. Usage:

    make_nemo_profile.py OUTDIR            # the default set of profiles
    make_nemo_profile.py --check FILE.db   # decode one, for comparison
"""
import struct
import sys
from pathlib import Path

# The patches behind the known-good Ragexe_nemo.exe (login via our server,
# English tables, data folder read first, stub Cheat Defender). Do not add
# "Restore Login Window": it fails on this exe and is not needed.
BASE = [
    (9, "Disable 1rag1 type parameters"),
    (14, "Disable Hallucination Wavy Screen"),
    (23, "Enable /who command"),
    (24, "Fix Camera Angles"),
    (34, "Enable /showname"),
    (35, "Read Data Folder First"),
    (36, "Always read msgstringtable.txt"),
    (38, "Remove Gravity Ads"),
    (39, "Remove Gravity Logo"),
    (41, "Disable Nagle Algorithm"),
    (44, "Translate Client"),
    (46, "Use Normal Guild Brackets"),
    (48, "Use Plain Text Descriptions"),
    (49, "Enable Multiple GRFs"),
    (53, "Use Ascii on All LangTypes"),
    (64, "@ Bug Fix"),
    (65, "Load Custom lua file instead of iteminfo*.lub"),
    (73, "Remove Hourly Announce"),
    (84, "Remove Serial Display"),
    (90, "Enable DNS Support"),
    (213, "Disable Help Message on Login"),
    (230, "Always load Korea ExternalSettings lua file"),
    (231, "Remove hardcoded address/port"),
    (232, "Restore old login packet"),
    (244, "Disable Cheat Defender Game Guard"),
    (284, "Copy patched Cheat Defender Game Guard"),
    (290, "Hide build info in client"),
    (291, "Hide packets from peek"),
    (326, "Disable OTP Login Packet"),
    (335, "Fix HTTP Emblems in clients"),
    (338, "Additional client validation"),
    (348, "Send client flags to server"),
    (362, "Fixes the Korean Job name issue with LangType"),
    (404, "Use borderless mode in full screen"),
    (427, "Check is servertype in xml file was set to correct value"),
]
FONT_SIZE = (391, "Adjust all fonts logical size")
FONT_FACE = (397, "Change all fonts face")


def qstring(s):
    b = s.encode("utf-16-be")
    return struct.pack(">I", len(b)) + b


def int_record(name, value):
    return (qstring(name) + struct.pack(">I", 4) + struct.pack("<i", value)
            + struct.pack(">IBi", 2, 0, value))


def str_record(name, value, nul):
    raw = value.encode() + (b"\0" if nul else b"")
    return (qstring(name) + struct.pack(">I", len(raw)) + raw
            + struct.pack(">IB", 10, 0) + qstring(value))


def inputs(size, face):
    recs = [str_record("$dataINI", "DATA.INI", True),
            str_record("$newItemInfo", "System/iteminfo_Sak.lub", True),
            int_record("$newFontSizeAdjL", size)]
    if face:
        recs.append(str_record("$newFont", face, False))
    return b"".join(recs)


def write(out, name, size, face=None):
    patches = BASE + [FONT_SIZE] + ([FONT_FACE] if face else [])
    patches.sort()
    (out / (name + ".log")).write_text(
        "".join("%d %s\n" % p for p in patches))
    (out / (name + "_inputs.db")).write_bytes(inputs(size, face))


def decode(data):
    pos, rec = 0, []
    u32 = lambda i: int.from_bytes(data[i:i + 4], "big")
    while pos < len(data):
        n = u32(pos)
        name = data[pos + 4:pos + 4 + n].decode("utf-16-be")
        nxt = pos + 4 + n
        j = nxt
        while j < len(data) and not (data[j + 4:j + 6] == b"\0$"
                                     and 0 < u32(j) < 200 and u32(j) % 2 == 0):
            j += 1
        rec.append((name, data[nxt:j]))
        pos = j
    return rec


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--check":
        for n, p in decode(Path(sys.argv[2]).read_bytes()):
            print(n, p.hex(" "))
    elif len(sys.argv) == 2:
        out = Path(sys.argv[1])
        out.mkdir(parents=True, exist_ok=True)
        for size in (3, 4, 5, 6):
            write(out, "font%d" % size, size)
        write(out, "font4-arial", 4, "Arial")
        write(out, "font6-arial", 6, "Arial")
        # A wide, coding-style face: expect to need a smaller size than Arial.
        for size in (2, 3, 4):
            write(out, "font%d-caskaydia" % size, size, "CaskaydiaCove NF")
        print("wrote profiles to", out)
    else:
        sys.exit(__doc__)
