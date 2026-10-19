# hercules-docker

A Docker build of the [Hercules](https://github.com/HerculesWS/Hercules)
Ragnarok Online server emulator: one image, run three or four times (login,
char, map, optionally api), plus MariaDB in the supplied compose file.

Hercules publishes no container image of its own. This builds a pinned
release from source on `debian:bookworm-slim`.

## Quick start

```sh
cp .env.example .env     # set PUBLIC_HOST and both passwords
docker compose up -d --build
docker compose logs -f map
```

The first start creates the database and replaces Hercules' well-known
inter-server account (`s1` / `p1`) with the password from `.env`. The image
refuses to start with an `INTER_PASSWORD` longer than 23 characters, because
Hercules silently truncates longer ones and the servers then fail to log in.

Ports to open: **6900** (login), **6121** (char), **5121** (map), all TCP.
Keep the database port closed; it is not published.

## Prebuilt image

`numbawon/hercules` on Docker Hub is built with the defaults below
(`v2026.09-pv20200219`, also `latest`). Use it with
`HERCULES_IMAGE=numbawon/hercules:latest docker compose up -d`. If your client
is a different date, or you want pre-renewal rules, build your own with the
arguments below: the client date is compiled in and cannot be changed at run
time.

## Build arguments

`PACKETVER` and `RENEWAL` are compiled in and must match the client players
run. Change them in `.env` and rebuild (`docker compose build --no-cache`).

| Argument | Default | Meaning |
|---|---|---|
| `HERCULES_REF` | `v2026.09` | Upstream git tag or branch |
| `PACKETVER` | `20200219` | Client date, `YYYYMMDD` |
| `RENEWAL` | `ON` | `ON` renewal rules, `OFF` pre-renewal |

## Configuration

Environment variables become Hercules' `conf/import/*.conf` overrides on
every start, so config lives in `.env`, not in the image:

| Variable | Default | Meaning |
|---|---|---|
| `PUBLIC_HOST` | required | Address clients are told to connect to |
| `DB_PASSWORD` | required | MariaDB password |
| `INTER_PASSWORD` | required | Login/char/map shared secret, 23 chars max |
| `NEW_ACCOUNT` | `true` | Players register by logging in as `name_M` / `name_F` |

Custom NPC scripts go in `./custom-npc` (mounted at `npc/custom`).

## What is not included

Game clients and data files. Players need a client matching `PACKETVER`,
patched to point at your server: see [docs/CLIENT.md](docs/CLIENT.md).

The web/API server is built into the image (`command: api-server`) but not
in the compose file, since only newer clients use it.

## Web panel (optional)

[FluxCP](https://github.com/HerculesWS/FluxCP) (the Hercules web control
panel: account registration, password changes, character and item lookup,
admin pages for group 99 accounts) is built from a pinned commit by
`fluxcp/` and added with an override file:

```
docker compose -f compose.yml -f compose.panel.yml up -d --build fluxcp
```

Set `FLUXCP_HOST` and `FLUXCP_INSTALLER_PASSWORD` in `.env` first. The
container publishes no port; it joins an existing overlay or bridge network
(`EDGE_NETWORK`, default `edge`) so a reverse proxy can reach
`http://fluxcp:80`. Put an authenticating proxy in front of it. On first run
open `/?module=install`, enter the installer password and run "Install or
Update Everything" to create the `cp_*` tables. The config is generated from
the environment on every start (`fluxcp/render-config.php`), with
`UseMD5` off to match this server's plain stored passwords.

Then run `./import-db-tables.sh` once: it loads the item and monster tables
(`item_db`, `mob_db` and friends) from the image into MariaDB. The game server
does not need them, but FluxCP's account, character, item and monster pages
fail without them.

`./set-password.sh <account>` changes a player's password from the shell
without the value ending up in history or logs.

## License

The build files in this repository are MIT licensed (`LICENSE`). Hercules itself
is GPL v3 or later, and the image contains its compiled binaries and its own
license file. Ragnarok Online is a trademark of its owners, and this project is
not affiliated with them.
