"""
DCS-BIOS TCP Control Sender
Sends control commands to DCS-BIOS via TCP
"""

import asyncio
import logging
import struct
from typing import Optional


logger = logging.getLogger(__name__)


class DCSBIOSSender:
    """TCP sender for DCS-BIOS control commands"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 7778):
        self.host = host
        self.port = port
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.connected = False
        self._reconnect_task: Optional[asyncio.Task] = None
        
    async def connect(self):
        """Connect to DCS-BIOS TCP server"""
        try:
            logger.info(f"Connecting to DCS-BIOS TCP server at {self.host}:{self.port}")
            self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
            self.connected = True
            logger.info("Connected to DCS-BIOS TCP server")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to DCS-BIOS: {e}")
            self.connected = False
            return False
            
    async def disconnect(self):
        """Disconnect from DCS-BIOS TCP server"""
        if self._reconnect_task:
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass
                
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")
                
        self.reader = None
        self.writer = None
        self.connected = False
        logger.info("Disconnected from DCS-BIOS TCP server")
        
    async def send_command(self, address: int, value: int):
        """
        Send a control command to DCS-BIOS
        
        Args:
            address: Control address
            value: Control value (0-65535)
        """
        if not self.connected or not self.writer:
            logger.warning("Not connected to DCS-BIOS, attempting to reconnect...")
            if not await self.connect():
                logger.error("Failed to send command: not connected")
                return False
                
        try:
            # DCS-BIOS protocol: address (2 bytes) + value (2 bytes)
            data = struct.pack('<HH', address, value)
            self.writer.write(data)
            await self.writer.drain()
            
            logger.debug(f"Sent command: address=0x{address:04X}, value=0x{value:04X}")
            return True
            
        except ConnectionError as e:
            logger.error(f"Connection error sending command: {e}")
            self.connected = False
            self._schedule_reconnect()
            return False
        except Exception as e:
            logger.error(f"Error sending command: {e}", exc_info=True)
            return False
            
    async def send_string_command(self, address: int, text: str):
        """
        Send a string command to DCS-BIOS (e.g., for CDU input)
        
        Args:
            address: Control address
            text: String to send
        """
        # Convert string to bytes and send each character
        for char in text:
            char_value = ord(char)
            if not await self.send_command(address, char_value):
                return False
        return True
        
    async def set_switch(self, address: int, position: int):
        """
        Set a switch to a specific position
        
        Args:
            address: Switch address
            position: Switch position
        """
        return await self.send_command(address, position)
        
    async def push_button(self, address: int):
        """
        Push a button (momentary action)
        
        Args:
            address: Button address
        """
        # Push button (value 1)
        if not await self.send_command(address, 1):
            return False
            
        # Small delay
        await asyncio.sleep(0.1)
        
        # Release button (value 0)
        return await self.send_command(address, 0)
        
    async def set_rotary(self, address: int, value: int, min_val: int = 0, max_val: int = 65535):
        """
        Set a rotary control (potentiometer, knob, etc.)
        
        Args:
            address: Control address
            value: Desired value
            min_val: Minimum value
            max_val: Maximum value
        """
        # Clamp value to range
        value = max(min_val, min(value, max_val))
        return await self.send_command(address, value)
        
    def _schedule_reconnect(self):
        """Schedule reconnection attempt"""
        if not self._reconnect_task or self._reconnect_task.done():
            self._reconnect_task = asyncio.create_task(self._reconnect_loop())
            
    async def _reconnect_loop(self):
        """Reconnection loop"""
        retry_delay = 5  # seconds
        
        while not self.connected:
            await asyncio.sleep(retry_delay)
            
            logger.info("Attempting to reconnect to DCS-BIOS...")
            if await self.connect():
                logger.info("Reconnected to DCS-BIOS successfully")
                break
            else:
                logger.warning(f"Reconnection failed, retrying in {retry_delay} seconds...")