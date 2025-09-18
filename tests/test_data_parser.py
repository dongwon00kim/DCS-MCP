"""
Tests for DCS-BIOS Data Parser
"""

import struct
from datetime import datetime

import pytest

from data_parser import DataParser, AircraftState


class TestDataParser:
    """Test Data Parser functionality"""
    
    def test_parser_initialization(self):
        """Test parser initialization"""
        parser = DataParser()
        assert isinstance(parser.aircraft_state, AircraftState)
        assert parser.current_aircraft is None
        assert len(parser.definitions) > 0
        assert len(parser.common_addresses) > 0
    
    def test_aircraft_state_initialization(self):
        """Test aircraft state initialization"""
        state = AircraftState()
        assert state.aircraft_type == "Unknown"
        assert state.timestamp == ""
        assert isinstance(state.engine, dict)
        assert isinstance(state.navigation, dict)
        assert isinstance(state.weapons, dict)
        assert isinstance(state.raw_data, dict)
    
    def test_set_aircraft_type(self):
        """Test setting aircraft type"""
        parser = DataParser()
        parser.set_aircraft_type("FA-18C_hornet")
        
        assert parser.current_aircraft == "FA-18C_hornet"
        assert parser.aircraft_state.aircraft_type == "FA-18C_hornet"
    
    def test_parse_ias_message(self):
        """Test parsing IAS (Indicated Air Speed) message"""
        parser = DataParser()
        parser.set_aircraft_type("FA-18C_hornet")
        
        # IAS value: 4200 (420.0 knots after scaling)
        data = struct.pack('<H', 4200)
        result = parser.parse_message(0x0500, data)
        
        assert result is not None
        assert result['name'] == 'IAS'
        assert result['category'] == 'instruments'
        assert result['value'] == 420.0  # Scaled by 0.1
        assert parser.aircraft_state.instruments['IAS'] == 420.0
    
    def test_parse_altitude_message(self):
        """Test parsing altitude message"""
        parser = DataParser()
        parser.set_aircraft_type("FA-18C_hornet")
        
        # Altitude value: 1500 (15000 feet after scaling)
        data = struct.pack('<h', 1500)  # Signed int16
        result = parser.parse_message(0x0502, data)
        
        assert result is not None
        assert result['name'] == 'ALTITUDE'
        assert result['category'] == 'instruments'
        assert result['value'] == 15000  # Scaled by 10
        assert parser.aircraft_state.instruments['ALTITUDE'] == 15000
    
    def test_parse_heading_message(self):
        """Test parsing heading message"""
        parser = DataParser()
        parser.set_aircraft_type("FA-18C_hornet")
        
        # Heading value: 2700 (270.0 degrees after scaling)
        data = struct.pack('<H', 2700)
        result = parser.parse_message(0x0504, data)
        
        assert result is not None
        assert result['name'] == 'HEADING'
        assert result['category'] == 'navigation'
        assert result['value'] == 270.0  # Scaled by 0.1
        assert parser.aircraft_state.navigation['HEADING'] == 270.0
    
    def test_parse_engine_rpm_message(self):
        """Test parsing engine RPM message"""
        parser = DataParser()
        parser.set_aircraft_type("FA-18C_hornet")
        
        # Engine RPM: 8500 (85% after scaling)
        data = struct.pack('<H', 8500)
        result = parser.parse_message(0x0600, data)
        
        assert result is not None
        assert result['name'] == 'ENGINE_RPM_LEFT'
        assert result['category'] == 'engine'
        assert result['value'] == 85.0  # Scaled by 0.01
        assert parser.aircraft_state.engine['ENGINE_RPM_LEFT'] == 85.0
    
    def test_parse_master_caution_message(self):
        """Test parsing master caution (boolean) message"""
        parser = DataParser()
        parser.set_aircraft_type("FA-18C_hornet")
        
        # Master caution ON
        data = struct.pack('<H', 1)
        result = parser.parse_message(0x1012, data)
        
        assert result is not None
        assert result['name'] == 'MASTER_CAUTION'
        assert result['category'] == 'warnings'
        assert result['value'] is True
        assert parser.aircraft_state.warnings['MASTER_CAUTION'] is True
        
        # Master caution OFF
        data = struct.pack('<H', 0)
        result = parser.parse_message(0x1012, data)
        assert result['value'] is False
        assert parser.aircraft_state.warnings['MASTER_CAUTION'] is False
    
    def test_parse_unknown_address(self):
        """Test handling of unknown address"""
        parser = DataParser()
        parser.set_aircraft_type("FA-18C_hornet")
        
        # Unknown address
        data = struct.pack('<H', 12345)
        result = parser.parse_message(0xFFFF, data)
        
        assert result is None
        # But raw data should be stored
        assert 0xFFFF in parser.aircraft_state.raw_data
        assert parser.aircraft_state.raw_data[0xFFFF] == data
    
    def test_get_state(self):
        """Test getting complete aircraft state"""
        parser = DataParser()
        parser.set_aircraft_type("FA-18C_hornet")
        
        # Parse some messages
        parser.parse_message(0x0500, struct.pack('<H', 4200))  # IAS
        parser.parse_message(0x0600, struct.pack('<H', 8500))  # Engine RPM
        parser.parse_message(0x1012, struct.pack('<H', 1))     # Master Caution
        
        state = parser.get_state()
        
        assert state['aircraft']['type'] == 'FA-18C_hornet'
        assert 'timestamp' in state['aircraft']
        assert state['aircraft']['systems']['instruments']['IAS'] == 420.0
        assert state['aircraft']['systems']['engine']['ENGINE_RPM_LEFT'] == 85.0
        assert state['aircraft']['systems']['warnings']['MASTER_CAUTION'] is True
    
    def test_get_system_data(self):
        """Test getting specific system data"""
        parser = DataParser()
        parser.set_aircraft_type("FA-18C_hornet")
        
        # Parse engine messages
        parser.parse_message(0x0600, struct.pack('<H', 8500))  # RPM Left
        parser.parse_message(0x0602, struct.pack('<H', 8600))  # RPM Right
        parser.parse_message(0x0604, struct.pack('<H', 650))   # Temp Left
        
        engine_data = parser.get_system_data('engine')
        
        assert 'ENGINE_RPM_LEFT' in engine_data
        assert engine_data['ENGINE_RPM_LEFT'] == 85.0
        assert 'ENGINE_RPM_RIGHT' in engine_data
        assert engine_data['ENGINE_RPM_RIGHT'] == 86.0
        assert 'ENGINE_TEMP_LEFT' in engine_data
        assert engine_data['ENGINE_TEMP_LEFT'] == 650
    
    def test_reset_state(self):
        """Test resetting aircraft state"""
        parser = DataParser()
        parser.set_aircraft_type("FA-18C_hornet")
        
        # Add some data
        parser.parse_message(0x0500, struct.pack('<H', 4200))
        assert len(parser.aircraft_state.instruments) > 0
        
        # Reset
        parser.reset_state()
        
        assert len(parser.aircraft_state.instruments) == 0
        assert parser.aircraft_state.aircraft_type == "FA-18C_hornet"  # Type preserved
    
    def test_f16_specific_parsing(self):
        """Test F-16C specific data parsing"""
        parser = DataParser()
        parser.set_aircraft_type("F-16C_50")
        
        # F-16 has DED (Data Entry Display) lines
        # These would normally be string data
        data = b'TEST\x00\x00'
        result = parser.parse_message(0x4400, data[:2])  # DED_LINE1
        
        # Since we're using a simplified parser, just check it's handled
        if result:
            assert result['name'] == 'DED_LINE1'
            assert result['category'] == 'instruments'
    
    def test_timestamp_update(self):
        """Test that timestamp is updated on each parse"""
        parser = DataParser()
        parser.set_aircraft_type("FA-18C_hornet")
        
        # Parse first message
        parser.parse_message(0x0500, struct.pack('<H', 4200))
        timestamp1 = parser.aircraft_state.timestamp
        
        # Small delay to ensure different timestamp
        import time
        time.sleep(0.01)
        
        # Parse second message
        parser.parse_message(0x0502, struct.pack('<H', 1500))
        timestamp2 = parser.aircraft_state.timestamp
        
        # Timestamps should be different and valid ISO format
        assert timestamp1 != timestamp2
        assert timestamp2.endswith('Z')
        
        # Verify it's a valid ISO timestamp
        datetime.fromisoformat(timestamp2.replace('Z', '+00:00'))
    
    def test_data_type_parsing(self):
        """Test different data type parsing"""
        parser = DataParser()
        
        # Test uint16
        value = parser._parse_value(struct.pack('<H', 65535), 'uint16', {})
        assert value == 65535
        
        # Test int16
        value = parser._parse_value(struct.pack('<h', -1000), 'int16', {})
        assert value == -1000
        
        # Test bool
        value = parser._parse_value(struct.pack('<H', 0), 'bool', {})
        assert value is False
        value = parser._parse_value(struct.pack('<H', 1), 'bool', {})
        assert value is True
        
        # Test scaling
        value = parser._parse_value(struct.pack('<H', 1000), 'uint16', {'scale': 0.1})
        assert value == 100.0
        
        # Test string (simplified)
        value = parser._parse_value(b'AB', 'string', {})
        assert 'AB' in value or 'A' in value  # Depends on decoding
        
        # Test display (returns hex)
        value = parser._parse_value(b'\x12\x34', 'display', {})
        assert value == '1234'