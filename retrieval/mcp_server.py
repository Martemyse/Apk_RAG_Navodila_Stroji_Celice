"""MCP (Model Context Protocol) server for AI agent integration."""
from typing import List, Dict, Any, Optional
import asyncio
from loguru import logger

try:
    from mcp.server import Server, NotificationOptions
    from mcp.server.models import InitializationOptions
    import mcp.server.stdio
    import mcp.types as types
    MCP_AVAILABLE = True
except ImportError:
    logger.warning("MCP package not available, MCP server will be disabled")
    MCP_AVAILABLE = False

from config import get_settings
from weaviate_client import get_weaviate_client
from embeddings import get_embedding_provider
from reranker import get_reranker

settings = get_settings()


class MCPRAGServer:
    """MCP server for RAG operations."""
    
    def __init__(self):
        """Initialize MCP server."""
        if not MCP_AVAILABLE:
            raise ImportError("MCP package not available")
        
        self.server = Server(settings.mcp_server_name)
        self.weaviate_client = None
        self.embedding_provider = None
        self.reranker = None
        
        # Register handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register MCP handlers."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            """List available tools."""
            return [
                types.Tool(
                    name="search_docs",
                    description=(
                        "Search manufacturing documentation using hybrid search (BM25 + vector). "
                        "Returns relevant passages from manuals with page numbers and citations."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query for documentation"
                            },
                            "top_k": {
                                "type": "number",
                                "description": "Number of results to return (default: 5)",
                                "default": 5
                            },
                            "rerank": {
                                "type": "boolean",
                                "description": "Whether to rerank results for better relevance (default: true)",
                                "default": True
                            }
                        },
                        "required": ["query"]
                    }
                ),
                types.Tool(
                    name="get_document",
                    description=(
                        "Get detailed information about a specific document, "
                        "including all its chunks and metadata."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "doc_id": {
                                "type": "string",
                                "description": "Document ID (e.g., 'Navodila_PTL007_V1_4')"
                            }
                        },
                        "required": ["doc_id"]
                    }
                ),
                types.Tool(
                    name="list_documents",
                    description="List all available manufacturing manuals and documentation.",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                types.Tool(
                    name="get_document_page",
                    description=(
                        "Get content from a specific page of a document. "
                        "Useful when you need to reference exact page content."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "doc_id": {
                                "type": "string",
                                "description": "Document ID"
                            },
                            "page": {
                                "type": "number",
                                "description": "Page number (1-indexed)"
                            }
                        },
                        "required": ["doc_id", "page"]
                    }
                ),
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(
            name: str,
            arguments: dict
        ) -> List[types.TextContent | types.ImageContent | types.EmbeddedResource]:
            """Handle tool calls."""
            logger.info(f"MCP tool called: {name} with args: {arguments}")
            
            try:
                if name == "search_docs":
                    return await self._search_docs(arguments)
                elif name == "get_document":
                    return await self._get_document(arguments)
                elif name == "list_documents":
                    return await self._list_documents(arguments)
                elif name == "get_document_page":
                    return await self._get_document_page(arguments)
                else:
                    return [types.TextContent(
                        type="text",
                        text=f"Unknown tool: {name}"
                    )]
            except Exception as e:
                logger.error(f"Error calling tool {name}: {e}")
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )]
    
    async def _search_docs(self, arguments: dict) -> List[types.TextContent]:
        """Search documents tool."""
        query = arguments.get("query", "")
        top_k = arguments.get("top_k", 5)
        rerank = arguments.get("rerank", True)
        
        if not query:
            return [types.TextContent(
                type="text",
                text="Error: Query cannot be empty"
            )]
        
        # Generate embedding
        query_vector = self.embedding_provider.embed(query)
        
        # Search
        results = self.weaviate_client.hybrid_search(
            query=query,
            query_vector=query_vector,
            limit=top_k * 3 if rerank else top_k,
            alpha=0.5
        )
        
        # Rerank if requested
        if rerank and self.reranker and len(results) > 1:
            texts = [r.text for r in results]
            rerank_results = self.reranker.rerank(query, texts, top_k=top_k)
            reranked_indices = [idx for idx, _ in rerank_results]
            results = [results[i] for i in reranked_indices]
        else:
            results = results[:top_k]
        
        # Format response
        if not results:
            response_text = f"No results found for query: {query}"
        else:
            response_parts = [f"Found {len(results)} relevant passages:\n"]
            
            for i, result in enumerate(results, 1):
                response_parts.append(
                    f"\n[{i}] Document: {result.doc_id} (Page {result.page})\n"
                    f"Section: {result.section_path}\n"
                    f"Content: {result.text}\n"
                    f"Relevance Score: {result.score:.3f}\n"
                )
            
            response_text = "".join(response_parts)
        
        return [types.TextContent(
            type="text",
            text=response_text
        )]
    
    async def _get_document(self, arguments: dict) -> List[types.TextContent]:
        """Get document tool."""
        doc_id = arguments.get("doc_id", "")
        
        if not doc_id:
            return [types.TextContent(
                type="text",
                text="Error: doc_id is required"
            )]
        
        # Get document chunks
        chunks = self.weaviate_client.get_document_chunks(doc_id)
        
        if not chunks:
            return [types.TextContent(
                type="text",
                text=f"Document not found: {doc_id}"
            )]
        
        # Format response
        response_parts = [
            f"Document: {doc_id}\n",
            f"Total chunks: {len(chunks)}\n\n",
            "Content:\n"
        ]
        
        for chunk in chunks[:20]:  # Limit to first 20 chunks
            response_parts.append(
                f"\n[Page {chunk.page}] {chunk.section_path}\n"
                f"{chunk.text}\n"
            )
        
        if len(chunks) > 20:
            response_parts.append(f"\n... ({len(chunks) - 20} more chunks)")
        
        return [types.TextContent(
            type="text",
            text="".join(response_parts)
        )]
    
    async def _list_documents(self, arguments: dict) -> List[types.TextContent]:
        """List documents tool."""
        documents = self.weaviate_client.get_documents()
        
        if not documents:
            return [types.TextContent(
                type="text",
                text="No documents found in the system"
            )]
        
        # Format response
        response_parts = [f"Available documents ({len(documents)}):\n\n"]
        
        for doc in documents:
            response_parts.append(
                f"- {doc['doc_id']}\n"
                f"  Title: {doc['title']}\n"
                f"  Pages: {doc['total_pages']}\n"
                f"  Department: {doc['department']}\n"
                f"  Tags: {', '.join(doc['tags'])}\n\n"
            )
        
        return [types.TextContent(
            type="text",
            text="".join(response_parts)
        )]
    
    async def _get_document_page(self, arguments: dict) -> List[types.TextContent]:
        """Get document page tool."""
        doc_id = arguments.get("doc_id", "")
        page = arguments.get("page", 0)
        
        if not doc_id or page <= 0:
            return [types.TextContent(
                type="text",
                text="Error: doc_id and page (> 0) are required"
            )]
        
        # Get all chunks for document
        all_chunks = self.weaviate_client.get_document_chunks(doc_id)
        
        # Filter by page
        page_chunks = [c for c in all_chunks if c.page == page]
        
        if not page_chunks:
            return [types.TextContent(
                type="text",
                text=f"No content found for {doc_id} page {page}"
            )]
        
        # Format response
        response_parts = [
            f"Document: {doc_id} - Page {page}\n\n"
        ]
        
        for chunk in page_chunks:
            response_parts.append(
                f"{chunk.section_path}\n"
                f"{chunk.text}\n\n"
            )
        
        return [types.TextContent(
            type="text",
            text="".join(response_parts)
        )]
    
    async def run(self):
        """Run MCP server."""
        logger.info("Starting MCP server")
        
        # Initialize clients
        self.weaviate_client = get_weaviate_client()
        self.embedding_provider = get_embedding_provider()
        self.reranker = get_reranker()
        
        # Run server
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name=settings.mcp_server_name,
                    server_version=settings.mcp_server_version,
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    )
                )
            )


async def run_mcp_server():
    """Run MCP server."""
    if not MCP_AVAILABLE:
        logger.error("MCP package not available, cannot start MCP server")
        return
    
    if not settings.mcp_enable:
        logger.info("MCP server disabled in configuration")
        return
    
    server = MCPRAGServer()
    await server.run()


def main():
    """Main entry point for MCP server."""
    import sys
    from loguru import logger
    
    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>"
    )
    
    logger.info("Starting MCP RAG Server")
    
    try:
        asyncio.run(run_mcp_server())
    except KeyboardInterrupt:
        logger.info("MCP server stopped by user")
    except Exception as e:
        logger.error(f"MCP server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

