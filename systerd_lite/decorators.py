"""
Decorators for MCP tool authorization.
"""

from functools import wraps
import logging
from typing import Callable

from .permissions import Permission, PermissionManager
from .exceptions import SysterdError, ErrorCode

logger = logging.getLogger(__name__)


def require_permission(tool_name: str, default_permission: Permission = Permission.AI_ASK):
    """
    Decorator to enforce permission checks on MCP tool functions.
    
    Args:
        tool_name: Name of the tool (used for permission lookup)
        default_permission: Default permission if not configured
    
    Raises:
        SysterdError: If permission is denied
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(self, *args, **kwargs):
            # Get permission manager from context
            permission_manager = getattr(self.context, 'permission_manager', None)
            
            if permission_manager:
                # Check permission
                perm = permission_manager.check(tool_name)
                
                if perm == Permission.DISABLED:
                    logger.warning(f"Permission denied for tool '{tool_name}': disabled")
                    raise SysterdError(
                        f"Tool '{tool_name}' is disabled",
                        code=ErrorCode.PERMISSION_DENIED,
                        details={
                            "tool": tool_name,
                            "permission": perm.value,
                            "reason": "Tool is disabled by permission policy"
                        }
                    )
                
                if perm == Permission.AI_ASK:
                    logger.info(f"Tool '{tool_name}' requires human approval (AI_ASK mode)")
                    # TODO: Implement human approval workflow via Gradio
                    # For now, allow execution but log it
                
                # Log permission check
                logger.debug(f"Permission '{perm.value}' granted for tool '{tool_name}'")
            else:
                # No permission manager - allow by default (dev mode)
                logger.debug(f"No permission manager, allowing '{tool_name}' (dev mode)")
            
            # Execute tool
            return await func(self, *args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(self, *args, **kwargs):
            # Get permission manager from context
            permission_manager = getattr(self.context, 'permission_manager', None)
            
            if permission_manager:
                # Check permission
                perm = permission_manager.check(tool_name)
                
                if perm == Permission.DISABLED:
                    logger.warning(f"Permission denied for tool '{tool_name}': disabled")
                    raise SysterdError(
                        f"Tool '{tool_name}' is disabled",
                        code=ErrorCode.PERMISSION_DENIED,
                        details={
                            "tool": tool_name,
                            "permission": perm.value,
                            "reason": "Tool is disabled by permission policy"
                        }
                    )
                
                if perm == Permission.AI_ASK:
                    logger.info(f"Tool '{tool_name}' requires human approval (AI_ASK mode)")
                
                logger.debug(f"Permission '{perm.value}' granted for tool '{tool_name}'")
            else:
                logger.debug(f"No permission manager, allowing '{tool_name}' (dev mode)")
            
            # Execute tool
            return func(self, *args, **kwargs)
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def permission_audit(tool_name: str):
    """
    Decorator to log all tool invocations for audit trail.
    
    Args:
        tool_name: Name of the tool being audited
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(self, *args, **kwargs):
            # Log invocation (avoid 'args' conflict with logging.LogRecord)
            logger.info(
                f"[AUDIT] Tool '{tool_name}' invoked",
                extra={
                    "tool": tool_name,
                    "tool_args": str(args)[:100],  # Renamed to avoid conflict
                    "tool_kwargs": str(kwargs)[:100]  # Renamed to avoid conflict
                }
            )
            
            # Publish to NeuroBus if available
            if hasattr(self.context, 'neurobus'):
                self.context.neurobus.publish(
                    "audit",
                    "tool_invocation",
                    {
                        "tool": tool_name,
                        "args_count": len(args),
                        "kwargs_keys": list(kwargs.keys())
                    }
                )
            
            try:
                result = await func(self, *args, **kwargs)
                
                # Log success
                logger.info(f"[AUDIT] Tool '{tool_name}' succeeded")
                
                return result
            except Exception as e:
                # Log failure
                logger.error(
                    f"[AUDIT] Tool '{tool_name}' failed: {e}",
                    exc_info=True
                )
                raise
        
        @wraps(func)
        def sync_wrapper(self, *args, **kwargs):
            logger.info(
                f"[AUDIT] Tool '{tool_name}' invoked",
                extra={
                    "tool": tool_name,
                    "args": str(args)[:100],
                    "kwargs": str(kwargs)[:100]
                }
            )
            
            if hasattr(self.context, 'neurobus'):
                self.context.neurobus.publish(
                    "audit",
                    "tool_invocation",
                    {
                        "tool": tool_name,
                        "args_count": len(args),
                        "kwargs_keys": list(kwargs.keys())
                    }
                )
            
            try:
                result = func(self, *args, **kwargs)
                logger.info(f"[AUDIT] Tool '{tool_name}' succeeded")
                return result
            except Exception as e:
                logger.error(
                    f"[AUDIT] Tool '{tool_name}' failed: {e}",
                    exc_info=True
                )
                raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator
