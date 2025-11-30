"""
Systerd exception hierarchy and error handling utilities.
"""

from __future__ import annotations

import logging
import traceback
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ErrorCode(Enum):
    """Standard error codes for systerd operations."""
    
    # General errors (1xxx)
    UNKNOWN = 1000
    INVALID_INPUT = 1001
    TIMEOUT = 1002
    RESOURCE_EXHAUSTED = 1003
    NOT_IMPLEMENTED = 1004
    
    # Permission errors (2xxx)
    PERMISSION_DENIED = 2000
    PERMISSION_REQUIRED = 2001
    INVALID_TOKEN = 2002
    
    # System errors (3xxx)
    PROCESS_NOT_FOUND = 3000
    SERVICE_NOT_FOUND = 3001
    SERVICE_FAILED = 3002
    DBUS_ERROR = 3003
    SYSTEMD_ERROR = 3004
    
    # MCP errors (4xxx)
    TOOL_NOT_FOUND = 4000
    TOOL_EXECUTION_FAILED = 4001
    INVALID_PARAMETERS = 4002
    
    # Storage errors (5xxx)
    STORAGE_ERROR = 5000
    DB_CORRUPTED = 5001
    DISK_FULL = 5002
    
    # Network errors (6xxx)
    NETWORK_ERROR = 6000
    CONNECTION_FAILED = 6001
    DNS_ERROR = 6002


class SysterdError(Exception):
    """Base exception for all systerd errors."""
    
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.UNKNOWN,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
        self.cause = cause
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to JSON-serializable dict."""
        result = {
            "error": self.__class__.__name__,
            "message": self.message,
            "code": self.code.value,
            "code_name": self.code.name,
        }
        if self.details:
            result["details"] = self.details
        if self.cause:
            result["cause"] = str(self.cause)
        return result
    
    def log(self, level: int = logging.ERROR):
        """Log this exception with context."""
        logger.log(
            level,
            f"{self.__class__.__name__}: {self.message} (code={self.code.name})",
            extra={"details": self.details, "cause": self.cause},
        )


class PermissionError(SysterdError):
    """Permission-related errors."""
    
    def __init__(self, message: str, **kwargs):
        kwargs.setdefault("code", ErrorCode.PERMISSION_DENIED)
        super().__init__(message, **kwargs)


class ProcessError(SysterdError):
    """Process management errors."""
    
    def __init__(self, message: str, **kwargs):
        kwargs.setdefault("code", ErrorCode.PROCESS_NOT_FOUND)
        super().__init__(message, **kwargs)


class ServiceError(SysterdError):
    """Systemd service management errors."""
    
    def __init__(self, message: str, **kwargs):
        kwargs.setdefault("code", ErrorCode.SERVICE_FAILED)
        super().__init__(message, **kwargs)


class MCPError(SysterdError):
    """MCP tool execution errors."""
    
    def __init__(self, message: str, **kwargs):
        kwargs.setdefault("code", ErrorCode.TOOL_EXECUTION_FAILED)
        super().__init__(message, **kwargs)


class StorageError(SysterdError):
    """Storage and database errors."""
    
    def __init__(self, message: str, **kwargs):
        kwargs.setdefault("code", ErrorCode.STORAGE_ERROR)
        super().__init__(message, **kwargs)


class NetworkError(SysterdError):
    """Network-related errors."""
    
    def __init__(self, message: str, **kwargs):
        kwargs.setdefault("code", ErrorCode.NETWORK_ERROR)
        super().__init__(message, **kwargs)


class TimeoutError(SysterdError):
    """Operation timeout errors."""
    
    def __init__(self, message: str, timeout: float, **kwargs):
        kwargs.setdefault("code", ErrorCode.TIMEOUT)
        kwargs.setdefault("details", {})
        kwargs["details"]["timeout"] = timeout
        super().__init__(message, **kwargs)


def safe_execute(func, *args, error_msg: str = None, default=None, log_level=logging.ERROR, **kwargs):
    """
    Execute function with comprehensive error handling.
    
    Args:
        func: Function to execute
        *args: Positional arguments for func
        error_msg: Custom error message prefix
        default: Default return value on error
        log_level: Logging level for errors
        **kwargs: Keyword arguments for func
    
    Returns:
        Function result or default value on error
    """
    try:
        return func(*args, **kwargs)
    except SysterdError as e:
        e.log(log_level)
        if error_msg:
            logger.log(log_level, f"{error_msg}: {e.message}")
        return default
    except Exception as e:
        logger.log(
            log_level,
            f"{error_msg or 'Operation failed'}: {type(e).__name__}: {e}",
            exc_info=True,
        )
        return default


async def safe_execute_async(func, *args, error_msg: str = None, default=None, log_level=logging.ERROR, **kwargs):
    """Async version of safe_execute."""
    try:
        return await func(*args, **kwargs)
    except SysterdError as e:
        e.log(log_level)
        if error_msg:
            logger.log(log_level, f"{error_msg}: {e.message}")
        return default
    except Exception as e:
        logger.log(
            log_level,
            f"{error_msg or 'Async operation failed'}: {type(e).__name__}: {e}",
            exc_info=True,
        )
        return default


def format_exception_details(exc: Exception) -> Dict[str, Any]:
    """Extract detailed information from exception."""
    return {
        "type": type(exc).__name__,
        "message": str(exc),
        "traceback": traceback.format_exc(),
    }
