# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a DCS MCP Server project that integrates DCS World flight simulator with Large Language Models (LLMs) through the Model Context Protocol (MCP). The server collects real-time aircraft data from DCS-BIOS and provides it to LLMs like Claude or ChatGPT.

## Key Architecture

### Core Components
- **DCS-BIOS Integration**: Located in `dcs-bios/` - a complete DCS-BIOS implementation for extracting aircraft data
- **MCP Server**: Main server implementation in `src/` directory
- **Main Entry Point**: `src/main.py` - currently a stub that needs implementation

### Data Flow
1. DCS World → DCS-BIOS (UDP multicast on `239.255.50.10:5010`)
2. DCS-BIOS → MCP Server (data collection and parsing)
3. MCP Server → LLM (via MCP protocol)
4. LLM → MCP Server → DCS-BIOS (control commands via TCP port `7778`)

## Development Commands

### Python Environment (using uv - recommended)
```bash
# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows

# Install dependencies
uv sync

# Install with dev dependencies
uv sync --extra dev
```

### Python Environment (using pip)
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Install package
pip install -e .

# Install with dev dependencies
pip install -e ".[dev]"
```

### Running the Server
```bash
python src/main.py
```

### Testing
```bash
# Run unit tests (to be implemented)
python -m pytest tests/

# Run integration tests with DCS World
python -m pytest tests/integration/
```

### DCS-BIOS Lua Tests
```bash
# Run DCS-BIOS Lua test suite
cd dcs-bios/Scripts/DCS-BIOS/test
lua TestSuite.lua
```

## Important Implementation Notes

### DCS-BIOS Data Format
- Aircraft modules are in `dcs-bios/Scripts/DCS-BIOS/lib/modules/aircraft_modules/`
- Each aircraft has specific control definitions and data exports
- Test files in `dcs-bios/Scripts/DCS-BIOS/test/` provide examples of control handling

### MCP Protocol Requirements
The server must implement these MCP tools:
- `get_aircraft_status` - Return current aircraft state
- `get_system_data` - Query specific systems
- `set_control` - Execute aircraft controls
- `monitor_changes` - Real-time monitoring
- `execute_procedure` - Complex command sequences

### Network Configuration
- **DCS-BIOS Receive**: UDP multicast `239.255.50.10:5010`
- **DCS-BIOS Control**: TCP `localhost:7778`
- **MCP Server**: Default port `8080`

### Supported Aircraft
Primary aircraft modules to support (found in aircraft_modules/):
- F/A-18C Hornet (`FA-18C_hornet.lua`)
- F-16C Viper (`F-16C_50.lua`)
- A-10C II (`A-10C.lua`)
- F-14 Tomcat (`F-14.lua`)
- AH-64D Apache (`AH-64D.lua`)

## Code Patterns

### DCS-BIOS Control Definition Pattern
Controls in aircraft modules follow this pattern:
```lua
defineToggleSwitch("CONTROL_NAME", device_id, button_id, position_id, "Category", "Description")
definePotentiometer("POT_NAME", device_id, button_id, position_id, {min, max}, "Category", "Description")
defineIndicatorLight("LIGHT_NAME", position_id, "Category", "Description")
```

### Data Processing Flow
1. Parse UDP packets from DCS-BIOS
2. Extract control states based on memory addresses
3. Format as JSON for MCP protocol
4. Handle control commands and convert to DCS-BIOS format

## Project Status

Current implementation status:
- ✅ DCS-BIOS library included
- ✅ Project structure defined
- ✅ MCP server implementation completed
- ✅ UDP multicast receiver implemented
- ✅ TCP control sender implemented
- ✅ Data parsing engine implemented
- ✅ REST API for debugging implemented
- ✅ WebSocket support added
- ✅ Test suite created
- ⏳ Windows installer needed

## File Organization

- `dcs-bios/` - Complete DCS-BIOS implementation (do not modify)
- `src/` - MCP server source code
  - `main.py` - Main entry point
  - `mcp_server.py` - MCP server implementation
  - `dcs_bios_receiver.py` - UDP multicast receiver
  - `dcs_bios_sender.py` - TCP control sender
  - `data_parser.py` - DCS-BIOS data parser
  - `config.py` - Configuration management
  - `logging_config.py` - Logging setup
- `tests/` - Test files
  - Unit tests for all modules
  - `integration/` - Integration tests
- `config.json` - Server configuration
- `pyproject.toml` - Project metadata and dependencies
- `pytest.ini` - Test configuration