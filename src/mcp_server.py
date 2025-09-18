"""
MCP Server Implementation
Provides MCP protocol interface for LLM integration
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from mcp import Server, Tool
from mcp.types import TextContent, ToolResult

from config import Config
from dcs_bios_receiver import DCSBIOSReceiver, DCSBIOSMessage
from dcs_bios_sender import DCSBIOSSender
from data_parser import DataParser


logger = logging.getLogger(__name__)


class MCPServer:
    """MCP Server for DCS-BIOS integration"""
    
    def __init__(self, config: Config):
        self.config = config
        self.server = Server("dcs-bios-mcp")
        
        # DCS-BIOS components
        self.receiver = DCSBIOSReceiver(
            host=config.dcs_bios.host,
            port=config.dcs_bios.port
        )
        self.sender = DCSBIOSSender(
            host=config.dcs_bios.tcp_host,
            port=config.dcs_bios.tcp_port
        )
        self.parser = DataParser()
        
        # State tracking
        self.monitoring = False
        self.monitor_callbacks: List = []
        
        # Register MCP tools
        self._register_tools()
        
        # Set receiver callback
        self.receiver.set_data_callback(self._handle_dcs_data)
        
    def _register_tools(self):
        """Register MCP protocol tools"""
        
        @self.server.tool()
        async def get_aircraft_status() -> ToolResult:
            """Get complete aircraft status"""
            try:
                state = self.parser.get_state()
                return ToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps(state, indent=2)
                    )]
                )
            except Exception as e:
                logger.error(f"Error getting aircraft status: {e}")
                return ToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"Error: {str(e)}"
                    )],
                    is_error=True
                )
        
        @self.server.tool()
        async def get_system_data(system: str) -> ToolResult:
            """
            Get data for a specific aircraft system
            
            Args:
                system: System name (engine, navigation, weapons, etc.)
            """
            try:
                data = self.parser.get_system_data(system)
                return ToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps(data, indent=2)
                    )]
                )
            except Exception as e:
                logger.error(f"Error getting system data: {e}")
                return ToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"Error: {str(e)}"
                    )],
                    is_error=True
                )
        
        @self.server.tool()
        async def set_control(address: int, value: int) -> ToolResult:
            """
            Set a control value in the aircraft
            
            Args:
                address: Control address (hex or decimal)
                value: Control value (0-65535)
            """
            try:
                # Handle hex string input
                if isinstance(address, str):
                    address = int(address, 16 if address.startswith('0x') else 10)
                    
                success = await self.sender.send_command(address, value)
                
                return ToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"Control set: address=0x{address:04X}, value={value}, success={success}"
                    )]
                )
            except Exception as e:
                logger.error(f"Error setting control: {e}")
                return ToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"Error: {str(e)}"
                    )],
                    is_error=True
                )
        
        @self.server.tool()
        async def push_button(address: int) -> ToolResult:
            """
            Push a button control
            
            Args:
                address: Button address (hex or decimal)
            """
            try:
                # Handle hex string input
                if isinstance(address, str):
                    address = int(address, 16 if address.startswith('0x') else 10)
                    
                success = await self.sender.push_button(address)
                
                return ToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"Button pushed: address=0x{address:04X}, success={success}"
                    )]
                )
            except Exception as e:
                logger.error(f"Error pushing button: {e}")
                return ToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"Error: {str(e)}"
                    )],
                    is_error=True
                )
        
        @self.server.tool()
        async def set_switch(address: int, position: int) -> ToolResult:
            """
            Set a switch to a specific position
            
            Args:
                address: Switch address (hex or decimal)
                position: Switch position
            """
            try:
                # Handle hex string input
                if isinstance(address, str):
                    address = int(address, 16 if address.startswith('0x') else 10)
                    
                success = await self.sender.set_switch(address, position)
                
                return ToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"Switch set: address=0x{address:04X}, position={position}, success={success}"
                    )]
                )
            except Exception as e:
                logger.error(f"Error setting switch: {e}")
                return ToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"Error: {str(e)}"
                    )],
                    is_error=True
                )
        
        @self.server.tool()
        async def monitor_changes(duration: int = 10) -> ToolResult:
            """
            Monitor aircraft state changes for a duration
            
            Args:
                duration: Monitoring duration in seconds (default 10)
            """
            try:
                changes = []
                start_time = datetime.utcnow()
                
                async def monitor_callback(message: DCSBIOSMessage):
                    parsed = self.parser.parse_message(message.address, message.data)
                    if parsed:
                        changes.append({
                            "timestamp": datetime.utcnow().isoformat(),
                            **parsed
                        })
                
                # Temporarily add monitoring callback
                self.monitor_callbacks.append(monitor_callback)
                
                # Wait for duration
                await asyncio.sleep(duration)
                
                # Remove callback
                self.monitor_callbacks.remove(monitor_callback)
                
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                
                result = {
                    "duration": elapsed,
                    "changes_count": len(changes),
                    "changes": changes[-100:]  # Limit to last 100 changes
                }
                
                return ToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps(result, indent=2)
                    )]
                )
            except Exception as e:
                logger.error(f"Error monitoring changes: {e}")
                return ToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"Error: {str(e)}"
                    )],
                    is_error=True
                )
        
        @self.server.tool()
        async def execute_procedure(commands: List[Dict[str, Any]]) -> ToolResult:
            """
            Execute a sequence of control commands
            
            Args:
                commands: List of command dicts with 'type', 'address', 'value', and optional 'delay'
            """
            try:
                results = []
                
                for cmd in commands:
                    cmd_type = cmd.get("type", "set")
                    address = cmd.get("address")
                    value = cmd.get("value", 0)
                    delay = cmd.get("delay", 0.1)
                    
                    # Handle hex string input
                    if isinstance(address, str):
                        address = int(address, 16 if address.startswith('0x') else 10)
                    
                    if cmd_type == "button":
                        success = await self.sender.push_button(address)
                    elif cmd_type == "switch":
                        success = await self.sender.set_switch(address, value)
                    else:  # "set"
                        success = await self.sender.send_command(address, value)
                    
                    results.append({
                        "type": cmd_type,
                        "address": f"0x{address:04X}",
                        "value": value,
                        "success": success
                    })
                    
                    # Delay between commands
                    if delay > 0:
                        await asyncio.sleep(delay)
                
                return ToolResult(
                    content=[TextContent(
                        type="text",
                        text=json.dumps({"results": results}, indent=2)
                    )]
                )
            except Exception as e:
                logger.error(f"Error executing procedure: {e}")
                return ToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"Error: {str(e)}"
                    )],
                    is_error=True
                )
        
        @self.server.tool()
        async def set_aircraft_type(aircraft_type: str) -> ToolResult:
            """
            Set the current aircraft type for proper data parsing
            
            Args:
                aircraft_type: Aircraft type (e.g., 'FA-18C_hornet', 'F-16C_50')
            """
            try:
                self.parser.set_aircraft_type(aircraft_type)
                return ToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"Aircraft type set to: {aircraft_type}"
                    )]
                )
            except Exception as e:
                logger.error(f"Error setting aircraft type: {e}")
                return ToolResult(
                    content=[TextContent(
                        type="text",
                        text=f"Error: {str(e)}"
                    )],
                    is_error=True
                )
    
    async def _handle_dcs_data(self, message: DCSBIOSMessage):
        """Handle incoming DCS-BIOS data"""
        # Parse message
        parsed = self.parser.parse_message(message.address, message.data)
        
        if parsed:
            logger.debug(f"Parsed: {parsed}")
        
        # Call monitor callbacks
        for callback in self.monitor_callbacks:
            try:
                await callback(message)
            except Exception as e:
                logger.error(f"Error in monitor callback: {e}")
    
    async def start(self):
        """Start the MCP server"""
        logger.info("Starting MCP server components...")
        
        # Start DCS-BIOS receiver
        await self.receiver.start()
        
        # Connect DCS-BIOS sender
        await self.sender.connect()
        
        # Start MCP server
        logger.info("Starting MCP server...")
        await self.server.run()
        
    async def stop(self):
        """Stop the MCP server"""
        logger.info("Stopping MCP server...")
        
        # Stop receiver
        await self.receiver.stop()
        
        # Disconnect sender  
        await self.sender.disconnect()
        
        logger.info("MCP server stopped")