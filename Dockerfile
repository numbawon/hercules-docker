# Hercules (Ragnarok Online server emulator), built from source.
#
# PACKETVER and RENEWAL are compile-time: they must match the client the
# players run, so they are build arguments, not runtime settings.
FROM debian:bookworm-slim AS build
ARG HERCULES_REF=v2026.09
ARG PACKETVER=20200219
ARG RENEWAL=ON
# Which family of client executable the players run. Hercules uses different
# packet layouts for them: main (plain Ragexe, the default), RE (RagexeRE),
# zero, sak or ad.
ARG PACKETTYPE=main
# Upstream pulls its C dependencies (cJSON, MariaDB connector, PCRE, zlib,
# giflib) through Conan, wired in by cmake_modules/conan_provider.cmake.
RUN apt-get update && apt-get install -y --no-install-recommends \
      git ca-certificates build-essential cmake ninja-build pkg-config \
      python3 python3-pip python3-venv \
 && rm -rf /var/lib/apt/lists/* \
 && python3 -m venv /opt/conan && /opt/conan/bin/pip install --no-cache-dir conan
ENV PATH=/opt/conan/bin:$PATH
RUN conan profile detect
RUN git clone --depth 1 --branch "${HERCULES_REF}" https://github.com/HerculesWS/Hercules.git /src
WORKDIR /src
RUN set -e; \
    case "${PACKETTYPE}" in \
      main) TYPE_FLAG="" ;; \
      RE|zero|sak|ad) TYPE_FLAG="-DENABLE_PACKETVER_$(echo ${PACKETTYPE} | tr a-z A-Z)=ON" ;; \
      *) echo "PACKETTYPE must be main, RE, zero, sak or ad" >&2; exit 1 ;; \
    esac; \
    cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_PROJECT_TOP_LEVEL_INCLUDES=cmake_modules/conan_provider.cmake \
      -DPACKETVER=${PACKETVER} -DENABLE_RENEWAL=${RENEWAL} -DENABLE_LIBBACKTRACE=OFF \
      ${TYPE_FLAG}; \
    cmake --build build
RUN mkdir -p /out && cp -a build/src/login/login-server build/src/char/char-server \
      build/src/map/map-server build/src/api/api-server /out/ \
 && cp -a build/runtime-lib /out/runtime-lib

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
      libstdc++6 libssl3 ca-certificates mariadb-client netcat-openbsd \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --system --home-dir /opt/hercules --shell /usr/sbin/nologin hercules
COPY --from=build /out/runtime-lib/ /usr/local/lib/hercules/
RUN echo /usr/local/lib/hercules > /etc/ld.so.conf.d/hercules.conf && ldconfig
WORKDIR /opt/hercules
COPY --from=build /out/login-server /out/char-server /out/map-server /out/api-server ./
COPY --from=build /src/conf ./conf
COPY --from=build /src/db ./db
COPY --from=build /src/npc ./npc
COPY --from=build /src/maps ./maps
COPY --from=build /src/sql-files ./sql-files
COPY --from=build /src/LICENSE ./LICENSE
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN mkdir -p log save conf/import db/import \
 && chmod +x /usr/local/bin/docker-entrypoint.sh \
 && chown -R hercules:hercules /opt/hercules
ENV MARIADB_PLUGIN_DIR=/usr/local/lib/hercules/plugin
USER hercules
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["map-server"]
