#!/usr/bin/env python3
"""
DCS MCP Server
Main entry point for the MCP server that bridges DCS-BIOS with LLMs
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server import MCPServer
from config import Config
from logging_config import setup_logging


async def main():
    """Main entry point for the DCS MCP Server"""

    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Starting DCS MCP Server...")

    # Load configuration
    config = Config.load()

    # Create and start MCP server
    server = MCPServer(config)

    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
        await server.stop()
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        await server.stop()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())