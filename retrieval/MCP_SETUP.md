# MCP (Model Context Protocol) Setup Guide

This guide explains how to integrate the RAG pipeline with AI agents using the Model Context Protocol.

## What is MCP?

MCP (Model Context Protocol) is a standardized protocol for connecting AI agents (like Claude Desktop, ChatGPT, or custom agents) to external data sources and tools. It allows agents to:

- Search your manufacturing documentation
- Retrieve specific documents and pages
- Access real-time context from your knowledge base

## Quick Start

### 1. Claude Desktop Integration

Add this configuration to Claude Desktop's MCP settings:

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "rag-navodila": {
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "rag_retrieval",
        "python",
        "mcp_server.py"
      ],
      "env": {
        "WEAVIATE_URL": "http://weaviate:8080",
        "EMBEDDING_PROVIDER": "local",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### 2. Standalone MCP Server

Run the MCP server independently:

```bash
cd 2_Apk_RAG_Navodila_Stroji_Celice/retrieval
python mcp_server.py
```

Or via Docker:

```bash
docker exec -it rag_retrieval python mcp_server.py
```

## Available MCP Tools

### 1. `search_docs`
Search manufacturing documentation using hybrid search.

**Input:**
```json
{
  "query": "How to calibrate PTL007?",
  "top_k": 5,
  "rerank": true
}
```

**Output:**
Returns relevant passages with page numbers, section paths, and relevance scores.

**Example Usage (in Claude):**
```
"Can you search our manuals for information about PTL007 calibration?"
```

### 2. `list_documents`
List all available documentation.

**Input:**
```json
{}
```

**Output:**
List of all documents with titles, page counts, departments, and tags.

**Example Usage:**
```
"What manuals are available in the system?"
```

### 3. `get_document`
Get detailed content from a specific document.

**Input:**
```json
{
  "doc_id": "Navodila_PTL007_V1_4"
}
```

**Output:**
Full document content with all chunks and sections.

**Example Usage:**
```
"Can you show me the full PTL007 manual?"
```

### 4. `get_document_page`
Get content from a specific page.

**Input:**
```json
{
  "doc_id": "Navodila_PTL007_V1_4",
  "page": 5
}
```

**Output:**
Content from the specified page.

**Example Usage:**
```
"Show me page 5 of the PTL007 manual"
```

## Integration Examples

### Claude Desktop

Once configured, Claude will automatically detect the MCP tools. You can ask:

```
"Search our documentation for safety procedures related to ROM27"

"What documents do we have about die casting machines?"

"Show me the calibration steps from the PTL007 manual"
```

### Custom Python Agent (LangChain)

```python
from langchain_mcp import MCPClient

# Connect to MCP server
client = MCPClient("rag-navodila")

# Search documents
results = await client.call_tool(
    "search_docs",
    {"query": "machine calibration", "top_k": 3}
)

print(results)
```

### Custom Agent (Direct MCP)

```python
import mcp
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Connect to MCP server
server_params = StdioServerParameters(
    command="python",
    args=["mcp_server.py"],
    env={"WEAVIATE_URL": "http://localhost:8080"}
)

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        # Initialize
        await session.initialize()
        
        # List tools
        tools = await session.list_tools()
        
        # Call tool
        result = await session.call_tool(
            "search_docs",
            {"query": "safety procedures", "top_k": 5}
        )
        
        print(result)
```

## Environment Variables

Configure the MCP server with these environment variables:

```bash
# Weaviate
WEAVIATE_URL=http://weaviate:8080
WEAVIATE_API_KEY=

# Embeddings
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=BAAI/bge-large-en-v1.5

# Reranker
RERANKER_PROVIDER=local
RERANKER_MODEL=BAAI/bge-reranker-large

# MCP
MCP_ENABLE=true
MCP_SERVER_NAME=rag-navodila
MCP_SERVER_VERSION=1.0.0

# Logging
LOG_LEVEL=INFO
```

## Troubleshooting

### MCP Server Not Starting

1. **Check if MCP package is installed:**
   ```bash
   pip install mcp
   ```

2. **Verify Weaviate is running:**
   ```bash
   curl http://localhost:8080/v1/.well-known/ready
   ```

3. **Check logs:**
   ```bash
   docker logs rag_retrieval
   ```

### Claude Desktop Not Detecting MCP Server

1. **Restart Claude Desktop** after modifying config
2. **Check config file syntax** (must be valid JSON)
3. **Verify Docker container is running:**
   ```bash
   docker ps | grep rag_retrieval
   ```

### Empty or Incorrect Results

1. **Ensure documents are ingested:**
   ```bash
   curl http://localhost:8001/documents
   ```

2. **Test retrieval API directly:**
   ```bash
   curl -X POST http://localhost:8001/query \
     -H "Content-Type: application/json" \
     -d '{"query": "test", "top_k": 5}'
   ```

## Advanced Configuration

### Custom Tool Registration

Edit `mcp_server.py` to add custom tools:

```python
types.Tool(
    name="custom_search",
    description="Custom search with specific filters",
    inputSchema={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "department": {"type": "string"}
        }
    }
)
```

### Multi-Tenancy

Enable multi-tenancy for department-level isolation:

```bash
ENABLE_MULTI_TENANCY=true
DEFAULT_TENANT=manufacturing
```

### Authentication

Add authentication to MCP tools (optional):

```python
# In mcp_server.py
@self.server.call_tool()
async def handle_call_tool(name: str, arguments: dict, auth_token: str):
    # Verify auth_token
    if not verify_token(auth_token):
        raise PermissionError("Invalid authentication")
    
    # ... rest of handler
```

## Performance Tuning

1. **Adjust top_k based on your needs:**
   - Higher `top_k` = more comprehensive but slower
   - Recommended: 5-10 for most queries

2. **Enable/disable reranking:**
   - Reranking improves quality but adds latency
   - Disable for faster responses: `"rerank": false`

3. **Use filters for faster queries:**
   ```json
   {
     "query": "calibration",
     "filters": {"doc_id": "Navodila_PTL007_V1_4"}
   }
   ```

## Security Considerations

1. **Network isolation**: Run MCP server in private network
2. **API keys**: Use `WEAVIATE_API_KEY` if Weaviate auth is enabled
3. **Rate limiting**: Add rate limiting to MCP tools in production
4. **Audit logging**: Log all MCP tool calls for compliance

## Next Steps

- **Integrate with your existing agents**: Add MCP tools to LangChain, CrewAI, or custom agents
- **Create custom tools**: Extend MCP server with company-specific tools
- **Monitor usage**: Add metrics and monitoring for MCP tool calls
- **Build UI**: Create a web interface for non-technical users

## Resources

- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [Claude Desktop MCP Guide](https://docs.anthropic.com/claude/docs/model-context-protocol)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)

---
**Built for LTH Apps - Manufacturing Intelligence**

