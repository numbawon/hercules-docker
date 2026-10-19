# FluxCP, the web control panel for Hercules (github.com/HerculesWS/FluxCP,
# LGPL-3.0): account registration, password changes, character and item
# lookup, and an admin section for group 99 accounts. Built from a pinned
# commit so a rebuild is repeatable.
FROM php:8.3-apache

ARG FLUXCP_REF=24e4cd3133c1789a0fbd3df626684b49ccae0901

RUN apt-get update \
 && apt-get install -y --no-install-recommends libpng-dev libjpeg-dev libfreetype6-dev curl ca-certificates \
 && docker-php-ext-configure gd --with-freetype --with-jpeg \
 && docker-php-ext-install -j"$(nproc)" gd pdo_mysql mysqli \
 && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL "https://github.com/HerculesWS/FluxCP/archive/${FLUXCP_REF}.tar.gz" \
  | tar -xz --strip-components=1 -C /var/www/html \
 && cp -r /var/www/html/config /opt/fluxcp-config-dist

# Behind a TLS-terminating proxy: tell PHP the request was HTTPS so FluxCP
# builds https links.
RUN printf 'SetEnvIf X-Forwarded-Proto https HTTPS=on\n' > /etc/apache2/conf-available/proxy-https.conf \
 && a2enconf proxy-https

COPY docker-entrypoint.sh render-config.php /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh \
 && chown -R www-data:www-data /var/www/html

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["apache2-foreground"]
