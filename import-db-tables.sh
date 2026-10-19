#!/bin/sh
# Loads Hercules' item and monster tables into MariaDB for the web panel.
# The game server reads db/*.conf and does not need them; FluxCP's item,
# monster and character pages do. Safe to rerun (each file drops and
# recreates its table), and worth rerunning after a Hercules upgrade.
#   ./import-db-tables.sh
set -e
cd "$(dirname "$0")"
export COMPOSE_IGNORE_ORPHANS=true
renewal=$(sed -n 's/^RENEWAL=//p' .env 2>/dev/null | tail -1)
if [ "${renewal:-ON}" = "ON" ]; then
    files="item_db_re.sql item_db2.sql mob_db_re.sql mob_db2.sql mob_skill_db_re.sql mob_skill_db2.sql"
else
    files="item_db.sql item_db2.sql mob_db.sql mob_db2.sql mob_skill_db.sql mob_skill_db2.sql"
fi
for f in $files; do
    printf '%s ... ' "$f"
    docker compose run --rm -T --no-deps --entrypoint cat login "/opt/hercules/sql-files/$f" |
        docker compose exec -T db sh -c 'mariadb -u"$MARIADB_USER" -p"$MARIADB_PASSWORD" "$MARIADB_DATABASE"'
    echo ok
done
