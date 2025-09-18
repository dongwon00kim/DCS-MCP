"""
Tests for Logging Configuration
"""

import logging
import tempfile
from pathlib import Path

import pytest

from logging_config import setup_logging


class TestLogging:
    """Test logging configuration"""
    
    def test_setup_logging_default(self):
        """Test default logging setup"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            
            # Setup logging
            setup_logging(log_level="INFO", log_file=str(log_file))
            
            # Get root logger
            root_logger = logging.getLogger()
            
            # Check log level
            assert root_logger.level == logging.INFO
            
            # Check handlers
            assert len(root_logger.handlers) >= 2  # Console and file
            
            # Find console handler
            console_handler = None
            file_handler = None
            for handler in root_logger.handlers:
                if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                    console_handler = handler
                elif isinstance(handler, logging.handlers.RotatingFileHandler):
                    file_handler = handler
            
            assert console_handler is not None
            assert file_handler is not None
            
            # Test logging
            test_logger = logging.getLogger("test")
            test_logger.info("Test message")
            
            # Check log file was created
            assert log_file.exists()
            
            # Clean up handlers
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
                handler.close()
    
    def test_setup_logging_debug_level(self):
        """Test debug level logging setup"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "debug.log"
            
            setup_logging(log_level="DEBUG", log_file=str(log_file))
            
            root_logger = logging.getLogger()
            assert root_logger.level == logging.DEBUG
            
            # Clean up
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
                handler.close()
    
    def test_log_file_creation(self):
        """Test that log file and directory are created"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Use nested directory that doesn't exist
            log_file = Path(temp_dir) / "logs" / "nested" / "test.log"
            
            setup_logging(log_file=str(log_file))
            
            # Directory should be created
            assert log_file.parent.exists()
            
            # Log something
            logger = logging.getLogger("test")
            logger.info("Test message")
            
            # File should be created
            assert log_file.exists()
            
            # Clean up
            root_logger = logging.getLogger()
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
                handler.close()
    
    def test_rotating_file_handler(self):
        """Test that rotating file handler is configured correctly"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "rotate.log"
            
            setup_logging(log_file=str(log_file))
            
            # Find the rotating file handler
            root_logger = logging.getLogger()
            file_handler = None
            for handler in root_logger.handlers:
                if isinstance(handler, logging.handlers.RotatingFileHandler):
                    file_handler = handler
                    break
            
            assert file_handler is not None
            assert file_handler.maxBytes == 10 * 1024 * 1024  # 10MB
            assert file_handler.backupCount == 5
            
            # Clean up
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
                handler.close()
    
    def test_logger_hierarchy(self):
        """Test that specific loggers have correct levels"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "hierarchy.log"
            
            setup_logging(log_file=str(log_file))
            
            # Check specific logger levels
            asyncio_logger = logging.getLogger('asyncio')
            assert asyncio_logger.level == logging.WARNING
            
            websockets_logger = logging.getLogger('websockets')
            assert websockets_logger.level == logging.WARNING
            
            # Clean up
            root_logger = logging.getLogger()
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
                handler.close()
    
    def test_formatter_configuration(self):
        """Test that formatters are configured correctly"""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "format.log"
            
            setup_logging(log_file=str(log_file))
            
            root_logger = logging.getLogger()
            
            # Check console formatter
            console_handler = None
            file_handler = None
            for handler in root_logger.handlers:
                if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                    console_handler = handler
                elif isinstance(handler, logging.handlers.RotatingFileHandler):
                    file_handler = handler
            
            # Console formatter should be simpler
            if console_handler and console_handler.formatter:
                console_format = console_handler.formatter._fmt
                assert 'asctime' in console_format
                assert 'levelname' in console_format
                assert 'message' in console_format
            
            # File formatter should be more detailed
            if file_handler and file_handler.formatter:
                file_format = file_handler.formatter._fmt
                assert 'asctime' in file_format
                assert 'levelname' in file_format
                assert 'filename' in file_format
                assert 'lineno' in file_format
                assert 'message' in file_format
            
            # Clean up
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
                handler.close()