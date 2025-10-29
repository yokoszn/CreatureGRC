# CreatureGRC Documentation

Welcome to CreatureGRC, an open-source compliance automation platform that connects your infrastructure to security controls.

## What is CreatureGRC?

CreatureGRC automates compliance workflows by continuously collecting evidence from your infrastructure and mapping it to security frameworks like SOC 2, ISO 27001, and NIST 800-53.

### Key Features

- **Automated Evidence Collection**: Continuously gather compliance evidence from Wazuh, Netbox, Keycloak, and more
- **Multi-Framework Support**: NIST 800-53, SOC 2, ISO 27001, PCI-DSS, HIPAA
- **Agent & Server Modes**: Deploy as lightweight agent or full GRC platform
- **Profile Management**: Perfect for consultants managing multiple clients
- **Plugin Architecture**: Extensible with custom scanners and integrations

## Quick Start

### Agent Mode (Lightweight)

```bash
# Install agent mode
pip install creaturegrc[agent]

# Create profile for your client
creaturegrc profile create acme-corp \
  --server-url https://grc.acmecorp.com \
  --api-key-file ~/.config/creaturegrc/credentials/acme-key

# Switch to profile and collect evidence
creaturegrc profile use acme-corp
creaturegrc collect evidence --source wazuh --days 30
```

### Server Mode (Full Platform)

```bash
# Clone repository
git clone https://github.com/yokoszn/CreatureGRC.git
cd CreatureGRC

# Deploy with Docker Compose
docker-compose -f deployments/docker-compose.yml up -d

# Import frameworks
docker exec grc-cli creaturegrc import-controls --framework nist-800-53

# Generate audit package
docker exec grc-cli creaturegrc audit generate \
  --framework soc2 \
  --output /var/lib/grc/audit-packages/
```

## Architecture

CreatureGRC uses a **monorepo workspace architecture** with clear boundaries:

```
CreatureGRC/
├── packages/
│   ├── creature-ir/        # THE ONLY public contract
│   ├── creature-core/      # Core engines
│   ├── creature-dsl/       # DSL parser
│   └── creature-plugins-*/ # Scanner plugins
├── src/creaturegrc/        # Main package (pip install)
└── deployments/            # Docker Compose
```

See [Workspace Structure](architecture/workspace.md) for details.

## Deployment Modes

### Agent Mode
- **Use Case**: Consultant managing multiple clients, edge device evidence collection
- **Dependencies**: Minimal (no database)
- **Profile Support**: Switch between client configurations
- **Installation**: `pip install creaturegrc[agent]`

### Server Mode
- **Use Case**: Central GRC platform for organization
- **Dependencies**: PostgreSQL database
- **Features**: Full API, integrations, audit generation
- **Deployment**: Docker Compose or Kubernetes

## Configuration

CreatureGRC supports hierarchical configuration with **environment variables overriding files**:

**Priority** (highest to lowest):
1. Environment variables (`CREATUREGRC_*`)
2. Explicit config file (`--config`)
3. Profile file (`~/.config/creaturegrc/profiles/`)
4. System config (`/etc/creaturegrc/server.toml`)
5. Defaults

See [Configuration Guide](configuration.md) for details.

## Next Steps

- [Quick Start Guide](quickstart.md) - Get running in 5 minutes
- [Commands Reference](commands.md) - All CLI commands
- [Profile Management](profile-management.md) - Multi-client setup
- [Creating Plugins](development/creating-plugins.md) - Extend CreatureGRC

## Contributing

CreatureGRC is open source and welcomes contributions!

- **GitHub**: [yokoszn/CreatureGRC](https://github.com/yokoszn/CreatureGRC)
- **Issues**: [Report bugs or request features](https://github.com/yokoszn/CreatureGRC/issues)
- **Discussions**: [Ask questions](https://github.com/yokoszn/CreatureGRC/discussions)

See [Contributing Guide](contributing.md) for details.

## License

MIT License - See [LICENSE](https://github.com/yokoszn/CreatureGRC/blob/main/LICENSE) for details.
