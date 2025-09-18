#!/usr/bin/env python3
"""
MCP Server stdio implementation for DCS-BIOS
Provides stdio-based MCP server for LLM integration
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp import Server
from mcp.server.stdio import stdio_server

from config import Config
from dcs_bios_receiver import DCSBIOSReceiver
from dcs_bios_sender import DCSBIOSSender
from data_parser import DataParser
from logging_config import setup_logging


logger = logging.getLogger(__name__)


async def main():
    """Main entry point for MCP stdio server"""
    
    # Setup logging (to file only, not stdout)
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Redirect all stdout/stderr to null to avoid interfering with MCP
    import os
    sys.stderr = open(os.devnull, 'w')
    
    logger.info("Starting DCS-BIOS MCP stdio server...")
    
    # Load configuration
    config = Config.load()
    
    # Create server
    server = Server("dcs-bios-mcp")
    
    # Initialize components
    receiver = DCSBIOSReceiver(
        host=config.dcs_bios.host,
        port=config.dcs_bios.port
    )
    sender = DCSBIOSSender(
        host=config.dcs_bios.tcp_host,
        port=config.dcs_bios.tcp_port
    )
    parser = DataParser()
    
    # Set default aircraft type
    parser.set_aircraft_type("FA-18C_hornet")
    
    # Start receiver
    await receiver.start()
    await sender.connect()
    
    # Register data handler
    async def handle_dcs_data(message):
        parser.parse_message(message.address, message.data)
    
    receiver.set_data_callback(handle_dcs_data)
    
    # Register MCP tools
    @server.tool()
    async def get_aircraft_status():
        """Get complete aircraft status from DCS"""
        try:
            state = parser.get_state()
            return json.dumps(state, indent=2)
        except Exception as e:
            logger.error(f"Error getting aircraft status: {e}")
            return f"Error: {str(e)}"
    
    @server.tool()
    async def get_system_data(system: str):
        """Get data for a specific aircraft system
        
        Args:
            system: System name (engine, navigation, weapons, etc.)
        """
        try:
            data = parser.get_system_data(system)
            return json.dumps(data, indent=2)
        except Exception as e:
            logger.error(f"Error getting system data: {e}")
            return f"Error: {str(e)}"
    
    @server.tool()
    async def set_control(address: str, value: int):
        """Set a control value in the aircraft
        
        Args:
            address: Control address (hex string like '0x1234' or decimal)
            value: Control value (0-65535)
        """
        try:
            # Parse address
            if address.startswith('0x'):
                addr = int(address, 16)
            else:
                addr = int(address)
            
            success = await sender.send_command(addr, value)
            return f"Control set: address=0x{addr:04X}, value={value}, success={success}"
        except Exception as e:
            logger.error(f"Error setting control: {e}")
            return f"Error: {str(e)}"
    
    @server.tool()
    async def push_button(address: str):
        """Push a button control
        
        Args:
            address: Button address (hex string like '0x1234' or decimal)
        """
        try:
            # Parse address
            if address.startswith('0x'):
                addr = int(address, 16)
            else:
                addr = int(address)
            
            success = await sender.push_button(addr)
            return f"Button pushed: address=0x{addr:04X}, success={success}"
        except Exception as e:
            logger.error(f"Error pushing button: {e}")
            return f"Error: {str(e)}"
    
    @server.tool()
    async def set_switch(address: str, position: int):
        """Set a switch to a specific position
        
        Args:
            address: Switch address (hex string like '0x1234' or decimal)
            position: Switch position
        """
        try:
            # Parse address
            if address.startswith('0x'):
                addr = int(address, 16)
            else:
                addr = int(address)
            
            success = await sender.set_switch(addr, position)
            return f"Switch set: address=0x{addr:04X}, position={position}, success={success}"
        except Exception as e:
            logger.error(f"Error setting switch: {e}")
            return f"Error: {str(e)}"
    
    @server.tool()
    async def set_aircraft_type(aircraft_type: str):
        """Set the current aircraft type for proper data parsing
        
        Args:
            aircraft_type: Aircraft type (e.g., 'FA-18C_hornet', 'F-16C_50')
        """
        try:
            parser.set_aircraft_type(aircraft_type)
            return f"Aircraft type set to: {aircraft_type}"
        except Exception as e:
            logger.error(f"Error setting aircraft type: {e}")
            return f"Error: {str(e)}"
    
    @server.tool() 
    async def monitor_changes(duration: int = 10):
        """Monitor aircraft state changes for a duration
        
        Args:
            duration: Monitoring duration in seconds (default 10)
        """
        try:
            changes = []
            
            async def monitor_callback(message):
                parsed = parser.parse_message(message.address, message.data)
                if parsed:
                    changes.append(parsed)
            
            # Temporarily add monitoring callback
            old_callback = receiver.data_callback
            receiver.set_data_callback(monitor_callback)
            
            # Wait for duration
            await asyncio.sleep(duration)
            
            # Restore callback
            receiver.set_data_callback(old_callback)
            
            result = {
                "duration": duration,
                "changes_count": len(changes),
                "changes": changes[-100:]  # Limit to last 100 changes
            }
            
            return json.dumps(result, indent=2)
        except Exception as e:
            logger.error(f"Error monitoring changes: {e}")
            return f"Error: {str(e)}"
    
    # Run the stdio server
    async with stdio_server() as (read_stream, write_stream):
        logger.info("MCP stdio server ready")
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )
    
    # Cleanup
    await receiver.stop()
    await sender.disconnect()


if __name__ == "__main__":
    asyncio.run(main())