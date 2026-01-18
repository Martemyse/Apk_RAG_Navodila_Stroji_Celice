FROM node:20
WORKDIR /app

# Disable SSL verification for npm during build ONLY
RUN npm config set strict-ssl false

# Install latest mcp-postgres globally
RUN npm install -g mcp-postgres@latest

# Copy entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# No ENTRYPOINT - container will run command from docker-compose.yml directly
# Entrypoint script will be called explicitly by Cursor via docker exec
