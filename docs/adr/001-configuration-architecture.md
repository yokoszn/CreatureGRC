# ADR 001: Configuration Architecture for Agent and Server Modes

**Status**: Proposed
**Date**: 2025-10-28
**Deciders**: SRE, SecEng

## Context

CreatureGRC has two deployment modes:

1. **Agent/CLI Mode** (lightweight)
   - Deployed on security agent devices, consultant laptops, edge systems
   - Export-only: collects evidence and pushes to server
   - No database access
   - Must support multiple profiles (consultant managing 5+ clients)
   - Minimal dependencies

2. **Server Mode** (full platform)
   - Central compliance platform
   - PostgreSQL database
   - Receives evidence from agents
   - Integrates with Netbox, Wazuh, Keycloak, etc.
   - Generates audit packages

**Similar patterns**: Wazuh agent/manager, Datadog agent/platform, Teleport node/cluster

## Decision

Implement hierarchical configuration with mode detection and profile support.

### Configuration Locations

**Agent Mode** (user-specific):
```
~/.config/creaturegrc/
├── config.toml                    # Active config (or symlink)
├── profiles/
│   ├── acme-corp.toml             # Client profiles
│   ├── widgets-inc.toml
│   └── default.toml
├── credentials/                   # Encrypted credentials
│   ├── acme-api-key.encrypted
│   └── widgets-api-key.encrypted
├── cache/                         # Local evidence cache before upload
│   ├── acme/
│   │   └── evidence-2024-10-28.json
│   └── widgets/
└── logs/
    └── agent.log
```

**Server Mode** (system-wide):
```
/etc/creaturegrc/
├── server.toml                    # Server configuration
├── database.toml                  # DB connection (or use .env)
├── integrations/
│   ├── netbox.toml
│   ├── wazuh.toml
│   ├── keycloak.toml
│   └── aws.toml
└── .env                           # Secrets (loaded by Docker Compose)

/var/lib/creaturegrc/
├── evidence/                      # Received evidence from agents
├── audit-packages/                # Generated audit packages
└── cache/                         # Framework data cache
```

### Configuration Schema

**Agent Config** (`~/.config/creaturegrc/profiles/acme-corp.toml`):
```toml
[profile]
name = "acme-corp"
mode = "agent"  # agent | server
description = "ACME Corporation GRC Platform"

[server]
url = "https://grc.acmecorp.com"
api_key_file = "~/.config/creaturegrc/credentials/acme-api-key.encrypted"
verify_ssl = true
timeout = 30

[agent]
device_id = "agent-laptop-consultant-01"  # Auto-generated or manual
evidence_cache_dir = "~/.config/creaturegrc/cache/acme"
upload_interval = 3600  # seconds (1 hour)
batch_size = 100

[collection]
enabled_sources = ["netbox", "wazuh", "keycloak"]  # What to scan locally
frameworks = ["soc2", "iso27001"]

[logging]
level = "INFO"
file = "~/.config/creaturegrc/logs/acme-agent.log"
max_size_mb = 100
```

**Server Config** (`/etc/creaturegrc/server.toml`):
```toml
[server]
mode = "server"
host = "0.0.0.0"
port = 8080
workers = 4

[database]
# Loaded from environment or database.toml
host = "${GRC_DB_HOST:-localhost}"
port = "${GRC_DB_PORT:-5432}"
name = "${GRC_DB_NAME:-grc_platform}"
user = "${GRC_DB_USER:-grc_user}"
password_file = "/run/secrets/db_password"  # Docker secret
pool_size = 20
pool_timeout = 30

[api]
enabled = true
cors_origins = ["https://admin.example.com"]
rate_limit = "100/minute"
auth_method = "api_key"  # api_key | oauth2 | mtls

[evidence]
storage_dir = "/var/lib/creaturegrc/evidence"
retention_days = 365
compression = true

[integrations]
config_dir = "/etc/creaturegrc/integrations"
enabled = ["netbox", "wazuh", "keycloak", "freeipa", "github"]

[audit]
output_dir = "/var/lib/creaturegrc/audit-packages"
formats = ["pdf", "excel", "zip"]

[logging]
level = "INFO"
format = "json"  # json | text
output = "stdout"  # stdout | file
file = "/var/log/creaturegrc/server.log"
```

**Integration Config** (`/etc/creaturegrc/integrations/netbox.toml`):
```toml
[netbox]
enabled = true
api_url = "${NETBOX_API_URL}"
token_file = "/run/secrets/netbox_token"
verify_ssl = true
sync_interval = 86400  # 24 hours
timeout = 30

[netbox.mapping]
# Map Netbox device roles to creature classes
device_role_to_class = {
    "server" = "server",
    "firewall" = "network-security",
    "switch" = "network-device"
}

[netbox.filters]
# Only sync devices with these tags
required_tags = ["production", "compliance"]
exclude_status = ["decommissioned", "planned"]
```

### Configuration Hierarchy

Priority order (highest to lowest):
1. CLI flags: `--config`, `--profile`, `--server-url`
2. Environment variables: `CREATUREGRC_PROFILE`, `CREATUREGRC_SERVER_URL`
3. Active config file: `~/.config/creaturegrc/config.toml`
4. Default config: `~/.config/creaturegrc/profiles/default.toml`
5. System config: `/etc/creaturegrc/server.toml` (server mode only)

### Profile Management

**CLI Commands**:
```bash
# List profiles
creaturegrc profile list

# Create new profile
creaturegrc profile create acme-corp \
  --server-url https://grc.acmecorp.com \
  --api-key-file ~/.config/creaturegrc/credentials/acme-api-key

# Switch profile
creaturegrc profile use acme-corp

# Show current profile
creaturegrc profile show

# Run command with specific profile (without switching)
creaturegrc --profile widgets-inc status --framework soc2

# Edit profile
creaturegrc profile edit acme-corp

# Delete profile
creaturegrc profile delete acme-corp
```

**Profile Switching Behavior**:
- `creaturegrc profile use <name>` updates `~/.config/creaturegrc/config.toml` (symlink or copy)
- All subsequent commands use active profile
- `--profile` flag overrides for single command

### Credential Management

**Options**:

1. **Encrypted Files** (default):
   - API keys stored in `~/.config/creaturegrc/credentials/`
   - Encrypted with user's system keyring (keyring library)
   - `creaturegrc credential set acme-corp api-key`

2. **Environment Variables** (CI/CD):
   - `CREATUREGRC_API_KEY=xyz creaturegrc status`
   - Useful for automation

3. **Docker Secrets** (server mode):
   - `/run/secrets/db_password`
   - `/run/secrets/netbox_token`

4. **External Secret Managers** (enterprise):
   - Infisical, Vault integration
   - `password_file = "infisical://prod/grc/db_password"`

### Mode Detection

```python
def detect_mode() -> Literal["agent", "server"]:
    """Auto-detect deployment mode"""

    # 1. Explicit config
    if config.get("mode"):
        return config["mode"]

    # 2. Database connectivity
    if can_connect_to_database():
        return "server"

    # 3. Server URL configured
    if config.get("server.url"):
        return "agent"

    # 4. Check if running in Docker with postgres service
    if os.path.exists("/.dockerenv") and check_postgres_host():
        return "server"

    # 5. Default to agent (safest)
    return "agent"
```

### Package Installation

**Agent Mode** (minimal):
```bash
pip install creaturegrc[agent]  # Core + scanners, no server deps
```

**Server Mode** (full):
```bash
pip install creaturegrc[server]  # Includes FastAPI, Temporal, etc.
```

**Both**:
```bash
pip install creaturegrc  # Installs both, auto-detects mode at runtime
```

### Docker Deployment

**Agent Container**:
```yaml
# docker-compose.agent.yml
services:
  agent:
    image: ghcr.io/yokoszn/creaturegrc:agent
    environment:
      CREATUREGRC_MODE: agent
      CREATUREGRC_SERVER_URL: https://grc.company.com
      CREATUREGRC_API_KEY_FILE: /run/secrets/api_key
    secrets:
      - api_key
    volumes:
      - ./evidence-cache:/var/lib/creaturegrc/cache
    command: ["agent", "run", "--interval", "3600"]

secrets:
  api_key:
    file: ./secrets/api_key.txt
```

**Server Container**:
```yaml
# docker-compose.server.yml (existing)
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: grc_platform
      POSTGRES_USER: grc_user
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
    secrets:
      - db_password

  grc-server:
    image: ghcr.io/yokoszn/creaturegrc:server
    environment:
      CREATUREGRC_MODE: server
      GRC_DB_HOST: postgres
    secrets:
      - db_password
      - netbox_token
    volumes:
      - grc_evidence:/var/lib/creaturegrc/evidence
      - grc_audit:/var/lib/creaturegrc/audit-packages
    ports:
      - "8080:8080"
```

## Consequences

### Positive
- Clear separation between agent and server deployment
- Consultants can manage multiple clients easily
- Configuration is explicit and version-controllable
- Docker-friendly with secrets support
- Supports both on-device CLI and remote agent deployment

### Negative
- More complex configuration surface
- Need to document profile management workflow
- Credential encryption adds dependency on system keyring
- Mode auto-detection could be confusing if wrong

### Mitigations
- Provide `creaturegrc doctor` command to validate config
- Ship example configs for common scenarios
- Clear error messages when mode detection fails
- Interactive setup wizard: `creaturegrc init`

## Implementation

1. **Phase 1**: Configuration models with Pydantic Settings
2. **Phase 2**: Profile management CLI commands
3. **Phase 3**: Mode detection logic
4. **Phase 4**: Agent-specific commands (`agent run`, `agent upload`)
5. **Phase 5**: Credential encryption with keyring
6. **Phase 6**: Docker builds for agent vs server

## References

- Pydantic Settings: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- Python keyring: https://github.com/jaraco/keyring
- Docker secrets: https://docs.docker.com/engine/swarm/secrets/
- TOML spec: https://toml.io/
