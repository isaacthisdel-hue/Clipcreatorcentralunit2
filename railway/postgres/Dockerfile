# Postgres for Railway, pre-loaded with the app's schema (init.sql).
# Build context is the repo root; Railway uses this file via RAILWAY_DOCKERFILE_PATH.
FROM postgres:15-alpine
COPY init.sql /docker-entrypoint-initdb.d/init.sql
# Railway volumes contain lost+found, so keep the data in a subfolder.
ENV PGDATA=/var/lib/postgresql/data/pgdata
