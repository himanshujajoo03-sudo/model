FROM postgis/postgis:15-3.4

# Install pgvector extension alongside PostGIS.
# Acquire::Check-Valid-Until=false bypasses expired InRelease timestamp on Debian Bullseye mirrors.
RUN apt-get -o Acquire::Check-Valid-Until=false update \
    && apt-get install -y --no-install-recommends \
       postgresql-15-pgvector \
    && rm -rf /var/lib/apt/lists/*
