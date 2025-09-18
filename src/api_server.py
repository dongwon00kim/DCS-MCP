"""
REST API and WebSocket server for DCS-BIOS MCP Server
Provides debugging and monitoring interfaces
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from config import Config
from dcs_bios_receiver import DCSBIOSReceiver, DCSBIOSMessage
from dcs_bios_sender import DCSBIOSSender
from data_parser import DataParser


logger = logging.getLogger(__name__)


class ControlCommand(BaseModel):
    """Control command model"""
    address: str  # Hex or decimal address
    value: int
    type: str = "set"  # set, button, switch


class APIServer:
    """REST API and WebSocket server"""
    
    def __init__(self, config: Config):
        self.config = config
        self.app = FastAPI(
            title="DCS-BIOS MCP Server API",
            description="Debug and monitoring API for DCS-BIOS MCP Server",
            version="1.0.0"
        )
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
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
        
        # WebSocket connections
        self.websocket_clients: Set[WebSocket] = set()
        
        # Data buffers
        self.raw_data_buffer = []
        self.parsed_data_buffer = []
        self.max_buffer_size = 1000
        
        # Connection status
        self.connection_status = {
            "receiver": False,
            "sender": False,
            "last_data": None,
            "messages_received": 0,
            "messages_sent": 0
        }
        
        # Setup routes
        self._setup_routes()
        
    def _setup_routes(self):
        """Setup API routes"""
        
        @self.app.on_event("startup")
        async def startup():
            """Start DCS-BIOS components on server startup"""
            await self.receiver.start()
            await self.sender.connect()
            
            # Set data callback
            self.receiver.set_data_callback(self._handle_dcs_data)
            
            self.connection_status["receiver"] = True
            self.connection_status["sender"] = self.sender.connected
            
            logger.info("API server started, DCS-BIOS components initialized")
        
        @self.app.on_event("shutdown")
        async def shutdown():
            """Stop DCS-BIOS components on server shutdown"""
            await self.receiver.stop()
            await self.sender.disconnect()
            
            # Close all websocket connections
            for ws in self.websocket_clients:
                await ws.close()
            
            logger.info("API server stopped")
        
        @self.app.get("/")
        async def root():
            """Root endpoint"""
            return {
                "name": "DCS-BIOS MCP Server API",
                "version": "1.0.0",
                "status": "running",
                "docs": "/docs"
            }
        
        @self.app.get("/api/raw-data")
        async def get_raw_data(limit: int = 100):
            """Get raw DCS-BIOS data"""
            return JSONResponse({
                "count": len(self.raw_data_buffer),
                "data": self.raw_data_buffer[-limit:]
            })
        
        @self.app.get("/api/parsed-data")
        async def get_parsed_data(limit: int = 100):
            """Get parsed DCS-BIOS data"""
            return JSONResponse({
                "count": len(self.parsed_data_buffer),
                "data": self.parsed_data_buffer[-limit:]
            })
        
        @self.app.get("/api/connection-status")
        async def get_connection_status():
            """Get connection status"""
            return JSONResponse(self.connection_status)
        
        @self.app.get("/api/aircraft-list")
        async def get_aircraft_list():
            """Get list of supported aircraft"""
            return JSONResponse({
                "aircraft": list(self.parser.definitions.keys()),
                "current": self.parser.current_aircraft
            })
        
        @self.app.get("/api/aircraft/current")
        async def get_current_aircraft():
            """Get current aircraft state"""
            return JSONResponse(self.parser.get_state())
        
        @self.app.get("/api/aircraft/systems/{system}")
        async def get_system_data(system: str):
            """Get specific system data"""
            data = self.parser.get_system_data(system)
            if not data:
                raise HTTPException(status_code=404, detail=f"System '{system}' not found")
            return JSONResponse(data)
        
        @self.app.post("/api/aircraft/type/{aircraft_type}")
        async def set_aircraft_type(aircraft_type: str):
            """Set aircraft type"""
            if aircraft_type not in self.parser.definitions:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Unknown aircraft type: {aircraft_type}"
                )
            self.parser.set_aircraft_type(aircraft_type)
            return JSONResponse({"success": True, "aircraft_type": aircraft_type})
        
        @self.app.post("/api/test-control")
        async def test_control(command: ControlCommand):
            """Test control command"""
            try:
                # Parse address
                if command.address.startswith('0x'):
                    address = int(command.address, 16)
                else:
                    address = int(command.address)
                
                # Send command based on type
                if command.type == "button":
                    success = await self.sender.push_button(address)
                elif command.type == "switch":
                    success = await self.sender.set_switch(address, command.value)
                else:  # "set"
                    success = await self.sender.send_command(address, command.value)
                
                self.connection_status["messages_sent"] += 1
                
                return JSONResponse({
                    "success": success,
                    "command": {
                        "address": f"0x{address:04X}",
                        "value": command.value,
                        "type": command.type
                    }
                })
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time data"""
            await websocket.accept()
            self.websocket_clients.add(websocket)
            
            try:
                # Send initial state
                await websocket.send_json({
                    "type": "state",
                    "data": self.parser.get_state()
                })
                
                # Keep connection alive
                while True:
                    # Receive messages (for ping/pong)
                    data = await websocket.receive_text()
                    
                    if data == "ping":
                        await websocket.send_text("pong")
                    elif data == "get_state":
                        await websocket.send_json({
                            "type": "state",
                            "data": self.parser.get_state()
                        })
                        
            except WebSocketDisconnect:
                self.websocket_clients.remove(websocket)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                self.websocket_clients.discard(websocket)
        
        @self.app.get("/api/aircraft/weapons")
        async def get_weapons_status():
            """Get weapons system status"""
            return JSONResponse(self.parser.get_system_data("weapons"))
        
        @self.app.get("/api/aircraft/engine")
        async def get_engine_data():
            """Get engine data"""
            return JSONResponse(self.parser.get_system_data("engine"))
        
        @self.app.get("/api/aircraft/navigation")
        async def get_navigation_data():
            """Get navigation data"""
            return JSONResponse(self.parser.get_system_data("navigation"))
    
    async def _handle_dcs_data(self, message: DCSBIOSMessage):
        """Handle incoming DCS-BIOS data"""
        # Update connection status
        self.connection_status["last_data"] = datetime.utcnow().isoformat()
        self.connection_status["messages_received"] += 1
        
        # Store raw data
        raw_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "address": f"0x{message.address:04X}",
            "data": message.data.hex()
        }
        self.raw_data_buffer.append(raw_entry)
        
        # Parse message
        parsed = self.parser.parse_message(message.address, message.data)
        if parsed:
            parsed_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                **parsed
            }
            self.parsed_data_buffer.append(parsed_entry)
            
            # Send to WebSocket clients
            asyncio.create_task(self._broadcast_to_websockets({
                "type": "update",
                "data": parsed_entry
            }))
        
        # Trim buffers
        if len(self.raw_data_buffer) > self.max_buffer_size:
            self.raw_data_buffer = self.raw_data_buffer[-self.max_buffer_size:]
        if len(self.parsed_data_buffer) > self.max_buffer_size:
            self.parsed_data_buffer = self.parsed_data_buffer[-self.max_buffer_size:]
    
    async def _broadcast_to_websockets(self, data: Dict[str, Any]):
        """Broadcast data to all WebSocket clients"""
        disconnected = set()
        
        for ws in self.websocket_clients:
            try:
                await ws.send_json(data)
            except Exception:
                disconnected.add(ws)
        
        # Remove disconnected clients
        self.websocket_clients -= disconnected
    
    def run(self):
        """Run the API server"""
        uvicorn.run(
            self.app,
            host=self.config.mcp_server.host,
            port=self.config.mcp_server.port,
            log_level="info"
        )


async def main():
    """Main entry point for API server"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    
    from logging_config import setup_logging
    
    # Setup logging
    setup_logging()
    
    # Load configuration
    config = Config.load()
    
    # Create and run API server
    server = APIServer(config)
    server.run()


if __name__ == "__main__":
    asyncio.run(main())