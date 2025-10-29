"""
Configuration loading and profile management.
"""

import os
import toml
from pathlib import Path
from typing import Optional

from rich.console import Console

from creaturegrc.config.models import CreatureGRCConfig, DeploymentMode

console = Console()


# Configuration paths
DEFAULT_CONFIG_DIR = Path("~/.config/creaturegrc").expanduser()
DEFAULT_PROFILES_DIR = DEFAULT_CONFIG_DIR / "profiles"
DEFAULT_CREDENTIALS_DIR = DEFAULT_CONFIG_DIR / "credentials"
SYSTEM_CONFIG_DIR = Path("/etc/creaturegrc")


def get_config_paths() -> tuple[Path, Path, Path]:
    """Get configuration directory paths"""
    config_dir = Path(os.getenv("CREATUREGRC_CONFIG_DIR", DEFAULT_CONFIG_DIR))
    profiles_dir = config_dir / "profiles"
    credentials_dir = config_dir / "credentials"

    # Create directories if they don't exist
    config_dir.mkdir(parents=True, exist_ok=True)
    profiles_dir.mkdir(parents=True, exist_ok=True)
    credentials_dir.mkdir(parents=True, exist_ok=True)
    credentials_dir.chmod(0o700)  # Secure permissions

    return config_dir, profiles_dir, credentials_dir


def get_active_profile() -> str:
    """Get the currently active profile name"""
    # 1. Check environment variable
    if profile := os.getenv("CREATUREGRC_PROFILE"):
        return profile

    # 2. Check active config link
    config_dir, _, _ = get_config_paths()
    active_config = config_dir / "config.toml"

    if active_config.is_symlink():
        # Extract profile name from symlink target
        target = active_config.readlink()
        if "profiles/" in str(target):
            return target.stem

    # 3. Check for default profile
    _, profiles_dir, _ = get_config_paths()
    if (profiles_dir / "default.toml").exists():
        return "default"

    # 4. No profile configured
    return "default"


def list_profiles() -> list[str]:
    """List available profiles"""
    _, profiles_dir, _ = get_config_paths()
    return [p.stem for p in profiles_dir.glob("*.toml")]


def load_profile_config(profile_name: str) -> dict:
    """Load configuration from profile file"""
    _, profiles_dir, _ = get_config_paths()
    profile_path = profiles_dir / f"{profile_name}.toml"

    if not profile_path.exists():
        raise FileNotFoundError(f"Profile not found: {profile_name}")

    return toml.load(profile_path)


def save_profile_config(profile_name: str, config: dict) -> None:
    """Save configuration to profile file"""
    _, profiles_dir, _ = get_config_paths()
    profile_path = profiles_dir / f"{profile_name}.toml"

    with open(profile_path, "w") as f:
        toml.dump(config, f)

    console.print(f"[green]Profile '{profile_name}' saved to {profile_path}[/green]")


def set_active_profile(profile_name: str) -> None:
    """Set the active profile by creating/updating symlink"""
    config_dir, profiles_dir, _ = get_config_paths()
    profile_path = profiles_dir / f"{profile_name}.toml"

    if not profile_path.exists():
        raise FileNotFoundError(f"Profile not found: {profile_name}")

    active_config = config_dir / "config.toml"

    # Remove existing link or file
    if active_config.exists() or active_config.is_symlink():
        active_config.unlink()

    # Create new symlink
    active_config.symlink_to(profile_path)

    console.print(f"[green]Switched to profile: {profile_name}[/green]")


def delete_profile(profile_name: str) -> None:
    """Delete a profile"""
    if profile_name == "default":
        raise ValueError("Cannot delete default profile")

    _, profiles_dir, _ = get_config_paths()
    profile_path = profiles_dir / f"{profile_name}.toml"

    if not profile_path.exists():
        raise FileNotFoundError(f"Profile not found: {profile_name}")

    profile_path.unlink()
    console.print(f"[yellow]Profile '{profile_name}' deleted[/yellow]")

    # If this was the active profile, switch to default
    if get_active_profile() == profile_name:
        if "default" in list_profiles():
            set_active_profile("default")
        else:
            console.print("[yellow]Warning: No default profile exists[/yellow]")


def load_config(
    profile: Optional[str] = None,
    config_file: Optional[Path] = None,
) -> CreatureGRCConfig:
    """
    Load CreatureGRC configuration with correct precedence.

    Priority order (highest to lowest):
    1. Environment variables (CREATUREGRC_*)
    2. Explicit config file (--config flag)
    3. Profile file (~/.config/creaturegrc/profiles/{profile}.toml)
    4. Active profile (~/.config/creaturegrc/config.toml)
    5. System config (/etc/creaturegrc/server.toml) if in server mode
    6. Defaults

    This ensures environment variables can override file settings for containers/CI.
    """

    # Build file config data (lowest to highest priority)
    file_config_data = {}

    # 1. System config (lowest priority file)
    system_config = SYSTEM_CONFIG_DIR / "server.toml"
    if system_config.exists():
        file_config_data.update(toml.load(system_config))

    # 2. Profile config
    if not config_file:
        profile_name = profile or get_active_profile()
        try:
            file_config_data.update(load_profile_config(profile_name))
        except FileNotFoundError:
            console.print(
                f"[yellow]Warning: Profile '{profile_name}' not found, using defaults[/yellow]"
            )

    # 3. Explicit config file (highest priority file)
    if config_file:
        file_config_data.update(toml.load(config_file))

    # Create config with custom settings source that reads:
    # 1. Environment variables (highest priority)
    # 2. File config (lower priority)
    # 3. Defaults (lowest priority)
    config = CreatureGRCConfig(_file_config=file_config_data)

    return config


def detect_mode() -> DeploymentMode:
    """
    Auto-detect deployment mode.

    Detection logic:
    1. Check explicit CREATUREGRC_MODE environment variable
    2. Check if database is configured and accessible
    3. Check if server URL is configured (agent mode)
    4. Check if running in Docker with postgres service
    5. Default to agent mode (safest)
    """

    # 1. Explicit mode
    if mode := os.getenv("CREATUREGRC_MODE"):
        return DeploymentMode(mode.lower())

    # 2. Try to load config
    try:
        config = load_config()
        if config.database is not None:
            # Check database connectivity
            try:
                import psycopg2

                conn = psycopg2.connect(
                    host=config.database.host,
                    port=config.database.port,
                    dbname=config.database.name,
                    user=config.database.user,
                    password=_load_password(config.database.password_file),
                    connect_timeout=3,
                )
                conn.close()
                return DeploymentMode.SERVER
            except Exception:
                pass

        if config.server is not None:
            return DeploymentMode.AGENT

    except Exception:
        pass

    # 3. Check Docker environment
    if os.path.exists("/.dockerenv"):
        if os.getenv("POSTGRES_HOST") or os.getenv("GRC_DB_HOST"):
            return DeploymentMode.SERVER

    # 4. Default to agent
    return DeploymentMode.AGENT


def _load_password(password_file: Optional[Path]) -> Optional[str]:
    """Load password from file"""
    if not password_file:
        return None

    if not password_file.exists():
        raise FileNotFoundError(f"Password file not found: {password_file}")

    return password_file.read_text().strip()


def validate_config(config: CreatureGRCConfig) -> list[str]:
    """
    Validate configuration and return list of errors.

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Agent mode validation
    if config.is_agent_mode():
        if config.server is None:
            errors.append("Agent mode requires [server] configuration")

        if config.agent and not config.agent.evidence_cache_dir.exists():
            try:
                config.agent.evidence_cache_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create evidence cache directory: {e}")

    # Server mode validation
    if config.is_server_mode():
        if config.database is None:
            errors.append("Server mode requires [database] configuration")

        if config.api and config.api.enabled:
            if config.api.port < 1024 and os.geteuid() != 0:
                errors.append(f"Port {config.api.port} requires root privileges")

    # Storage validation
    if not config.evidence.storage_dir.exists():
        try:
            config.evidence.storage_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"Cannot create evidence storage directory: {e}")

    if not config.audit.output_dir.exists():
        try:
            config.audit.output_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"Cannot create audit output directory: {e}")

    return errors
