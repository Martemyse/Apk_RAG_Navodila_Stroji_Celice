# MCP PostgreSQL Configuration

This directory contains the MCP (Model Context Protocol) configuration for connecting Cursor to PostgreSQL databases on the remote VM (ecotech).

## Architecture

- **Production PostgreSQL**: Runs on `ecotech` VM (192.168.99.206) inside Docker
- **MCP Server**: Runs in Docker Desktop on local Windows development machine
- **Cursor (MCP Client)**: Runs on Windows local development machine (outside Docker)
- **Local Test PostgreSQL**: Also runs in Docker Desktop (port 5432) - separate from production

## Setup Instructions

### Docker-Based MCP Server (Current Setup)

1. **Start the MCP Server Container:**
   ```bash
   docker-compose up -d
   ```
   
   This starts a container that stays running and is ready for Cursor to connect to it.

2. **Configure Cursor to Use the Docker Container:**
   
   **Option A: Via Cursor Settings UI**
   - Open Cursor Settings (Ctrl+,)
   - Search for "MCP" or "Model Context Protocol"
   - Click "Add MCP Server" or "Edit MCP Servers"
   - Remove any existing "postgres" configuration
   - Add a new server with the name "postgres" and use the configuration from `mcp.json`
   
   **Option B: Edit Cursor's MCP Settings File Directly (Windows)**
   - The MCP settings file is typically located at:
     `%APPDATA%\Cursor\User\globalStorage\mcp.json`
     or
     `C:\Users\<YourUsername>\AppData\Roaming\Cursor\User\globalStorage\mcp.json`
   - Open this file in a text editor
   - Replace the existing "postgres" configuration with the contents from `mcp.json` in this directory
   - Or copy the entire `mcp.json` file to that location (if Cursor uses file-based config)
   
   **The configuration should look like this:**
   ```json
   {
     "postgres": {
       "command": "docker",
       "args": [
         "exec",
         "-i",
         "mcp_postgres_c",
         "/app/entrypoint.sh",
         "mcp-postgres",
         "--connections",
         "postgresql://cursor_readonly:read@192.168.99.206:5432/bpsna_dobri_slabi_lj",
         "postgresql://cursor_readonly:read@192.168.99.206:5432/layout_proizvodnja_libre_konva",
         "postgresql://cursor_readonly:read@192.168.99.206:5432/postgres_db_anze",
         "--max-rows",
         "200"
       ],
       "env": {
         "NODE_TLS_REJECT_UNAUTHORIZED": "0"
       }
     }
   }
   ```

3. **Verify Docker is accessible from Cursor:**
   - Ensure Docker Desktop is running
   - Test that `docker exec -i mcp_postgres_c echo "test"` works from a command prompt
   - The container should be running: `docker ps | findstr mcp_postgres_c`

4. **Restart Cursor** completely (close and reopen) after updating the configuration

### Alternative: Direct npx Configuration

If you prefer to run the MCP server directly (without Docker):

1. **Install Node.js** (if not already installed)
   - Download from: https://nodejs.org/

2. **Configure Cursor** to use npx directly (modify `mcp.json` to use `npx` instead of `docker exec`)

## Database Connections

The configuration connects to three PostgreSQL databases on the remote VM (192.168.99.206):

1. `bpsna_dobri_slabi_lj`
2. `layout_proizvodnja_libre_konva`
3. `postgres_db_anze`

All connections use the `cursor_readonly` user with read-only access.

## Troubleshooting

- **Connection refused to 127.0.0.1:5432**: The MCP server is trying to connect to localhost instead of the external VM. Ensure:
  - The container is running: `docker ps` should show `mcp_postgres_c`
  - The `mcp.json` uses `docker exec` to connect to the container
  - The connection strings in `mcp.json` point to `192.168.99.206`, not `127.0.0.1`
  
- **Client reuse errors**: This can occur if connection strings aren't parsed correctly. The array format in `docker-compose.yml` and proper argument passing in `mcp.json` should fix this.

- **Container not accessible**: Ensure Docker Desktop is running and the container is up:
  ```bash
  docker ps | grep mcp_postgres_c
  ```

- **Cannot reach ecotech VM**: Verify network connectivity from your Windows machine to 192.168.99.206

