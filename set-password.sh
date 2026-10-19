#!/bin/sh
# Change a player's password without it touching the shell history or any log.
#   ./set-password.sh <account>        (run from the folder with compose.yml)
# Hercules stores passwords as typed (use_MD5_passwords is off by default), at
# most 23 characters, and the client sends them as typed, so this is a plain
# column update. Takes effect at the next login.
set -e
[ -n "$1" ] || { echo "usage: $0 <account>"; exit 1; }
printf 'New password for %s: ' "$1"
stty -echo; read -r pw; stty echo; echo
printf 'Again: '
stty -echo; read -r pw2; stty echo; echo
[ "$pw" = "$pw2" ] || { echo "passwords differ"; exit 1; }
[ "${#pw}" -ge 4 ] && [ "${#pw}" -le 23 ] || { echo "use 4 to 23 characters"; exit 1; }
hex=$(printf %s "$pw" | od -An -tx1 | tr -d ' \n')
uhex=$(printf %s "$1" | od -An -tx1 | tr -d ' \n')
echo "update login set user_pass=UNHEX('$hex') where userid=CAST(UNHEX('$uhex') AS CHAR) and sex<>'S'; select row_count() as accounts_changed;" |
    docker compose exec -T db sh -c 'mariadb -u"$MARIADB_USER" -p"$MARIADB_PASSWORD" "$MARIADB_DATABASE"'
