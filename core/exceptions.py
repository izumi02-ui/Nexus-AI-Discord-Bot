"""
Project Nexus

Custom Exceptions
"""


class NexusError(Exception):
    """Base Nexus Exception."""


class ProviderError(NexusError):
    """AI Provider Error."""


class MemoryError(NexusError):
    """Memory Error."""


class DatabaseError(NexusError):
    """Database Error."""
