# Pointing a client at your server

The server is built for one client date (`PACKETVER`, default `20190530`).
The client must be that date, or one very close to it, or the character
screen and in-game packets fail in odd ways. The steps below are for the
default build; they have not been tested against a specific client download,
so treat client-specific details (file names, tool menus) as a guide.

## 1. Get the right client

- A **full client** dated 2019-05-30, with its own `data.grf` and friends.
  The executable is usually named `Ragexe.exe` or `RagexeRE.exe`; "RE" is the
  renewal client, which matches the default `RENEWAL=ON` build. A
  `RagexeRE_2019_05_30*` executable is the target.
- Keep it in its own folder, away from any official install.

If your client is a different date, rebuild the server with that date
(see the README's build arguments). The date is compiled in.

## 2. Make the executable safe to run

Official Korean-origin clients ship with anti-cheat that refuses to run
against a private server (HackShield, nProtect GameGuard). Either:

- use an executable that is already **cleaned** (community "RagexeRE" builds
  for emulators usually are), or
- patch yours with **NEMO**, the usual client patcher for emulators: load the
  executable, tick *Disable HShield* / *Disable nProtect GameGuard*, plus
  anything your client needs for English text, then save the patched copy and
  use that.

Keep an untouched copy of the original executable.

## 3. Point the client at your server

This needs no exe patching. The client reads `data/clientinfo.xml`; a loose
file in the client's `data` folder overrides the one inside the GRF.

1. Open the client's GRF with a GRF editor and extract its
   `data/clientinfo.xml` (or use the one that came with the download).
2. Change only the server block, leaving everything else as it was:

```xml
<connection>
    <display>Family RO</display>
    <address>ro.numbawon.xyz</address>
    <port>6900</port>
    ...
</connection>
```

   Do not change `version` or `langtype` from the file's own values.
3. Save it as `data/clientinfo.xml` next to the GRFs (create the `data`
   folder if it is missing).

`ro.numbawon.xyz` resolves to the server's LAN address at home and to your
public address elsewhere. Any other host or IP your DNS gives works too.

## 4. Run it

- Run the patched executable. On modern Windows, set it to run as
  administrator and in a compatibility mode (Windows 7 or XP SP3), and turn on
  reduced colour mode if the screen is black. A DirectX wrapper such as
  dgVoodoo is the usual fix for a black or glitchy render.
- Some clients start only through their `setup.exe` or with the argument
  `1rag1`; use a shortcut ending in `Ragexe.exe 1rag1` if you see "Please run
  from the official launcher".

## 5. Create the account

Registration is on by default. At the login screen type a name ending in
`_M` (male) or `_F` (female), such as `alex_M`, with the password you want,
and press Login. The first attempt creates the account `alex`; afterwards
log in as just `alex`. Set `NEW_ACCOUNT=false` in `.env` to turn this off and
create accounts by hand.

## 6. Make an admin

Log in once, then on the server:

```sh
docker compose exec db sh -c 'mariadb -uragnarok -p"$MARIADB_PASSWORD" ragnarok \
  -e "update login set group_id=99 where userid=\"alex\""'
```

Log out and back in. Group 99 is the full admin group in `conf/groups.conf`.

## If it will not connect

| Symptom | Likely cause |
|---|---|
| "Cannot connect" at login | Router port 6900 not forwarded, or the DNS record is wrong |
| Logs in, then fails to reach the character screen | Port 6121 not forwarded, or `PUBLIC_HOST` is not what you typed in the client |
| Logs in, character screen shown, game never loads | Port 5121 not forwarded |
| Immediate disconnect or garbled characters | Client date is not the server's `PACKETVER` |
| "Rejected by server" with a valid account | Wrong server version in `clientinfo.xml` |

Watch the servers while you try: `docker compose logs -f login char map`.
