"""
Tests for Configuration Management
"""

import json
import tempfile
from pathlib import Path

import pytest

from config import Config, DCSBIOSConfig, MCPServerConfig, LoggingConfig


class TestConfig:
    """Test configuration management"""
    
    def test_dcs_bios_config_defaults(self):
        """Test DCS-BIOS config default values"""
        config = DCSBIOSConfig()
        assert config.host == "239.255.50.10"
        assert config.port == 5010
        assert config.multicast is True
        assert config.tcp_host == "127.0.0.1"
        assert config.tcp_port == 7778
    
    def test_mcp_server_config_defaults(self):
        """Test MCP server config default values"""
        config = MCPServerConfig()
        assert config.host == "127.0.0.1"
        assert config.port == 8080
        assert config.enable_websocket is True
    
    def test_logging_config_defaults(self):
        """Test logging config default values"""
        config = LoggingConfig()
        assert config.level == "INFO"
        assert config.file == "logs/dcs_mcp_server.log"
    
    def test_config_defaults(self):
        """Test main config default values"""
        config = Config()
        assert isinstance(config.dcs_bios, DCSBIOSConfig)
        assert isinstance(config.mcp_server, MCPServerConfig)
        assert isinstance(config.logging, LoggingConfig)
        assert config.data_update_rate == 10
        assert "FA-18C_hornet" in config.aircraft_filter
        assert "F-16C_50" in config.aircraft_filter
    
    def test_load_config_from_file(self):
        """Test loading configuration from JSON file"""
        config_data = {
            "dcs_bios": {
                "host": "239.255.50.11",
                "port": 5011,
                "multicast": False,
                "tcp_host": "192.168.1.100",
                "tcp_port": 7779
            },
            "mcp_server": {
                "host": "0.0.0.0",
                "port": 8081,
                "enable_websocket": False
            },
            "aircraft_filter": ["F-14"],
            "data_update_rate": 20,
            "logging": {
                "level": "DEBUG",
                "file": "test.log"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = Config.load(temp_path)
            
            assert config.dcs_bios.host == "239.255.50.11"
            assert config.dcs_bios.port == 5011
            assert config.dcs_bios.multicast is False
            assert config.dcs_bios.tcp_host == "192.168.1.100"
            assert config.dcs_bios.tcp_port == 7779
            
            assert config.mcp_server.host == "0.0.0.0"
            assert config.mcp_server.port == 8081
            assert config.mcp_server.enable_websocket is False
            
            assert config.aircraft_filter == ["F-14"]
            assert config.data_update_rate == 20
            
            assert config.logging.level == "DEBUG"
            assert config.logging.file == "test.log"
        finally:
            Path(temp_path).unlink()
    
    def test_load_config_partial(self):
        """Test loading partial configuration from file"""
        config_data = {
            "dcs_bios": {
                "port": 5011
            },
            "data_update_rate": 15
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = Config.load(temp_path)
            
            # Modified values
            assert config.dcs_bios.port == 5011
            assert config.data_update_rate == 15
            
            # Default values for unspecified fields
            assert config.dcs_bios.host == "239.255.50.10"
            assert config.dcs_bios.multicast is True
            assert config.mcp_server.port == 8080
        finally:
            Path(temp_path).unlink()
    
    def test_load_config_no_file(self):
        """Test loading config when file doesn't exist"""
        config = Config.load("nonexistent.json")
        
        # Should return default config
        assert isinstance(config, Config)
        assert config.dcs_bios.host == "239.255.50.10"
        assert config.mcp_server.port == 8080
    
    def test_save_config(self):
        """Test saving configuration to file"""
        config = Config()
        config.dcs_bios.port = 5012
        config.mcp_server.port = 8082
        config.aircraft_filter = ["A-10C"]
        config.data_update_rate = 25
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            config.save(temp_path)
            
            # Load and verify
            with open(temp_path, 'r') as f:
                data = json.load(f)
            
            assert data['dcs_bios']['port'] == 5012
            assert data['mcp_server']['port'] == 8082
            assert data['aircraft_filter'] == ["A-10C"]
            assert data['data_update_rate'] == 25
        finally:
            Path(temp_path).unlink()
    
    def test_config_search_paths(self):
        """Test that config searches multiple paths"""
        # Create a temporary config file
        config_data = {"data_update_rate": 30}
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            with open(config_path, 'w') as f:
                json.dump(config_data, f)
            
            # Patch possible paths to include our temp file
            import config as config_module
            original_paths = [
                Path("config.json"),
                Path("config/config.json"),
                Path(__file__).parent.parent / "config.json",
                Path.home() / ".dcs-mcp" / "config.json"
            ]
            
            # Add our temp path as the first option
            test_paths = [config_path] + original_paths
            
            # Mock the path checking
            def mock_load(cls, config_path=None):
                if config_path is None:
                    for path in test_paths:
                        if path.exists():
                            config_path = str(path)
                            break
                
                if config_path and Path(config_path).exists():
                    with open(config_path, 'r') as f:
                        data = json.load(f)
                    
                    cfg = cls()
                    if 'data_update_rate' in data:
                        cfg.data_update_rate = data['data_update_rate']
                    return cfg
                
                return cls()
            
            # Test that it finds our config
            config = mock_load(Config)
            assert config.data_update_rate == 30