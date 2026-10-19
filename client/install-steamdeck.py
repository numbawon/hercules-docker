#!/usr/bin/env python3
"""Family RO client installer for the Steam Deck (or any Linux with Steam).

Downloads Gravity's own kRO full client, applies the small exe patch beside
this script, drops in the do-nothing CDClient.dll, writes clientinfo.xml, then
adds "Family RO" to Steam as a non-Steam game that runs under Proton. Steam
creates the Wine prefix the first time you launch it.

Run it in Desktop Mode, with Steam closed (it edits Steam's shortcut list):
    python3 install-steamdeck.py [--dir ~/Games/FamilyRO] [--server ro.example.com]
                                 [--proton proton_experimental]
"""
import argparse
import binascii
import glob
import hashlib
import os
import shutil
import struct
import subprocess
import sys
import zipfile

ZIP_URL = 'http://rofull.gnjoy.com/Ragnarok_200304.zip'
ZIP_SHA256 = 'a00bd56f591c097ad84567128a6a2ccadc2ea98dbec7fa58b3a6c5fa94b8d092'
HERE = os.path.dirname(os.path.abspath(__file__))


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def apply_patch(src, dst, patch_file):
    lines = [l.split() for l in open(patch_file) if l.strip() and not l.startswith('#')]
    want_src = next(l[1] for l in lines if l[0] == 'source-sha256')
    want_dst = next(l[1] for l in lines if l[0] == 'result-sha256')
    if sha256(src) != want_src:
        sys.exit('Ragexe.exe is not the 2020-02-19 build this patch is for')
    data = bytearray(open(src, 'rb').read())
    for l in lines:
        if l[0].endswith('-sha256'):
            continue
        off, old, new = int(l[0], 16), bytes.fromhex(l[1]), bytes.fromhex(l[2])
        if data[off:off + len(old)] != old:
            sys.exit('unexpected byte at 0x%x' % off)
        data[off:off + len(new)] = new
    open(dst, 'wb').write(data)
    if sha256(dst) != want_dst:
        sys.exit('patched exe does not match the expected result')


# --- Steam's binary shortcuts.vdf ------------------------------------------

def vdf_str(k, v):
    return b'\x01' + k.encode() + b'\0' + v.encode() + b'\0'


def vdf_int(k, v):
    return b'\x02' + k.encode() + b'\0' + struct.pack('<I', v & 0xffffffff)


def shortcut_entry(index, appid, name, exe, start_dir, launch_opts):
    body = (vdf_int('appid', appid) + vdf_str('AppName', name) + vdf_str('Exe', exe)
            + vdf_str('StartDir', start_dir) + vdf_str('icon', '') + vdf_str('ShortcutPath', '')
            + vdf_str('LaunchOptions', launch_opts) + vdf_int('IsHidden', 0)
            + vdf_int('AllowDesktopConfig', 1) + vdf_int('AllowOverlay', 1)
            + vdf_int('OpenVR', 0) + vdf_int('Devkit', 0) + vdf_str('DevkitGameID', '')
            + vdf_int('DevkitOverrideAppID', 0) + vdf_int('LastPlayTime', 0)
            + vdf_str('FlatpakAppID', '') + b'\x00tags\x00\x08')
    return b'\x00' + str(index).encode() + b'\0' + body + b'\x08'


def read_shortcuts(path):
    """Return the raw entries already present (each as bytes) so they are kept as they were."""
    if not os.path.exists(path):
        return []
    data = open(path, 'rb').read()
    head = b'\x00shortcuts\x00'
    if not data.startswith(head) or not data.endswith(b'\x08\x08'):
        sys.exit('unfamiliar shortcuts.vdf layout, not touching it: ' + path)
    body = data[len(head):-2]
    entries, pos = [], 0
    while pos < len(body):
        # an entry is \0 index \0 ... ended by a \x08 at nesting depth 0
        start, depth = pos, 0
        assert body[pos] == 0
        pos = body.index(b'\0', pos + 1) + 1
        while True:
            t = body[pos]
            pos += 1
            if t == 8:
                if depth == 0:
                    break
                depth -= 1
                continue
            end = body.index(b'\0', pos)
            pos = end + 1
            if t == 0:
                depth += 1
            elif t == 1:
                pos = body.index(b'\0', pos) + 1
            elif t == 2:
                pos += 4
            else:
                sys.exit('unknown VDF type %d' % t)
        entries.append(body[start:pos])
    return entries


def add_shortcut(vdf_path, name, exe, start_dir):
    appid = (binascii.crc32((f'"{exe}"' + name).encode()) | 0x80000000) & 0xffffffff
    entries = read_shortcuts(vdf_path)
    for e in entries:
        if b'\x01AppName\0' + name.encode() + b'\0' in e:
            print('Steam already has a "%s" shortcut, leaving it' % name)
            return appid
    if os.path.exists(vdf_path):
        shutil.copy(vdf_path, vdf_path + '.bak-familyro')
    entries.append(shortcut_entry(len(entries), appid, name, f'"{exe}"', f'"{start_dir}"', ''))
    # re-number so indexes stay 0..n-1
    fixed = []
    for i, e in enumerate(entries):
        rest = e[e.index(b'\0', 1) + 1:]
        fixed.append(b'\x00' + str(i).encode() + b'\0' + rest)
    os.makedirs(os.path.dirname(vdf_path), exist_ok=True)
    open(vdf_path, 'wb').write(b'\x00shortcuts\x00' + b''.join(fixed) + b'\x08\x08')
    return appid


def set_compat_tool(config_vdf, appid, tool):
    text = open(config_vdf).read()
    if f'"{appid}"' in text.split('"CompatToolMapping"', 1)[-1][:200000]:
        print('compat tool already set for this shortcut, leaving it')
        return
    block = f'\t\t\t\t\t"{appid}"\n\t\t\t\t\t{{\n\t\t\t\t\t\t"name"\t\t"{tool}"\n\t\t\t\t\t\t"config"\t\t""\n\t\t\t\t\t\t"priority"\t\t"250"\n\t\t\t\t\t}}\n'
    key = '"CompatToolMapping"'
    i = text.find(key)
    if i < 0:
        sys.exit('no CompatToolMapping in config.vdf; set Proton by hand (Properties > Compatibility)')
    j = text.index('{', i) + 1
    shutil.copy(config_vdf, config_vdf + '.bak-familyro')
    open(config_vdf, 'w').write(text[:j] + '\n' + block.rstrip('\n') + text[j:])


def steam_root():
    for p in ('~/.local/share/Steam', '~/.steam/steam'):
        p = os.path.expanduser(p)
        if os.path.isdir(os.path.join(p, 'userdata')):
            return os.path.realpath(p)
    sys.exit('Steam folder not found; start Steam once first')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--dir', default='~/Games/FamilyRO')
    ap.add_argument('--server', default='ro.numbawon.xyz')
    ap.add_argument('--proton', default='proton_experimental')
    a = ap.parse_args()
    d = os.path.expanduser(a.dir)

    if subprocess.run(['pgrep', '-x', 'steam'], capture_output=True).returncode == 0:
        sys.exit('Steam is running. Quit it completely (Steam menu > Exit), then run this again.')

    os.makedirs(d, exist_ok=True)
    zp = os.path.join(d, 'Ragnarok_200304.zip')
    if not (os.path.exists(zp) and sha256(zp) == ZIP_SHA256):
        print('Downloading the client (3.8 GB)...')
        subprocess.run(['curl', '-L', '-C', '-', '--fail', '-o', zp, ZIP_URL], check=True)
    if sha256(zp) != ZIP_SHA256:
        sys.exit('the downloaded client does not match the expected build, stopping')
    if not os.path.exists(os.path.join(d, 'Ragexe.exe')):
        print('Unpacking...')
        zipfile.ZipFile(zp).extractall(d)

    exe = os.path.join(d, 'Ragexe_patched.exe')
    apply_patch(os.path.join(d, 'Ragexe.exe'), exe, os.path.join(HERE, 'ragexe-2020-02-19.patch'))
    shutil.copy(os.path.join(HERE, 'CDClient.dll'), d)
    shutil.copy(os.path.join(HERE, 'DATA.INI'), d)
    os.makedirs(os.path.join(d, 'data'), exist_ok=True)
    info = open(os.path.join(HERE, 'clientinfo.xml')).read().replace('ro.numbawon.xyz', a.server)
    open(os.path.join(d, 'data', 'clientinfo.xml'), 'w').write(info)

    root = steam_root()
    users = [u for u in glob.glob(os.path.join(root, 'userdata', '*')) if os.path.basename(u).isdigit()]
    if not users:
        sys.exit('no Steam user found; log in to Steam once first')
    for u in users:
        appid = add_shortcut(os.path.join(u, 'config', 'shortcuts.vdf'), 'Family RO', exe, d)
    set_compat_tool(os.path.join(root, 'config', 'config.vdf'), appid, a.proton)
    print('\nDone. Start Steam, find "Family RO" under Non-Steam games in your Library, and Play.')
    print('The first launch builds the Wine prefix and takes a minute. To register, log in as')
    print('yourname_M or yourname_F (any password) the first time.')


if __name__ == '__main__':
    main()
