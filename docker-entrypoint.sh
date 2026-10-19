#!/bin/sh
# Renders Hercules' config from environment variables, creates the database
# on first start, then runs one server: login-server, char-server,
# map-server or api-server.
#
# Everything is written under conf/import/ (Hercules' own override
# directory) except the shared database connection file.
set -eu

: "${DB_HOST:=db}" "${DB_PORT:=3306}" "${DB_NAME:=ragnarok}"
: "${DB_USER:=ragnarok}" "${DB_PASSWORD:?DB_PASSWORD is required}"
: "${INTER_USER:=s1}" "${INTER_PASSWORD:?INTER_PASSWORD is required}"
: "${LOGIN_HOST:=login}" "${CHAR_HOST:=char}"
: "${PUBLIC_HOST:?PUBLIC_HOST is required (address players connect to)}"
: "${NEW_ACCOUNT:=true}"

# Hercules keeps usernames and passwords in 24-byte buffers (23 usable); a
# longer inter-server password is silently cut and then never matches.
[ "${#INTER_PASSWORD}" -le 23 ] || { echo "INTER_PASSWORD must be 23 characters or fewer" >&2; exit 1; }

cd /opt/hercules

cat > conf/global/sql_connection.conf <<CONF
sql_connection: {
	db_hostname: "$DB_HOST"
	db_port: $DB_PORT
	db_username: "$DB_USER"
	db_password: "$DB_PASSWORD"
	db_database: "$DB_NAME"
}
CONF

cat > conf/import/login-server.conf <<CONF
login_configuration: {
	account: {
		new_account: $NEW_ACCOUNT
	}
}
CONF

cat > conf/import/char-server.conf <<CONF
char_configuration: {
	inter: {
		userid: "$INTER_USER"
		passwd: "$INTER_PASSWORD"
		login_ip: "$LOGIN_HOST"
		char_ip: "$PUBLIC_HOST"
	}
}
CONF

cat > conf/import/map-server.conf <<CONF
map_configuration: {
	inter: {
		userid: "$INTER_USER"
		passwd: "$INTER_PASSWORD"
		char_ip: "$CHAR_HOST"
		map_ip: "$PUBLIC_HOST"
	}
}
CONF

SQL="mariadb --skip-ssl -h$DB_HOST -P$DB_PORT -u$DB_USER $DB_NAME"
export MYSQL_PWD="$DB_PASSWORD"

if [ "$1" = login-server ]; then
	i=0
	until $SQL -e 'select 1' >/dev/null 2>&1; do
		i=$((i + 1)); [ "$i" -gt 60 ] && { echo "database never came up" >&2; exit 1; }
		sleep 2
	done
	if ! $SQL -e 'select 1 from login limit 1' >/dev/null 2>&1; then
		echo "first start: creating tables"
		$SQL < sql-files/main.sql
		$SQL < sql-files/logs.sql
	fi
	# main.sql ships a well-known inter-server account (s1 / p1). Replace it
	# with ours so the default credentials never work.
	$SQL -e "update login set userid='$INTER_USER', user_pass='$INTER_PASSWORD' where account_id=1 and sex='S'"
fi

exec "./$1"
