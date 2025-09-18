"""
Configuration management for DCS-BIOS MCP Server
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class DCSBIOSConfig:
    """DCS-BIOS connection configuration"""
    host: str = "239.255.50.10"  # Multicast address
    port: int = 5010
    multicast: bool = True
    tcp_host: str = "127.0.0.1"
    tcp_port: int = 7778
    
    
@dataclass
class MCPServerConfig:
    """MCP Server configuration"""
    host: str = "127.0.0.1"
    port: int = 8080
    enable_websocket: bool = True
    

@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    file: str = "logs/dcs_mcp_server.log"
    

@dataclass
class Config:
    """Main configuration class"""
    dcs_bios: DCSBIOSConfig = field(default_factory=DCSBIOSConfig)
    mcp_server: MCPServerConfig = field(default_factory=MCPServerConfig)
    aircraft_filter: List[str] = field(default_factory=lambda: [
        "FA-18C_hornet",
        "F-16C_50", 
        "A-10C",
        "F-14",
        "AH-64D"
    ])
    data_update_rate: int = 10  # Updates per second
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    @classmethod
    def load(cls, config_path: Optional[str] = None) -> 'Config':
        """Load configuration from file or use defaults"""
        if config_path is None:
            # Look for config.json in various locations
            possible_paths = [
                Path("config.json"),
                Path("config/config.json"),
                Path(__file__).parent.parent / "config.json",
                Path.home() / ".dcs-mcp" / "config.json"
            ]
            
            for path in possible_paths:
                if path.exists():
                    config_path = str(path)
                    break
        
        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                data = json.load(f)
                
            # Parse nested configurations
            config = cls()
            
            if 'dcs_bios' in data:
                config.dcs_bios = DCSBIOSConfig(**data['dcs_bios'])
            
            if 'mcp_server' in data:
                config.mcp_server = MCPServerConfig(**data['mcp_server'])
                
            if 'logging' in data:
                config.logging = LoggingConfig(**data['logging'])
                
            if 'aircraft_filter' in data:
                config.aircraft_filter = data['aircraft_filter']
                
            if 'data_update_rate' in data:
                config.data_update_rate = data['data_update_rate']
                
            return config
        
        # Return default configuration
        return cls()
    
    def save(self, config_path: str = "config.json"):
        """Save configuration to file"""
        data = {
            'dcs_bios': {
                'host': self.dcs_bios.host,
                'port': self.dcs_bios.port,
                'multicast': self.dcs_bios.multicast,
                'tcp_host': self.dcs_bios.tcp_host,
                'tcp_port': self.dcs_bios.tcp_port
            },
            'mcp_server': {
                'host': self.mcp_server.host,
                'port': self.mcp_server.port,
                'enable_websocket': self.mcp_server.enable_websocket
            },
            'aircraft_filter': self.aircraft_filter,
            'data_update_rate': self.data_update_rate,
            'logging': {
                'level': self.logging.level,
                'file': self.logging.file
            }
        }
        
        with open(config_path, 'w') as f:
            json.dump(data, f, indent=2)