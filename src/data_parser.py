"""
DCS-BIOS Data Parser
Parses DCS-BIOS messages and maintains aircraft state
"""

import json
import logging
import struct
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path


logger = logging.getLogger(__name__)


@dataclass
class AircraftState:
    """Maintains current aircraft state"""
    aircraft_type: str = "Unknown"
    timestamp: str = ""
    
    # Engine data
    engine: Dict[str, Any] = field(default_factory=dict)
    
    # Navigation data
    navigation: Dict[str, Any] = field(default_factory=dict)
    
    # Weapons data
    weapons: Dict[str, Any] = field(default_factory=dict)
    
    # Electronic warfare
    ew_systems: Dict[str, Any] = field(default_factory=dict)
    
    # Communications
    communications: Dict[str, Any] = field(default_factory=dict)
    
    # Flight controls
    flight_controls: Dict[str, Any] = field(default_factory=dict)
    
    # Instruments
    instruments: Dict[str, Any] = field(default_factory=dict)
    
    # Warnings
    warnings: Dict[str, Any] = field(default_factory=dict)
    
    # Raw data buffer for unknown addresses
    raw_data: Dict[int, bytes] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary"""
        return {
            "aircraft": {
                "type": self.aircraft_type,
                "timestamp": self.timestamp,
                "systems": {
                    "engine": self.engine,
                    "navigation": self.navigation,
                    "weapons": self.weapons,
                    "ew_systems": self.ew_systems,
                    "communications": self.communications,
                    "flight_controls": self.flight_controls,
                    "instruments": self.instruments,
                    "warnings": self.warnings
                }
            }
        }


class DataParser:
    """Parses DCS-BIOS data based on aircraft definitions"""
    
    def __init__(self):
        self.aircraft_state = AircraftState()
        self.definitions: Dict[str, Dict] = {}
        self.current_aircraft: Optional[str] = None
        self._load_definitions()
        
    def _load_definitions(self):
        """Load aircraft control definitions"""
        # This would normally load from JSON files defining each aircraft's controls
        # For now, we'll define some common addresses manually
        
        # Common addresses across aircraft
        self.common_addresses = {
            # Master caution
            0x1012: {"name": "MASTER_CAUTION", "category": "warnings", "type": "bool"},
            
            # Basic flight data (example addresses - these vary by aircraft)
            0x0500: {"name": "IAS", "category": "instruments", "type": "uint16", "scale": 0.1},
            0x0502: {"name": "ALTITUDE", "category": "instruments", "type": "int16", "scale": 10},
            0x0504: {"name": "HEADING", "category": "navigation", "type": "uint16", "scale": 0.1},
            0x0506: {"name": "VERTICAL_VELOCITY", "category": "instruments", "type": "int16"},
            
            # Engine data
            0x0600: {"name": "ENGINE_RPM_LEFT", "category": "engine", "type": "uint16", "scale": 0.01},
            0x0602: {"name": "ENGINE_RPM_RIGHT", "category": "engine", "type": "uint16", "scale": 0.01},
            0x0604: {"name": "ENGINE_TEMP_LEFT", "category": "engine", "type": "uint16"},
            0x0606: {"name": "ENGINE_TEMP_RIGHT", "category": "engine", "type": "uint16"},
            
            # Fuel
            0x0700: {"name": "FUEL_QUANTITY", "category": "engine", "type": "uint16", "scale": 10},
            0x0702: {"name": "FUEL_FLOW_LEFT", "category": "engine", "type": "uint16"},
            0x0704: {"name": "FUEL_FLOW_RIGHT", "category": "engine", "type": "uint16"},
        }
        
        # F/A-18C specific addresses
        self.definitions["FA-18C_hornet"] = {
            **self.common_addresses,
            # Add F/A-18C specific controls here
            0x7400: {"name": "UFC_COMM1", "category": "communications", "type": "string"},
            0x7402: {"name": "UFC_COMM2", "category": "communications", "type": "string"},
            0x74A0: {"name": "DDI_LEFT", "category": "instruments", "type": "display"},
            0x74C0: {"name": "DDI_RIGHT", "category": "instruments", "type": "display"},
        }
        
        # F-16C specific addresses  
        self.definitions["F-16C_50"] = {
            **self.common_addresses,
            # Add F-16C specific controls here
            0x4400: {"name": "DED_LINE1", "category": "instruments", "type": "string"},
            0x4420: {"name": "DED_LINE2", "category": "instruments", "type": "string"},
            0x4440: {"name": "DED_LINE3", "category": "instruments", "type": "string"},
            0x4460: {"name": "DED_LINE4", "category": "instruments", "type": "string"},
            0x4480: {"name": "DED_LINE5", "category": "instruments", "type": "string"},
        }
        
    def parse_message(self, address: int, data: bytes) -> Optional[Dict[str, Any]]:
        """
        Parse a DCS-BIOS message
        
        Returns:
            Parsed data or None if address is unknown
        """
        # Update timestamp
        self.aircraft_state.timestamp = datetime.utcnow().isoformat() + "Z"
        
        # Store raw data
        self.aircraft_state.raw_data[address] = data
        
        # Get definition for current aircraft
        definitions = self.definitions.get(self.current_aircraft, self.common_addresses)
        
        if address not in definitions:
            # Unknown address, store in raw data
            logger.debug(f"Unknown address: 0x{address:04X}")
            return None
            
        definition = definitions[address]
        name = definition["name"]
        category = definition["category"]
        data_type = definition.get("type", "uint16")
        
        # Parse based on type
        value = self._parse_value(data, data_type, definition)
        
        # Store in appropriate category
        self._store_value(category, name, value)
        
        return {
            "address": f"0x{address:04X}",
            "name": name,
            "category": category,
            "value": value
        }
        
    def _parse_value(self, data: bytes, data_type: str, definition: Dict[str, Any]) -> Any:
        """Parse value based on type"""
        if data_type == "bool":
            return struct.unpack('<H', data)[0] > 0
            
        elif data_type == "uint16":
            value = struct.unpack('<H', data)[0]
            if "scale" in definition:
                value *= definition["scale"]
            return value
            
        elif data_type == "int16":
            value = struct.unpack('<h', data)[0]
            if "scale" in definition:
                value *= definition["scale"]
            return value
            
        elif data_type == "string":
            # String data may come in multiple messages
            return data.decode('ascii', errors='ignore').rstrip('\x00')
            
        elif data_type == "display":
            # Display data (complex, would need special handling)
            return data.hex()
            
        else:
            return struct.unpack('<H', data)[0]
            
    def _store_value(self, category: str, name: str, value: Any):
        """Store parsed value in aircraft state"""
        if category == "engine":
            self.aircraft_state.engine[name] = value
        elif category == "navigation":
            self.aircraft_state.navigation[name] = value
        elif category == "weapons":
            self.aircraft_state.weapons[name] = value
        elif category == "ew_systems":
            self.aircraft_state.ew_systems[name] = value
        elif category == "communications":
            self.aircraft_state.communications[name] = value
        elif category == "flight_controls":
            self.aircraft_state.flight_controls[name] = value
        elif category == "instruments":
            self.aircraft_state.instruments[name] = value
        elif category == "warnings":
            self.aircraft_state.warnings[name] = value
            
    def set_aircraft_type(self, aircraft_type: str):
        """Set current aircraft type"""
        self.current_aircraft = aircraft_type
        self.aircraft_state.aircraft_type = aircraft_type
        logger.info(f"Aircraft type set to: {aircraft_type}")
        
    def get_state(self) -> Dict[str, Any]:
        """Get current aircraft state"""
        return self.aircraft_state.to_dict()
        
    def get_system_data(self, system: str) -> Dict[str, Any]:
        """Get data for a specific system"""
        state_dict = self.aircraft_state.to_dict()
        return state_dict["aircraft"]["systems"].get(system, {})
        
    def reset_state(self):
        """Reset aircraft state"""
        self.aircraft_state = AircraftState()
        if self.current_aircraft:
            self.aircraft_state.aircraft_type = self.current_aircraft