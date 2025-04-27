"""Exceptions module for OpenNebula client."""


class OpenNebulaError(Exception):
    """Base exception class for OpenNebula client."""

    message = 'An unknown exception occurred.'

    def __init__(self, message=None, code=None):
        """Initialize exception class with optional message and code."""
        if message:
            self.message = message
        if code:
            self.code = code

    def __str__(self):
        """Serialize exception to string using it's message."""
        return self.message


class BadRequest(OpenNebulaError):
    """General purpose exception class."""


class Unauthorized(BadRequest):
    """Raised when invalid credentials are provided."""
    message = 'Unauthorized: bad credentials.'
