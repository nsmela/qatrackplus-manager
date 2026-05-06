from __future__ import annotations

class QATManagerError(Exception):
    """Base exception."""

class TransportError(QATManagerError):
    """Command execution or file operation failed."""

class ConfigError(QATManagerError):
    """State file or settings are missing or invalid."""

class InstallError(QATManagerError):
    """Installation step failed."""

class DependencyError(QATManagerError):
    """Python dependency could not be resolved or installed."""

class DatabaseError(QATManagerError):
    """Database operation failed."""

class MigrationError(InstallError):
    """Django migrations failed."""
