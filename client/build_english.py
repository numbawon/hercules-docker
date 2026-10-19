#!/usr/bin/env python3
"""Lay the ROenglishRE translation (github.com/llchrisll/ROenglishRE) over a kRO client folder.

The project is written for clients run under a non-Korean Windows, with its
own System folder name ("SystemEN") selected by an exe patch. This script does
the same thing without that patch: the SystemEN files go into System under the
names the 2020-02-19 exe loads, and the Lua paths inside them are rewritten.
Loose files go in data/ (the "Read Data Folder First" patch makes them win).
Korean folder names in the repo are Korean bytes read as Latin-1, which is what
the client asks the OS for under a non-Korean locale, so they are copied as is
(re-encoded to UTF-8 on Linux so Wine sees the same names).

Usage: build_english.py <ROenglishRE checkout> <client folder>
"""
import os
import shutil
import sys

# compatibility layers up to the client date, in the project's own order
DATES = ['2017-06-14', '2017-12-13', '2018-06-20', '2019-06-05', '2020-01-22']
# The project's Lua tables are written for newer clients and index into constant
# tables (job, skill and status ids) that this older exe's own files do not fully
# define, which fails with "table index is nil". Missing constants get harmless
# unique negative ids instead.
PRELUDE = (b'do local n=0 for _,k in ipairs({"jobtbl","SKID","JOBID","EFST_IDs","EnumVAR","PetAccIDs"}) do '
           b'local t=rawget(_G,k) if type(t)=="table" then local m=getmetatable(t) '
           b'if not (m and m.__metatable) then local old=m and m.__index '
           b'setmetatable(t,{__index=function(tt,key) local v if type(old)=="function" then v=old(tt,key) '
           b'elseif type(old)=="table" then v=old[key] end if v==nil then n=n-1 v=n end return v end}) end end end end\n')
SHIMMED = ('datainfo', 'skillinfoz', 'stateicon')
# needs files this client does not ship, so it stays Korean
SKIPPED = ('worldviewdata', 'datainfo/addrandomoptionnametable.lub')
# SystemEN file -> the name the 2020-02-19 exe loads from System/
# The exe picks the "true" or the "Sak" (Sakray) variant by the servertype in
# clientinfo.xml and by which NEMO patches are on, so each table is written
# under both names.
RENAMES = {
    'itemInfo.lua': ['itemInfo_true.lub', 'itemInfo_Sak.lub'],
    'mapInfo.lub': ['mapInfo_true.lub', 'mapInfo_sak.lub'],
    'Towninfo.lub': ['Towninfo.lub'],
    'achievements.lub': ['achievement_list.lub'],
    'OngoingQuests.lub': ['OngoingQuestInfoList_True.lub', 'OngoingQuestInfoList_Sakray.lub', 'OngoingQuestInfoList.lub'],
    'RecommendedQuests.lub': ['RecommendedQuestInfoList_True.lub', 'RecommendedQuestInfoList_Sakray.lub', 'RecommendedQuestInfoList.lub'],
}


def fsname(name):
    """Linux: Korean bytes seen as Latin-1 by Wine become the UTF-8 name Wine will ask for."""
    if os.name == 'nt':
        return name
    raw = os.fsencode(name)
    try:
        raw.decode('utf-8')
        return name
    except UnicodeDecodeError:
        return raw.decode('cp1252', errors='replace') if b'\x81' not in raw else raw.decode('latin-1')


def overlay(src, dst):
    for root, dirs, files in os.walk(os.fsencode(src)):
        rel = os.path.relpath(root, os.fsencode(src))
        parts = [] if rel == b'.' else [fsname(os.fsdecode(p)) for p in rel.split(os.fsencode(os.sep))]
        out = os.path.join(dst, *parts)
        os.makedirs(out, exist_ok=True)
        for f in files:
            shutil.copyfile(os.path.join(root, f), os.path.join(out, fsname(os.fsdecode(f))))


def main(repo, client):
    tr = os.path.join(repo, 'Translation')
    stage = os.path.join(client, '.en-stage')
    shutil.rmtree(stage, ignore_errors=True)
    os.makedirs(stage)
    for src in [os.path.join(tr, 'Renewal')] + [
            p for d in DATES for p in (
                os.path.join(tr, 'Compatibility', d, 'Renewal'),
                os.path.join(tr, 'Compatibility', d)) if os.path.isdir(p)
            and not (p.endswith(d) and os.path.isdir(os.path.join(p, 'Renewal')))]:
        overlay(src, stage)
    # data/: everything except the project's example clientinfo.xml
    sd = os.path.join(stage, 'data')
    os.makedirs(os.path.join(client, 'data'), exist_ok=True)
    keep = os.path.join(client, 'data', 'clientinfo.xml')
    mine = open(keep, 'rb').read() if os.path.exists(keep) else None
    os.path.exists(os.path.join(sd, 'clientinfo.xml')) and os.remove(os.path.join(sd, 'clientinfo.xml'))
    for d in SKIPPED:
        t = os.path.join(sd, 'luafiles514', 'lua files', d)
        shutil.rmtree(t, ignore_errors=True) if os.path.isdir(t) else os.path.isfile(t) and os.remove(t)
    shutil.rmtree(os.path.join(client, 'data', 'luafiles514'), ignore_errors=True)
    overlay(sd, os.path.join(client, 'data'))
    lf = os.path.join(client, 'data', 'luafiles514', 'lua files')
    for d in SHIMMED:
        for root, _, files in os.walk(os.path.join(lf, d)):
            for f in files:
                if f.lower().endswith('.lub') and f.lower() != 'skillid.lub':
                    p = os.path.join(root, f)
                    body = open(p, 'rb').read()
                    open(p, 'wb').write(PRELUDE + body)
    if mine is not None:
        open(keep, 'wb').write(mine)
    # System/: translated tables and the item info loader
    se = os.path.join(stage, 'SystemEN')
    system = os.path.join(client, 'System')
    os.makedirs(system, exist_ok=True)
    for f in os.listdir(se):
        p = os.path.join(se, f)
        if f in RENAMES and os.path.isfile(p):
            for target in RENAMES[f]:
                shutil.copyfile(p, os.path.join(system, target))
        elif os.path.isfile(p) and f.endswith(('.lua', '.lub')):
            shutil.copyfile(p, os.path.join(system, f))
    os.makedirs(os.path.join(system, 'LuaFiles514'), exist_ok=True)
    for f in os.listdir(os.path.join(se, 'LuaFiles514')):
        shutil.copyfile(os.path.join(se, 'LuaFiles514', f), os.path.join(system, 'LuaFiles514', f))
    # the project's Lua files load each other as "SystemEN/..."; here that folder is System
    for base in (system, os.path.join(client, 'data')):
        for root, _, files in os.walk(base):
            for f in files:
                p = os.path.join(root, f)
                if f.lower().endswith(('.lua', '.lub')):
                    t = open(p, 'rb').read()
                    if b'SystemEN' in t:
                        open(p, 'wb').write(t.replace(b'SystemEN', b'System'))
    shutil.rmtree(stage)
    print('translation laid over', client)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(*sys.argv[1:])
