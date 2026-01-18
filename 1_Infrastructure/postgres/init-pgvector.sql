-- init-pgvector.sql
-- this runs at container startup for a brand‐new cluster only!
-- it adds the vector extension into template1 so that all new DBs include it.
\connect template1
CREATE EXTENSION IF NOT EXISTS vector;
