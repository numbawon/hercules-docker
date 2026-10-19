# Pointing a client at your server

The server is built for one client: the plain `Ragexe.exe` from the kRO
build of **2020-02-19** (`PACKETVER=20200219`, packet family `main`). The
client you run must be that build, or the character screen and in-game
packets fail in odd ways.

## Quick install (Windows and Steam Deck)

The `client/` folder automates everything below. It downloads Gravity's
client from their own server (nothing of theirs is redistributed), applies
a patch of about a hundred bytes, drops in the stub `CDClient.dll`, writes
`clientinfo.xml` and makes a shortcut.

- **Windows:** double-click `client/install-windows.bat`. Add
  `-Server your.host.name` to the PowerShell line if you are not using
  `ro.numbawon.xyz`.
- **Steam Deck:** in Desktop Mode, quit Steam completely, then
  `python3 client/install-steamdeck.py`. It adds "Family RO" to Steam as a
  non-Steam game using Proton Experimental; Steam builds the Wine prefix on
  the first launch. In Game Mode set the controller layout to
  keyboard and mouse, the game wants both.

`client/ragexe-2020-02-19.patch` lists the byte changes (offset, old bytes,
new bytes) and checks the exe's SHA-256 before and after. It is the
output of `client/nemo_patch.py`, a headless port of the four NEMO patches
below, which you can run yourself on any `Ragexe.exe`:
`python3 client/nemo_patch.py Ragexe.exe Ragexe_patched.exe`. The
patched exe starts under Wine/Proton; the Windows installer script has not
been run on a Windows machine yet.

The manual route follows, for other client builds or if you would rather
see what is being changed.

## 1. Get the client

The full kRO client dated 2020-03-04 contains the 2020-02-19 executables.
It is listed on <http://nemo.herc.ws/downloads/>:

```
http://rofull.gnjoy.com/Ragnarok_200304.zip     (3.8 GB, plain files)
```

Unzip it into its own folder. You need these from it:

| File | Use |
|---|---|
| `Ragexe.exe` | **the one to patch and run** |
| `data.grf`, `rdata.grf` | game data |
| `CDClient.dll` | Gravity's anti-cheat; replaced in step 3 |

Ignore `RagexeRE.exe` (a different packet family), `Ragnarok.exe` (the
official launcher, which would try to log in to Gravity) and `Setup.exe`.
Keep an untouched copy of `Ragexe.exe`.

## 2. Patch the executable with NEMO

NEMO is the patcher the Hercules project uses. Its source and Windows
build are at <https://gitlab.com/4144/Nemo> (download the master zip and
run `NEMO.exe`; it needs no install). Patch lists per client are at
<http://nemo.herc.ws/>.

1. Run `NEMO.exe`, choose **Select Client** and pick a *copy* of
   `Ragexe.exe`.
2. Tick these patches, by name:

   | Patch | Why |
   |---|---|
   | **Disable Cheat Defender Game Guard** | stops the anti-cheat from refusing a private server |
   | **Copy patched Cheat Defender Game Guard** | copies a stub `CDClient.dll` next to the exe (step 3) |
   | **Disable 1rag1 type parameters** | lets the exe start directly, without the launcher's arguments |
   | **Enable DNS support for clientinfo.xml** | needed because the server address is a hostname |
   | **Read Data Folder First** | loose files in `data/` override the GRFs, so a custom `clientinfo.xml` wins |

   Optional: **Disable Multiple Windows** if you want to run two clients at
   once.
3. Choose **Apply Patch**, then save. NEMO writes the patched file to its
   `Output` folder (named like `Ragexe_<date>.exe`). Copy it into the
   client folder next to the GRFs. Name it anything; this guide calls it
   `Ragexe_patched.exe`.

If a patch is greyed out or reported as "failed", that patch does not
match this exe. Check the exe is really the 2020-02-19 build, using
the report page for it on nemo.herc.ws, rather than forcing it.

## 3. Replace the anti-cheat DLL

The patched exe still loads `CDClient.dll`. Use NEMO's drop-in
replacement, which does nothing: `Input/CDClient.dll` in the NEMO folder
overwrites the client's own. (The "Copy patched Cheat Defender Game
Guard" patch does the copy for you into NEMO's `Output` folder.)

## 4. Point the client at the server

Create `data/clientinfo.xml` in the client folder (make the `data`
folder if it does not exist; the *Read Data Folder First* patch makes it
win over the one in the GRF). Start from the file inside `data.grf`
(extract it with a GRF editor), change only the connection block, and
leave every other value alone:

```xml
<connection>
    <display>Family RO</display>
    <address>ro.numbawon.xyz</address>
    <port>6900</port>
    ...
</connection>
```

Make sure `DATA.INI` in the client folder lists the GRFs the way the
official client does (`1=rdata.grf`, `2=data.grf`).

At home `ro.numbawon.xyz` resolves to the server's LAN address; elsewhere
it is your public address.

## 5. Run it

Run `Ragexe_patched.exe`. On Windows 10/11 set it to run as
administrator and, if the screen is black, in Windows 7 compatibility
mode; a DirectX wrapper such as dgVoodoo fixes most remaining rendering
problems.

## 6. Create the account

Registration is on by default. At the login screen type a name ending in
`_M` (male) or `_F` (female), such as `alex_M`, with the password you
want, and press Login. The first attempt creates the account `alex`;
afterwards log in as just `alex`. Set `NEW_ACCOUNT=false` in `.env` to
turn this off and create accounts by hand.

## 7. Make an admin

Log in once, then on the server:

```sh
docker compose exec db sh -c 'mariadb -uragnarok -p"$MARIADB_PASSWORD" ragnarok \
  -e "update login set group_id=99 where userid=\"alex\""'
```

Log out and back in. Group 99 is the full admin group in `conf/groups.conf`.

## If it will not connect

| Symptom | Likely cause |
|---|---|
| Client closes at start or complains about the game guard | step 2 or 3 not done; the original `CDClient.dll` is still in use |
| "Cannot connect" at login | router port 6900 not forwarded, or the DNS record is wrong |
| Logs in, then fails to reach the character screen | port 6121 not forwarded, or `PUBLIC_HOST` is not what the client resolves |
| Logs in, character screen shown, game never loads | port 5121 not forwarded |
| Immediate disconnect or garbled characters | the exe is not the 2020-02-19 `Ragexe`, so it does not match `PACKETVER` |
| Address ignored, always connects to the wrong place | the DNS support patch is missing, or the loose `clientinfo.xml` is not being read |

Watch the servers while you try: `docker compose logs -f login char map`.
