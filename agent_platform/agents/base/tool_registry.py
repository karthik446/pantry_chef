from typing import Dict, Callable, Any
from functools import wraps


class ToolRegistry:
    """Registry for agent tools."""

    def __init__(self):
        self._tools: Dict[str, Callable] = {}

    def register(self, name: str = None):
        """Decorator to register a tool."""

        def decorator(func: Callable):
            tool_name = name or func.__name__

            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            self._tools[tool_name] = wrapper
            return wrapper

        return decorator

    def get_tool(self, name: str) -> Callable:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> Dict[str, Callable]:
        """List all registered tools."""
        return self._tools
