#!/usr/bin/env python3
"""
DCS-BIOS MCP Server Runner
Runs both MCP stdio server and API debug server
"""

import asyncio
import sys
import argparse
import logging
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from logging_config import setup_logging


def run_mcp_stdio():
    """Run MCP stdio server"""
    from mcp_server import main as mcp_main
    asyncio.run(mcp_main())


def run_api_server():
    """Run API debug server"""
    from api_server import APIServer
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Starting API debug server...")
    
    # Load configuration
    config = Config.load()
    
    # Create and run API server
    server = APIServer(config)
    server.run()


def run_combined():
    """Run both servers in separate processes"""
    import multiprocessing
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("Starting DCS-BIOS MCP Server in combined mode...")
    
    # Start API server in a separate process
    api_process = multiprocessing.Process(target=run_api_server)
    api_process.start()
    
    try:
        # Run MCP stdio server in main process
        run_mcp_stdio()
    except KeyboardInterrupt:
        logger.info("Shutting down servers...")
    finally:
        # Terminate API server
        api_process.terminate()
        api_process.join()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="DCS-BIOS MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run as MCP stdio server (for Claude Desktop)
  python run_server.py --mode mcp
  
  # Run API debug server only
  python run_server.py --mode api
  
  # Run both servers (default)
  python run_server.py
  
For Claude Desktop, use --mode mcp and configure in Claude Desktop settings:
{
  "mcpServers": {
    "dcs-bios": {
      "command": "python",
      "args": ["/path/to/run_server.py", "--mode", "mcp"]
    }
  }
}
        """
    )
    
    parser.add_argument(
        '--mode',
        choices=['mcp', 'api', 'both'],
        default='both',
        help='Server mode: mcp (stdio), api (debug), or both (default)'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        help='Path to configuration file'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    args = parser.parse_args()
    
    # Set config path if provided
    if args.config:
        import os
        os.environ['DCS_MCP_CONFIG'] = args.config
    
    # Set debug logging if requested
    if args.debug:
        import os
        os.environ['DCS_MCP_DEBUG'] = '1'
    
    # Run based on mode
    if args.mode == 'mcp':
        run_mcp_stdio()
    elif args.mode == 'api':
        run_api_server()
    else:  # both
        run_combined()


if __name__ == "__main__":
    main()