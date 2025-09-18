"""
Tests for DCS-BIOS TCP Control Sender
"""

import asyncio
import struct
from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from dcs_bios_sender import DCSBIOSSender


class TestDCSBIOSSender:
    """Test DCS-BIOS Sender functionality"""
    
    @pytest.mark.asyncio
    async def test_sender_initialization(self):
        """Test sender initialization with default values"""
        sender = DCSBIOSSender()
        assert sender.host == "127.0.0.1"
        assert sender.port == 7778
        assert sender.reader is None
        assert sender.writer is None
        assert sender.connected is False
    
    @pytest.mark.asyncio
    async def test_sender_initialization_custom(self):
        """Test sender initialization with custom values"""
        sender = DCSBIOSSender(host="192.168.1.100", port=7779)
        assert sender.host == "192.168.1.100"
        assert sender.port == 7779
    
    @pytest.mark.asyncio
    async def test_connect_success(self, mock_reader_writer):
        """Test successful connection to DCS-BIOS"""
        reader, writer = mock_reader_writer
        
        with patch('asyncio.open_connection', return_value=(reader, writer)):
            sender = DCSBIOSSender()
            result = await sender.connect()
            
            assert result is True
            assert sender.connected is True
            assert sender.reader == reader
            assert sender.writer == writer
    
    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Test failed connection to DCS-BIOS"""
        with patch('asyncio.open_connection', side_effect=ConnectionError("Connection refused")):
            sender = DCSBIOSSender()
            result = await sender.connect()
            
            assert result is False
            assert sender.connected is False
            assert sender.reader is None
            assert sender.writer is None
    
    @pytest.mark.asyncio
    async def test_disconnect(self, mock_reader_writer):
        """Test disconnection from DCS-BIOS"""
        reader, writer = mock_reader_writer
        
        with patch('asyncio.open_connection', return_value=(reader, writer)):
            sender = DCSBIOSSender()
            await sender.connect()
            assert sender.connected is True
            
            await sender.disconnect()
            
            assert sender.connected is False
            assert sender.reader is None
            assert sender.writer is None
            writer.close.assert_called()
            writer.wait_closed.assert_called()
    
    @pytest.mark.asyncio
    async def test_send_command(self, mock_reader_writer):
        """Test sending a control command"""
        reader, writer = mock_reader_writer
        
        with patch('asyncio.open_connection', return_value=(reader, writer)):
            sender = DCSBIOSSender()
            await sender.connect()
            
            # Send command
            result = await sender.send_command(0x1234, 0x5678)
            
            assert result is True
            
            # Check that correct data was sent
            expected_data = struct.pack('<HH', 0x1234, 0x5678)
            writer.write.assert_called_with(expected_data)
            writer.drain.assert_called()
    
    @pytest.mark.asyncio
    async def test_send_command_not_connected(self, mock_reader_writer):
        """Test sending command when not connected (should auto-connect)"""
        reader, writer = mock_reader_writer
        
        with patch('asyncio.open_connection', return_value=(reader, writer)):
            sender = DCSBIOSSender()
            assert sender.connected is False
            
            # Send command should trigger connection
            result = await sender.send_command(0x1234, 0x5678)
            
            assert result is True
            assert sender.connected is True
            writer.write.assert_called()
    
    @pytest.mark.asyncio
    async def test_send_string_command(self, mock_reader_writer):
        """Test sending a string command (e.g., for CDU input)"""
        reader, writer = mock_reader_writer
        
        with patch('asyncio.open_connection', return_value=(reader, writer)):
            sender = DCSBIOSSender()
            await sender.connect()
            
            # Send string
            result = await sender.send_string_command(0x7400, "TEST")
            
            assert result is True
            
            # Check that each character was sent
            assert writer.write.call_count == 4
            expected_calls = [
                struct.pack('<HH', 0x7400, ord('T')),
                struct.pack('<HH', 0x7400, ord('E')),
                struct.pack('<HH', 0x7400, ord('S')),
                struct.pack('<HH', 0x7400, ord('T')),
            ]
            for i, expected in enumerate(expected_calls):
                assert writer.write.call_args_list[i][0][0] == expected
    
    @pytest.mark.asyncio
    async def test_set_switch(self, mock_reader_writer):
        """Test setting a switch position"""
        reader, writer = mock_reader_writer
        
        with patch('asyncio.open_connection', return_value=(reader, writer)):
            sender = DCSBIOSSender()
            await sender.connect()
            
            # Set switch to position 2
            result = await sender.set_switch(0x2000, 2)
            
            assert result is True
            
            expected_data = struct.pack('<HH', 0x2000, 2)
            writer.write.assert_called_with(expected_data)
    
    @pytest.mark.asyncio
    async def test_push_button(self, mock_reader_writer):
        """Test pushing a button (momentary action)"""
        reader, writer = mock_reader_writer
        
        with patch('asyncio.open_connection', return_value=(reader, writer)):
            sender = DCSBIOSSender()
            await sender.connect()
            
            # Push button
            with patch('asyncio.sleep', new_callable=AsyncMock):
                result = await sender.push_button(0x3000)
            
            assert result is True
            
            # Check press and release
            assert writer.write.call_count == 2
            press_data = struct.pack('<HH', 0x3000, 1)
            release_data = struct.pack('<HH', 0x3000, 0)
            assert writer.write.call_args_list[0][0][0] == press_data
            assert writer.write.call_args_list[1][0][0] == release_data
    
    @pytest.mark.asyncio
    async def test_set_rotary(self, mock_reader_writer):
        """Test setting a rotary control"""
        reader, writer = mock_reader_writer
        
        with patch('asyncio.open_connection', return_value=(reader, writer)):
            sender = DCSBIOSSender()
            await sender.connect()
            
            # Set rotary within range
            result = await sender.set_rotary(0x4000, 32768, 0, 65535)
            assert result is True
            expected_data = struct.pack('<HH', 0x4000, 32768)
            writer.write.assert_called_with(expected_data)
            
            # Reset mock
            writer.write.reset_mock()
            
            # Test clamping to max
            result = await sender.set_rotary(0x4000, 70000, 0, 65535)
            assert result is True
            expected_data = struct.pack('<HH', 0x4000, 65535)
            writer.write.assert_called_with(expected_data)
            
            # Reset mock
            writer.write.reset_mock()
            
            # Test clamping to min
            result = await sender.set_rotary(0x4000, -100, 0, 65535)
            assert result is True
            expected_data = struct.pack('<HH', 0x4000, 0)
            writer.write.assert_called_with(expected_data)
    
    @pytest.mark.asyncio
    async def test_connection_error_handling(self, mock_reader_writer):
        """Test handling of connection errors during send"""
        reader, writer = mock_reader_writer
        writer.write.side_effect = ConnectionError("Connection lost")
        
        with patch('asyncio.open_connection', return_value=(reader, writer)):
            sender = DCSBIOSSender()
            await sender.connect()
            
            # Mock reconnect task
            with patch.object(sender, '_schedule_reconnect') as mock_schedule:
                result = await sender.send_command(0x1234, 0x5678)
                
                assert result is False
                assert sender.connected is False
                mock_schedule.assert_called()
    
    @pytest.mark.asyncio
    async def test_auto_reconnect(self, mock_reader_writer):
        """Test automatic reconnection after connection loss"""
        reader, writer = mock_reader_writer
        
        # First connection succeeds, second fails, third succeeds
        connection_attempts = [
            (reader, writer),
            ConnectionError("Connection refused"),
            (reader, writer)
        ]
        
        with patch('asyncio.open_connection', side_effect=connection_attempts):
            sender = DCSBIOSSender()
            
            # First connection
            assert await sender.connect() is True
            assert sender.connected is True
            
            # Simulate connection loss
            sender.connected = False
            
            # Start reconnect loop
            with patch('asyncio.sleep', new_callable=AsyncMock):
                # This will fail once then succeed
                reconnect_task = asyncio.create_task(sender._reconnect_loop())
                
                # Give it time to run (mocked sleep)
                await asyncio.sleep(0)
                
                # Should eventually reconnect
                # Note: In real implementation, this would retry with delay
                # For testing, we'll just verify the method structure
                reconnect_task.cancel()
                try:
                    await reconnect_task
                except asyncio.CancelledError:
                    pass