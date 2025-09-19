FROM postgis/postgis:15-3.4

USER root

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
       postgresql-15-pgvector \
    && rm -rf /var/lib/apt/lists/*

USER postgres

