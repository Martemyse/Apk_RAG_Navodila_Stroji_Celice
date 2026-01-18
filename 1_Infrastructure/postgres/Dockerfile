FROM postgres:16

# Install build dependencies
RUN apt-get update && \
    apt-get install -y \
      build-essential \
      git \
      postgresql-server-dev-16 \
      curl \
      ca-certificates \
      gnupg \
      lsb-release && \
    rm -rf /var/lib/apt/lists/*

# Add PostgreSQL APT repository for pg_cron
RUN curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /usr/share/keyrings/postgresql-keyring.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/postgresql-keyring.gpg] http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list && \
    apt-get update && \
    apt-get install -y postgresql-16-cron && \
    rm -rf /var/lib/apt/lists/*

# Build and install pgvector from source
RUN git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git /tmp/pgvector && \
    cd /tmp/pgvector && \
    make && \
    make install && \
    cd / && \
    rm -rf /tmp/pgvector

# (optional) place init scripts for auto-enabling extensions
COPY ./init-pgvector.sql /docker-entrypoint-initdb.d/
