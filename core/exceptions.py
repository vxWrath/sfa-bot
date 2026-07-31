__all__ = ["CommandNotFound", "SFAException"]


class SFAException(Exception):
    """Base class for SFA exceptions."""


class CommandNotFound(SFAException):
    """Raised when a command is expected but not found in the in-memory store."""

    def __init__(self, name: str):
        super().__init__(f"Command with name '{name}' not found in the in-memory store.")
        self.name = name
