"""
Test configuration and fixtures for pytest
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock, MagicMock

import pytest

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import Config, DCSBIOSConfig, MCPServerConfig, LoggingConfig


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_config():
    """Create a test configuration"""
    config = Config(
        dcs_bios=DCSBIOSConfig(
            host="239.255.50.10",
            port=5010,
            multicast=True,
            tcp_host="127.0.0.1",
            tcp_port=7778
        ),
        mcp_server=MCPServerConfig(
            host="127.0.0.1",
            port=8080,
            enable_websocket=False  # Disable for tests
        ),
        aircraft_filter=["FA-18C_hornet", "F-16C_50"],
        data_update_rate=10,
        logging=LoggingConfig(
            level="DEBUG",
            file="tests/test.log"
        )
    )
    return config


@pytest.fixture
def mock_socket():
    """Create a mock socket for testing"""
    mock = MagicMock()
    mock.recv = MagicMock()
    mock.send = MagicMock()
    mock.close = MagicMock()
    mock.bind = MagicMock()
    mock.setsockopt = MagicMock()
    mock.setblocking = MagicMock()
    return mock


@pytest.fixture
def sample_dcs_bios_messages():
    """Sample DCS-BIOS messages for testing"""
    return [
        # Sync message
        {"address": 0x5555, "data": b'\x55\x55'},
        # IAS (Indicated Air Speed)
        {"address": 0x0500, "data": b'\x10\x27'},  # 10000 (scaled by 0.1 = 1000)
        # Altitude
        {"address": 0x0502, "data": b'\xE8\x03'},  # 1000 (scaled by 10 = 10000)
        # Heading
        {"address": 0x0504, "data": b'\x68\x01'},  # 360 (scaled by 0.1 = 36.0)
        # Engine RPM Left
        {"address": 0x0600, "data": b'\x10\x27'},  # 10000 (scaled by 0.01 = 100%)
        # Master Caution
        {"address": 0x1012, "data": b'\x01\x00'},  # True
    ]


@pytest.fixture
def sample_aircraft_state():
    """Sample aircraft state for testing"""
    return {
        "aircraft": {
            "type": "FA-18C_hornet",
            "timestamp": "2025-01-18T12:00:00.000Z",
            "systems": {
                "engine": {
                    "ENGINE_RPM_LEFT": 100.0,
                    "ENGINE_RPM_RIGHT": 100.0,
                    "ENGINE_TEMP_LEFT": 650,
                    "ENGINE_TEMP_RIGHT": 648,
                    "FUEL_QUANTITY": 5000,
                },
                "navigation": {
                    "HEADING": 270,
                    "coordinates": {"lat": 36.123456, "lon": -115.654321}
                },
                "weapons": {
                    "selected": "AIM-120C",
                    "stations": {
                        "1": {"type": "AIM-9X", "count": 1},
                        "3": {"type": "AIM-120C", "count": 2}
                    }
                },
                "instruments": {
                    "IAS": 420,
                    "ALTITUDE": 15000,
                    "VERTICAL_VELOCITY": 0
                },
                "warnings": {
                    "MASTER_CAUTION": False
                }
            }
        }
    }


@pytest.fixture
def mock_reader_writer():
    """Create mock StreamReader and StreamWriter for TCP testing"""
    reader = AsyncMock()
    writer = AsyncMock()
    writer.close = AsyncMock()
    writer.wait_closed = AsyncMock()
    writer.write = MagicMock()
    writer.drain = AsyncMock()
    return reader, writer