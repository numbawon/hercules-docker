#!/bin/sh
# Writes FluxCP's config from the environment on every start (from pristine
# copies), so a changed .env takes effect on restart.
set -e
php /usr/local/bin/render-config.php
chown www-data:www-data /var/www/html/config/application.php /var/www/html/config/servers.php
chmod 640 /var/www/html/config/application.php /var/www/html/config/servers.php
exec docker-php-entrypoint "$@"
