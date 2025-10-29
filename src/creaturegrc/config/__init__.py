"""
Configuration management for CreatureGRC.

Supports agent and server modes with profile management for consultants.
"""

from creaturegrc.config.loader import (
    load_config,
    detect_mode,
    get_active_profile,
    list_profiles,
    set_active_profile,
    delete_profile,
    validate_config,
)

from creaturegrc.config.models import (
    CreatureGRCConfig,
    DeploymentMode,
    ProfileConfig,
    ServerConnectionConfig,
    AgentConfig,
    DatabaseConfig,
    APIConfig,
    LoggingConfig,
)

__all__ = [
    # Loaders
    "load_config",
    "detect_mode",
    "get_active_profile",
    "list_profiles",
    "set_active_profile",
    "delete_profile",
    "validate_config",
    # Models
    "CreatureGRCConfig",
    "DeploymentMode",
    "ProfileConfig",
    "ServerConnectionConfig",
    "AgentConfig",
    "DatabaseConfig",
    "APIConfig",
    "LoggingConfig",
]
