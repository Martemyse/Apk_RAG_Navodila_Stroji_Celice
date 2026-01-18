#!/bin/sh
set -e

# Ensure we're not using any default localhost connections
# Unset all possible database-related environment variables (except DATABASE_URL which we'll set from args)
unset POSTGRES_URL
unset POSTGRES_HOST
unset POSTGRES_PORT
unset PGHOST
unset PGPORT
unset PGDATABASE
unset PGUSER
unset PGPASSWORD

# Extract first connection string from arguments and set as DATABASE_URL
# This prevents mcp-postgres from defaulting to localhost
# Look for the first postgresql:// URL in the arguments
for arg in "$@"; do
  if echo "$arg" | grep -q "^postgresql://"; then
    export DATABASE_URL="$arg"
    echo "Setting DATABASE_URL to first connection: $arg" >&2
    break
  fi
done

# Debug: Show what arguments we're passing (redirect to stderr to avoid breaking MCP JSON protocol)
echo "Starting mcp-postgres with arguments: $@" >&2
echo "Number of arguments: $#" >&2
echo "Arguments list:" >&2
for arg in "$@"; do
  echo "  - $arg" >&2
done

# Verify connection strings are present
if echo "$@" | grep -q "192.168.99.206"; then
  echo "✓ Connection strings with external IP found in arguments" >&2
else
  echo "✗ WARNING: No connection strings with external IP found in arguments!" >&2
fi

# The first argument is "mcp-postgres" (passed by Cursor), skip it and pass the rest
shift
exec mcp-postgres "$@"

