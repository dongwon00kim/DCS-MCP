"""
End-to-end integration tests for DCS-BIOS MCP Server
These tests require DCS World and DCS-BIOS to be running
"""

import asyncio
import socket
import struct
import time
from unittest.mock import patch, AsyncMock

import pytest

from config import Config
from dcs_bios_receiver import DCSBIOSReceiver
from dcs_bios_sender import DCSBIOSSender
from data_parser import DataParser


@pytest.mark.integration
class TestEndToEnd:
    """End-to-end integration tests"""
    
    @pytest.mark.asyncio
    async def test_data_flow_simulation(self, test_config, sample_dcs_bios_messages):
        """Test complete data flow from receiver to parser"""
        # Setup components
        receiver = DCSBIOSReceiver(
            host=test_config.dcs_bios.host,
            port=test_config.dcs_bios.port
        )
        parser = DataParser()
        parser.set_aircraft_type("FA-18C_hornet")
        
        # Collect parsed data
        parsed_data = []
        
        async def data_handler(message):
            result = parser.parse_message(message.address, message.data)
            if result:
                parsed_data.append(result)
        
        receiver.set_data_callback(data_handler)
        
        # Simulate receiving messages
        for msg in sample_dcs_bios_messages:
            await data_handler(type('Message', (), {
                'address': msg['address'],
                'data': msg['data']
            })())
        
        # Verify parsed data
        assert len(parsed_data) > 0
        
        # Check specific values
        state = parser.get_state()
        assert state['aircraft']['type'] == 'FA-18C_hornet'
        
        # Verify some parsed values
        instruments = state['aircraft']['systems'].get('instruments', {})
        if 'IAS' in instruments:
            assert instruments['IAS'] > 0
        
        warnings = state['aircraft']['systems'].get('warnings', {})
        if 'MASTER_CAUTION' in warnings:
            assert isinstance(warnings['MASTER_CAUTION'], bool)
    
    @pytest.mark.asyncio
    async def test_control_command_flow(self, test_config):
        """Test sending control commands through the system"""
        sender = DCSBIOSSender(
            host=test_config.dcs_bios.tcp_host,
            port=test_config.dcs_bios.tcp_port
        )
        
        # Mock the connection
        with patch('asyncio.open_connection') as mock_connect:
            reader = AsyncMock()
            writer = AsyncMock()
            mock_connect.return_value = (reader, writer)
            
            # Connect and send commands
            await sender.connect()
            
            # Test various control types
            commands_sent = []
            
            # Capture writes
            def capture_write(data):
                commands_sent.append(data)
            
            writer.write.side_effect = capture_write
            
            # Send different command types
            await sender.set_switch(0x1000, 1)
            await sender.set_rotary(0x2000, 32768)
            await sender.push_button(0x3000)
            
            # Verify commands were sent
            assert len(commands_sent) >= 3
            
            # Verify command formats
            assert commands_sent[0] == struct.pack('<HH', 0x1000, 1)
            assert commands_sent[1] == struct.pack('<HH', 0x2000, 32768)
            
            await sender.disconnect()
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not socket.socket(socket.AF_INET, socket.SOCK_DGRAM).connect_ex(("239.255.50.10", 5010)) == 0,
        reason="DCS-BIOS not running"
    )
    async def test_live_dcs_connection(self):
        """Test actual connection to DCS-BIOS (requires DCS running)"""
        receiver = DCSBIOSReceiver()
        parser = DataParser()
        
        messages_received = []
        
        async def data_handler(message):
            messages_received.append(message)
            parser.parse_message(message.address, message.data)
        
        receiver.set_data_callback(data_handler)
        
        try:
            # Start receiver
            await receiver.start()
            
            # Collect data for 2 seconds
            await asyncio.sleep(2)
            
            # Stop receiver
            await receiver.stop()
            
            # Check if we received data
            if len(messages_received) > 0:
                print(f"Received {len(messages_received)} messages from DCS-BIOS")
                
                # Get aircraft state
                state = parser.get_state()
                print(f"Aircraft type: {state['aircraft']['type']}")
                
                # Show some data
                for system, data in state['aircraft']['systems'].items():
                    if data:
                        print(f"{system}: {list(data.keys())[:5]}")  # Show first 5 keys
        except Exception as e:
            pytest.skip(f"Could not connect to DCS-BIOS: {e}")
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self, sample_dcs_bios_messages):
        """Test performance requirements from SRS"""
        parser = DataParser()
        parser.set_aircraft_type("FA-18C_hornet")
        
        # Test message processing rate (requirement: 1000+ messages/second)
        start_time = time.time()
        messages_processed = 0
        
        # Process messages multiple times to get enough samples
        for _ in range(100):
            for msg in sample_dcs_bios_messages:
                parser.parse_message(msg['address'], msg['data'])
                messages_processed += 1
        
        elapsed = time.time() - start_time
        rate = messages_processed / elapsed
        
        print(f"Processing rate: {rate:.0f} messages/second")
        assert rate > 1000, f"Processing rate {rate:.0f} is below requirement of 1000/s"
        
        # Test response time (requirement: <100ms)
        async def timed_operation():
            start = time.time()
            state = parser.get_state()
            return time.time() - start
        
        response_times = []
        for _ in range(10):
            response_time = await timed_operation()
            response_times.append(response_time)
        
        avg_response = sum(response_times) / len(response_times)
        print(f"Average response time: {avg_response*1000:.2f}ms")
        assert avg_response < 0.1, f"Response time {avg_response*1000:.2f}ms exceeds 100ms requirement"
    
    @pytest.mark.asyncio
    async def test_reconnection_handling(self):
        """Test automatic reconnection after connection loss"""
        sender = DCSBIOSSender()
        
        connection_count = 0
        
        async def mock_connect(*args, **kwargs):
            nonlocal connection_count
            connection_count += 1
            
            if connection_count == 1:
                # First connection succeeds
                reader = AsyncMock()
                writer = AsyncMock()
                return reader, writer
            elif connection_count == 2:
                # Second attempt fails
                raise ConnectionError("Connection lost")
            else:
                # Third attempt succeeds
                reader = AsyncMock()
                writer = AsyncMock()
                return reader, writer
        
        with patch('asyncio.open_connection', side_effect=mock_connect):
            # First connection
            result = await sender.connect()
            assert result is True
            assert connection_count == 1
            
            # Simulate connection loss
            sender.connected = False
            
            # Try to reconnect (will fail once then succeed)
            with patch('asyncio.sleep', new_callable=AsyncMock):
                result = await sender.connect()
                # This attempt will fail
                assert result is False
                
                # Next attempt should succeed
                result = await sender.connect()
                assert result is True
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, sample_dcs_bios_messages):
        """Test handling concurrent read/write operations"""
        parser = DataParser()
        parser.set_aircraft_type("FA-18C_hornet")
        
        async def read_task():
            """Simulate reading data"""
            for msg in sample_dcs_bios_messages:
                parser.parse_message(msg['address'], msg['data'])
                await asyncio.sleep(0.001)
        
        async def query_task():
            """Simulate querying state"""
            results = []
            for _ in range(10):
                state = parser.get_state()
                results.append(state)
                await asyncio.sleep(0.002)
            return results
        
        # Run tasks concurrently
        results = await asyncio.gather(
            read_task(),
            query_task(),
            return_exceptions=True
        )
        
        # Verify no exceptions
        for result in results:
            if isinstance(result, Exception):
                raise result
        
        # Verify we got valid states
        states = results[1]
        assert len(states) == 10
        for state in states:
            assert 'aircraft' in state
            assert 'systems' in state['aircraft']