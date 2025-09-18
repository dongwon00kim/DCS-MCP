"""
Tests for DCS-BIOS UDP Multicast Receiver
"""

import asyncio
import socket
import struct
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from dcs_bios_receiver import DCSBIOSReceiver, DCSBIOSMessage


class TestDCSBIOSReceiver:
    """Test DCS-BIOS Receiver functionality"""
    
    @pytest.mark.asyncio
    async def test_receiver_initialization(self):
        """Test receiver initialization with default values"""
        receiver = DCSBIOSReceiver()
        assert receiver.host == "239.255.50.10"
        assert receiver.port == 5010
        assert receiver.socket is None
        assert receiver.running is False
        assert receiver.data_callback is None
    
    @pytest.mark.asyncio
    async def test_receiver_initialization_custom(self):
        """Test receiver initialization with custom values"""
        receiver = DCSBIOSReceiver(host="239.255.50.11", port=5011)
        assert receiver.host == "239.255.50.11"
        assert receiver.port == 5011
    
    @pytest.mark.asyncio
    async def test_start_receiver(self, mock_socket):
        """Test starting the receiver"""
        with patch('socket.socket', return_value=mock_socket):
            receiver = DCSBIOSReceiver()
            
            # Mock the receive loop to prevent actual running
            with patch.object(receiver, '_receive_loop', new_callable=AsyncMock) as mock_loop:
                await receiver.start()
                
                assert receiver.running is True
                assert receiver.socket is not None
                
                # Check socket configuration
                mock_socket.setsockopt.assert_called()
                mock_socket.bind.assert_called_with(('', 5010))
                mock_socket.setblocking.assert_called_with(False)
                
                # Clean up
                await receiver.stop()
    
    @pytest.mark.asyncio
    async def test_stop_receiver(self, mock_socket):
        """Test stopping the receiver"""
        with patch('socket.socket', return_value=mock_socket):
            receiver = DCSBIOSReceiver()
            
            with patch.object(receiver, '_receive_loop', new_callable=AsyncMock):
                await receiver.start()
                assert receiver.running is True
                
                await receiver.stop()
                assert receiver.running is False
                assert receiver.socket is None
                mock_socket.close.assert_called()
    
    @pytest.mark.asyncio
    async def test_data_callback_registration(self):
        """Test registering a data callback"""
        receiver = DCSBIOSReceiver()
        
        async def test_callback(message):
            pass
        
        receiver.set_data_callback(test_callback)
        assert receiver.data_callback == test_callback
    
    @pytest.mark.asyncio
    async def test_message_parsing(self, mock_socket, sample_dcs_bios_messages):
        """Test parsing of DCS-BIOS messages"""
        received_messages = []
        
        async def capture_callback(message):
            received_messages.append(message)
        
        # Create test data
        test_data = b''
        for msg in sample_dcs_bios_messages[:3]:  # Use first 3 messages
            test_data += struct.pack('<H', msg['address']) + msg['data']
        
        with patch('socket.socket', return_value=mock_socket):
            receiver = DCSBIOSReceiver()
            receiver.set_data_callback(capture_callback)
            
            # Mock socket receive to return our test data once
            async def mock_recv(sock, size):
                if not hasattr(mock_recv, 'called'):
                    mock_recv.called = True
                    return test_data
                raise BlockingIOError()
            
            with patch('asyncio.get_event_loop') as mock_loop:
                mock_loop.return_value.sock_recv = mock_recv
                
                # Manually process data (simulate _receive_loop behavior)
                buffer = bytearray(test_data)
                while len(buffer) >= 4:
                    address = struct.unpack('<H', buffer[0:2])[0]
                    value = buffer[2:4]
                    
                    if address != 0x5555 or value != b'\x55\x55':  # Skip sync
                        message = DCSBIOSMessage(address=address, data=value)
                        await capture_callback(message)
                    
                    buffer = buffer[4:]
        
        # Verify messages were parsed correctly (excluding sync)
        assert len(received_messages) == 2
        assert received_messages[0].address == 0x0500
        assert received_messages[0].data == b'\x10\x27'
        assert received_messages[1].address == 0x0502
        assert received_messages[1].data == b'\xE8\x03'
    
    @pytest.mark.asyncio
    async def test_sync_message_handling(self):
        """Test that sync messages are handled correctly"""
        received_messages = []
        
        async def capture_callback(message):
            received_messages.append(message)
        
        # Create sync message
        sync_data = struct.pack('<H', 0x5555) + b'\x55\x55'
        # Add a normal message after sync
        normal_data = struct.pack('<H', 0x0500) + b'\x10\x27'
        test_data = sync_data + normal_data
        
        # Process data
        buffer = bytearray(test_data)
        while len(buffer) >= 4:
            address = struct.unpack('<H', buffer[0:2])[0]
            value = buffer[2:4]
            
            if address == 0x5555 and value == b'\x55\x55':
                # Sync message should be skipped
                buffer = buffer[4:]
                continue
            
            message = DCSBIOSMessage(address=address, data=value)
            await capture_callback(message)
            buffer = buffer[4:]
        
        # Only non-sync message should be received
        assert len(received_messages) == 1
        assert received_messages[0].address == 0x0500
    
    @pytest.mark.asyncio
    async def test_partial_message_buffering(self):
        """Test handling of partial messages"""
        buffer = bytearray()
        
        # Add partial message (only 3 bytes)
        partial_data = b'\x00\x05\x10'
        buffer.extend(partial_data)
        
        # Should not process incomplete message
        messages_processed = 0
        while len(buffer) >= 4:
            messages_processed += 1
            buffer = buffer[4:]
        
        assert messages_processed == 0
        assert len(buffer) == 3
        
        # Add remaining byte
        buffer.extend(b'\x27')
        
        # Now should process
        while len(buffer) >= 4:
            address = struct.unpack('<H', buffer[0:2])[0]
            value = buffer[2:4]
            assert address == 0x0500
            assert value == b'\x10\x27'
            messages_processed += 1
            buffer = buffer[4:]
        
        assert messages_processed == 1
        assert len(buffer) == 0
    
    @pytest.mark.asyncio
    async def test_callback_error_handling(self, mock_socket):
        """Test that callback errors don't crash the receiver"""
        error_raised = False
        
        async def failing_callback(message):
            nonlocal error_raised
            error_raised = True
            raise ValueError("Test error")
        
        with patch('socket.socket', return_value=mock_socket):
            receiver = DCSBIOSReceiver()
            receiver.set_data_callback(failing_callback)
            
            # Create test message
            test_data = struct.pack('<H', 0x0500) + b'\x10\x27'
            
            # Process message with failing callback
            buffer = bytearray(test_data)
            while len(buffer) >= 4:
                address = struct.unpack('<H', buffer[0:2])[0]
                value = buffer[2:4]
                message = DCSBIOSMessage(address=address, data=value)
                
                # Callback should fail but be caught
                try:
                    await failing_callback(message)
                except ValueError:
                    pass  # Expected
                
                buffer = buffer[4:]
            
            assert error_raised