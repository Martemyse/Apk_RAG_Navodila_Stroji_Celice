# Use the official Redis image as the base
FROM redis:latest

# Update the package lists, install sudo, nano, and procps (for ps), and clean up the cache
RUN apt-get update && apt-get install -y sudo nano procps && \
    rm -rf /var/lib/apt/lists/*

# Copy the redis.conf file from the current directory to the container
COPY redis.conf /usr/local/etc/redis/redis.conf

# Make sure Redis starts with the custom configuration file
CMD ["redis-server", "/usr/local/etc/redis/redis.conf"]
