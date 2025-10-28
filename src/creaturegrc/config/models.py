"""
Configuration models for CreatureGRC.

Supports two deployment modes:
- Agent: Lightweight, export-only, multiple profiles for consultants
- Server: Full platform with database and integrations
"""

from datetime import timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DeploymentMode(str, Enum):
    """Deployment mode"""

    AGENT = "agent"
    SERVER = "server"


# ==============================================================================
# Profile Configuration (Agent Mode)
# ==============================================================================


class ProfileConfig(BaseModel):
    """Agent profile configuration for multi-client management"""

    name: str = Field(..., description="Profile name (e.g., 'acme-corp')")
    mode: DeploymentMode = Field(DeploymentMode.AGENT, description="Deployment mode")
    description: Optional[str] = Field(None, description="Profile description")


class ServerConnectionConfig(BaseModel):
    """Connection settings for agent → server communication"""

    url: HttpUrl = Field(..., description="CreatureGRC server URL")
    api_key_file: Path = Field(..., description="Path to API key file")
    verify_ssl: bool = Field(True, description="Verify SSL certificates")
    timeout: int = Field(30, description="Request timeout in seconds")


class AgentConfig(BaseModel):
    """Agent-specific configuration"""

    device_id: Optional[str] = Field(None, description="Unique device identifier")
    evidence_cache_dir: Path = Field(
        Path("~/.config/creaturegrc/cache").expanduser(),
        description="Local evidence cache directory",
    )
    upload_interval: int = Field(3600, description="Evidence upload interval (seconds)")
    batch_size: int = Field(100, description="Evidence batch size for upload")
    retry_attempts: int = Field(3, description="Number of retry attempts for failed uploads")


class CollectionConfig(BaseModel):
    """Evidence collection configuration"""

    enabled_sources: list[str] = Field(
        default_factory=list, description="Enabled evidence sources"
    )
    frameworks: list[str] = Field(
        default_factory=lambda: ["soc2"], description="Target frameworks"
    )
    scan_interval: int = Field(3600, description="Scan interval in seconds")


# ==============================================================================
# Server Configuration
# ==============================================================================


class DatabaseConfig(BaseModel):
    """Database connection configuration"""

    host: str = Field("localhost", description="Database host")
    port: int = Field(5432, description="Database port")
    name: str = Field("grc_platform", description="Database name")
    user: str = Field("grc_user", description="Database user")
    password_file: Optional[Path] = Field(None, description="Path to password file")
    pool_size: int = Field(20, description="Connection pool size")
    pool_timeout: int = Field(30, description="Pool timeout in seconds")

    @field_validator("password_file")
    @classmethod
    def validate_password_file(cls, v: Optional[Path]) -> Optional[Path]:
        if v and not v.exists():
            raise ValueError(f"Password file not found: {v}")
        return v


class APIConfig(BaseModel):
    """API server configuration"""

    enabled: bool = Field(True, description="Enable API server")
    host: str = Field("0.0.0.0", description="API bind host")
    port: int = Field(8080, description="API port")
    workers: int = Field(4, description="Number of worker processes")
    cors_origins: list[str] = Field(default_factory=list, description="Allowed CORS origins")
    rate_limit: str = Field("100/minute", description="Rate limit")
    auth_method: Literal["api_key", "oauth2", "mtls"] = Field(
        "api_key", description="Authentication method"
    )


class EvidenceStorageConfig(BaseModel):
    """Evidence storage configuration"""

    storage_dir: Path = Field(
        Path("/var/lib/creaturegrc/evidence"), description="Evidence storage directory"
    )
    retention_days: int = Field(365, description="Evidence retention in days")
    compression: bool = Field(True, description="Enable compression")
    max_size_mb: int = Field(1024, description="Maximum evidence size in MB")


class IntegrationsConfig(BaseModel):
    """External integrations configuration"""

    config_dir: Path = Field(
        Path("/etc/creaturegrc/integrations"), description="Integrations config directory"
    )
    enabled: list[str] = Field(default_factory=list, description="Enabled integrations")


class AuditConfig(BaseModel):
    """Audit package generation configuration"""

    output_dir: Path = Field(
        Path("/var/lib/creaturegrc/audit-packages"),
        description="Audit package output directory",
    )
    formats: list[str] = Field(
        default_factory=lambda: ["pdf", "excel", "zip"], description="Output formats"
    )
    compress_packages: bool = Field(True, description="Compress audit packages")


# ==============================================================================
# Logging Configuration
# ==============================================================================


class LoggingConfig(BaseModel):
    """Logging configuration"""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        "INFO", description="Log level"
    )
    format: Literal["text", "json"] = Field("text", description="Log format")
    output: Literal["stdout", "file"] = Field("stdout", description="Log output")
    file: Optional[Path] = Field(None, description="Log file path")
    max_size_mb: int = Field(100, description="Maximum log file size in MB")
    backup_count: int = Field(5, description="Number of log backups")


# ==============================================================================
# Main Configuration
# ==============================================================================


class CreatureGRCConfig(BaseSettings):
    """
    Main CreatureGRC configuration.

    Loads from:
    1. Environment variables (CREATUREGRC_*)
    2. Config file (TOML)
    3. Defaults
    """

    model_config = SettingsConfigDict(
        env_prefix="CREATUREGRC_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Profile settings
    profile: ProfileConfig = Field(
        default_factory=lambda: ProfileConfig(name="default"),
        description="Profile configuration",
    )

    # Server connection (agent mode)
    server: Optional[ServerConnectionConfig] = Field(
        None, description="Server connection settings"
    )

    # Agent settings
    agent: Optional[AgentConfig] = Field(None, description="Agent configuration")

    # Collection settings
    collection: CollectionConfig = Field(
        default_factory=CollectionConfig, description="Evidence collection settings"
    )

    # Database (server mode)
    database: Optional[DatabaseConfig] = Field(None, description="Database configuration")

    # API (server mode)
    api: Optional[APIConfig] = Field(None, description="API configuration")

    # Evidence storage
    evidence: EvidenceStorageConfig = Field(
        default_factory=EvidenceStorageConfig, description="Evidence storage settings"
    )

    # Integrations (server mode)
    integrations: Optional[IntegrationsConfig] = Field(
        None, description="Integrations configuration"
    )

    # Audit generation
    audit: AuditConfig = Field(default_factory=AuditConfig, description="Audit configuration")

    # Logging
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig, description="Logging configuration"
    )

    @property
    def mode(self) -> DeploymentMode:
        """Detect deployment mode"""
        if self.database is not None:
            return DeploymentMode.SERVER
        if self.server is not None:
            return DeploymentMode.AGENT
        return DeploymentMode.AGENT  # Default to agent

    def is_agent_mode(self) -> bool:
        """Check if running in agent mode"""
        return self.mode == DeploymentMode.AGENT

    def is_server_mode(self) -> bool:
        """Check if running in server mode"""
        return self.mode == DeploymentMode.SERVER


# ==============================================================================
# Integration-Specific Configurations
# ==============================================================================


class IntegrationConfig(BaseModel):
    """Base configuration for integrations"""

    enabled: bool = Field(True, description="Enable this integration")
    api_url: str = Field(..., description="API URL")
    token_file: Optional[Path] = Field(None, description="Path to API token file")
    verify_ssl: bool = Field(True, description="Verify SSL certificates")
    timeout: int = Field(30, description="Request timeout in seconds")
    sync_interval: int = Field(86400, description="Sync interval in seconds (default: 24h)")


class NetboxIntegrationConfig(IntegrationConfig):
    """Netbox integration configuration"""

    api_url: str = Field(..., description="Netbox API URL")
    mapping: dict[str, Any] = Field(
        default_factory=dict, description="Device role to creature class mapping"
    )
    filters: dict[str, Any] = Field(
        default_factory=dict, description="Netbox query filters (tags, status, etc.)"
    )


class WazuhIntegrationConfig(IntegrationConfig):
    """Wazuh integration configuration"""

    api_url: str = Field(..., description="Wazuh API URL")
    username: Optional[str] = Field(None, description="Wazuh username")
    password_file: Optional[Path] = Field(None, description="Path to password file")
    collect_alerts: bool = Field(True, description="Collect security alerts")
    collect_vulnerabilities: bool = Field(True, description="Collect vulnerability scans")
    collect_compliance: bool = Field(True, description="Collect compliance check results")


class KeycloakIntegrationConfig(IntegrationConfig):
    """Keycloak integration configuration"""

    api_url: str = Field(..., description="Keycloak API URL")
    realm: str = Field("master", description="Keycloak realm")
    client_id: str = Field(..., description="Client ID")
    client_secret_file: Path = Field(..., description="Path to client secret file")
    sync_users: bool = Field(True, description="Sync users")
    sync_roles: bool = Field(True, description="Sync roles")
    sync_events: bool = Field(True, description="Sync authentication events")
