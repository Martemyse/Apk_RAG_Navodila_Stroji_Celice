"""MCP server for text-image fused RAG."""
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
from mcp_tools import get_mcp_tools

settings = get_settings()


class MCPFusedRAGServer:
    """MCP server for fused text-image RAG."""
    
    def __init__(self):
        """Initialize MCP server."""
        if not MCP_AVAILABLE:
            raise ImportError("MCP package not available")
        
        self.server = Server(settings.mcp_server_name)
        self.mcp_tools = None
        
        # Register handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register MCP handlers."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            """List available tools."""
            return [
                types.Tool(
                    name="search_content_units",
                    description=(
                        "Search manufacturing documentation using fused text+image content units. "
                        "Returns semantic units that may include images with their context. "
                        "Use this to find relevant information from manuals."
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
                                "description": "Number of results to return (default: 10)",
                                "default": 10
                            }
                        },
                        "required": ["query"]
                    }
                ),
                types.Tool(
                    name="get_image",
                    description=(
                        "Get image asset by ID. Use this when a content unit has an image_id. "
                        "Returns image path and metadata for display."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "image_id": {
                                "type": "string",
                                "description": "Image asset UUID"
                            }
                        },
                        "required": ["image_id"]
                    }
                ),
                types.Tool(
                    name="get_pdf_section",
                    description=(
                        "Get PDF section information for a content unit. "
                        "Returns document ID, page number, and section details for deep linking."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "unit_id": {
                                "type": "string",
                                "description": "Content unit UUID"
                            }
                        },
                        "required": ["unit_id"]
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
                if name == "search_content_units":
                    return await self._search_content_units(arguments)
                elif name == "get_image":
                    return await self._get_image(arguments)
                elif name == "get_pdf_section":
                    return await self._get_pdf_section(arguments)
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
    
    async def _search_content_units(self, arguments: dict) -> List[types.TextContent]:
        """Search content units tool."""
        query = arguments.get("query", "")
        top_k = arguments.get("top_k", 10)
        
        if not query:
            return [types.TextContent(
                type="text",
                text="Error: Query cannot be empty"
            )]
        
        tools = await get_mcp_tools()
        results = await tools.search_content_units(query, top_k)
        
        if not results:
            return [types.TextContent(
                type="text",
                text=f"No results found for query: {query}"
            )]
        
        # Format response
        response_parts = [f"Found {len(results)} relevant content units:\n"]
        
        for i, unit in enumerate(results, 1):
            response_parts.append(
                f"\n[{i}] {unit.get('section_title', 'Untitled')} "
                f"(Page {unit['page_number']})\n"
                f"Document: {unit['doc_id']}\n"
                f"Content: {unit['text'][:200]}...\n"
            )
            
            if unit.get('has_image'):
                response_parts.append(
                    f"📷 Has associated image (ID: {unit['image_id']})\n"
                )
            
            response_parts.append(f"Relevance Score: {unit['score']:.3f}\n")
        
        return [types.TextContent(
            type="text",
            text="".join(response_parts)
        )]
    
    async def _get_image(self, arguments: dict) -> List[types.TextContent]:
        """Get image tool."""
        image_id = arguments.get("image_id", "")
        
        if not image_id:
            return [types.TextContent(
                type="text",
                text="Error: image_id is required"
            )]
        
        tools = await get_mcp_tools()
        image_data = await tools.get_image(image_id)
        
        if not image_data:
            return [types.TextContent(
                type="text",
                text=f"Image not found: {image_id}"
            )]
        
        response = (
            f"Image Asset:\n"
            f"ID: {image_data['image_id']}\n"
            f"Path: {image_data['image_path']}\n"
            f"Page: {image_data['page_number']}\n"
            f"Document: {image_data['doc_id']}\n"
        )
        
        if image_data.get('caption'):
            response += f"Caption: {image_data['caption']}\n"
        
        return [types.TextContent(
            type="text",
            text=response
        )]
    
    async def _get_pdf_section(self, arguments: dict) -> List[types.TextContent]:
        """Get PDF section tool."""
        unit_id = arguments.get("unit_id", "")
        
        if not unit_id:
            return [types.TextContent(
                type="text",
                text="Error: unit_id is required"
            )]
        
        tools = await get_mcp_tools()
        section_data = await tools.get_pdf_section(unit_id)
        
        if not section_data:
            return [types.TextContent(
                type="text",
                text=f"Content unit not found: {unit_id}"
            )]
        
        response = (
            f"PDF Section:\n"
            f"Document: {section_data['doc_id']} - {section_data['document_title']}\n"
            f"Page: {section_data['page_number']}\n"
            f"Section: {section_data.get('section_title', 'N/A')}\n"
            f"Path: {section_data.get('section_path', 'N/A')}\n"
            f"File: {section_data['file_path']}\n"
        )
        
        return [types.TextContent(
            type="text",
            text=response
        )]
    
    async def run(self):
        """Run MCP server."""
        logger.info("Starting MCP fused RAG server")
        
        # Initialize tools
        await get_mcp_tools()
        
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
    
    server = MCPFusedRAGServer()
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
    
    logger.info("Starting MCP Fused RAG Server")
    
    try:
        asyncio.run(run_mcp_server())
    except KeyboardInterrupt:
        logger.info("MCP server stopped by user")
    except Exception as e:
        logger.error(f"MCP server error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

