"""
DCS-BIOS UDP Multicast Receiver
Receives and processes DCS-BIOS data from UDP multicast
"""

import asyncio
import logging
import socket
import struct
from typing import Callable, Optional
from dataclasses import dataclass


logger = logging.getLogger(__name__)


@dataclass
class DCSBIOSMessage:
    """Represents a DCS-BIOS message"""
    address: int
    data: bytes
    
    def __repr__(self):
        return f"DCSBIOSMessage(address=0x{self.address:04X}, data={self.data.hex()})"


class DCSBIOSReceiver:
    """UDP Multicast receiver for DCS-BIOS data"""
    
    def __init__(self, host: str = "239.255.50.10", port: int = 5010):
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.running = False
        self.data_callback: Optional[Callable] = None
        self._receive_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Start receiving DCS-BIOS data"""
        if self.running:
            logger.warning("Receiver already running")
            return
            
        logger.info(f"Starting DCS-BIOS receiver on {self.host}:{self.port}")
        
        # Create UDP socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Bind to port
        self.socket.bind(('', self.port))
        
        # Join multicast group
        mreq = struct.pack("4sl", socket.inet_aton(self.host), socket.INADDR_ANY)
        self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        
        # Set non-blocking
        self.socket.setblocking(False)
        
        self.running = True
        self._receive_task = asyncio.create_task(self._receive_loop())
        
        logger.info("DCS-BIOS receiver started successfully")
        
    async def stop(self):
        """Stop receiving DCS-BIOS data"""
        if not self.running:
            return
            
        logger.info("Stopping DCS-BIOS receiver...")
        self.running = False
        
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
                
        if self.socket:
            # Leave multicast group
            try:
                mreq = struct.pack("4sl", socket.inet_aton(self.host), socket.INADDR_ANY)
                self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_DROP_MEMBERSHIP, mreq)
            except Exception as e:
                logger.warning(f"Error leaving multicast group: {e}")
                
            self.socket.close()
            self.socket = None
            
        logger.info("DCS-BIOS receiver stopped")
        
    async def _receive_loop(self):
        """Main receive loop"""
        loop = asyncio.get_event_loop()
        buffer = bytearray()
        
        while self.running:
            try:
                # Receive data asynchronously
                data = await loop.sock_recv(self.socket, 4096)
                
                if not data:
                    continue
                    
                # Add to buffer
                buffer.extend(data)
                
                # Process complete messages
                while len(buffer) >= 4:
                    # DCS-BIOS protocol: 2 bytes address + 2 bytes data
                    if len(buffer) >= 4:
                        address = struct.unpack('<H', buffer[0:2])[0]
                        value = buffer[2:4]
                        
                        # Check for sync message (0x5555 at address 0x5555)
                        if address == 0x5555 and value == b'\x55\x55':
                            logger.debug("Sync message received")
                            buffer = buffer[4:]
                            continue
                            
                        message = DCSBIOSMessage(address=address, data=value)
                        
                        # Call callback if registered
                        if self.data_callback:
                            try:
                                await self.data_callback(message)
                            except Exception as e:
                                logger.error(f"Error in data callback: {e}", exc_info=True)
                                
                        # Remove processed message from buffer
                        buffer = buffer[4:]
                    else:
                        break
                        
            except asyncio.CancelledError:
                raise
            except BlockingIOError:
                # No data available, wait a bit
                await asyncio.sleep(0.001)
            except Exception as e:
                logger.error(f"Error receiving DCS-BIOS data: {e}", exc_info=True)
                await asyncio.sleep(0.1)
                
    def set_data_callback(self, callback: Callable):
        """Set callback for received data"""
        self.data_callback = callback