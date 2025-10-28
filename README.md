# CreatureGRC

**Self-Hosted GRC Platform with AI-Powered ServiceNow Control Tower Parity**

CreatureGRC is a minimal, CLI-driven Governance, Risk, and Compliance (GRC) platform designed for self-hosted Proxmox/LXC environments. It extends your existing "Creature Database" infrastructure tracking with comprehensive compliance management, automated evidence collection, and AI-powered workflows.

## Features

- **Complete Control Libraries**: OSCAL (NIST 800-53), ComplianceForge SCF, CSA CCM
- **AI-Powered Workflows**: Multi-LLM orchestration via LiteLLM (Claude, GPT-4, Gemini)
- **Durable Workflows**: Temporal.io for reliable long-running processes
- **Automated Evidence Collection**: From Wazuh, Keycloak, Netbox, FreeIPA, and more
- **Infrastructure Mapping**: Automatic control-to-asset mapping from your Creature Database
- **Minimal Footprint**: 2GB RAM for core, connects to existing services via API
- **CLI-First**: No mandatory web UI, designed for automation and IaC

## Architecture

CreatureGRC follows a **minimal integration layer** approach:

```
┌─────────────────────────────────────────────────────────┐
│              PROXMOX HYPERVISOR                         │
│                                                         │
│  Existing LXC Services (Helper Scripts)                │
│  ├─ Wazuh (192.168.1.10)      ─────┐                   │
│  ├─ Netbox (192.168.1.11)     ─────┤                   │
│  ├─ Keycloak (192.168.1.20)   ─────┤  API              │
│  ├─ FreeIPA (192.168.1.21)    ─────┤  Connections      │
│  ├─ Infisical (192.168.1.22)  ─────┤                   │
│  ├─ Vaultwarden (192.168.1.23)─────┤                   │
│  ├─ OneDev (192.168.1.30)     ─────┤                   │
│  └─ Zot (192.168.1.31)        ─────┘                   │
│                                  │                      │
│  New CreatureGRC LXCs            ↓                      │
│  ├─ GRC Core (192.168.1.100) ◄──────                   │
│  │  └─ PostgreSQL + CLI                                │
│  │                                                      │
│  └─ AI Foundry (192.168.1.101) [Optional]              │
│     └─ Temporal + LiteLLM + Obot + GooseAI + Langfuse  │
└─────────────────────────────────────────────────────────┘
```

**No service duplication** - CreatureGRC connects to your existing infrastructure via API.

## Quick Start

### Prerequisites

- Proxmox hypervisor with existing LXC services (Wazuh, Netbox, Keycloak, etc.)
- Unprivileged LXC with nested Docker support (`pct set <vmid> -features nesting=1`)
- 2GB RAM minimum (GRC Core only), 10GB RAM for AI Foundry

### Option 1: Minimal Deployment (GRC Core Only)

**Resource Requirements**: 1 vCPU, 2GB RAM, 20GB disk

```bash
# 1. Create GRC Core LXC
pct create 100 local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst \
  --hostname grc-core \
  --memory 2048 --cores 1 --rootfs local-lvm:20 \
  --net0 name=eth0,bridge=vmbr0,ip=192.168.1.100/24,gw=192.168.1.1 \
  --unprivileged 1 --features nesting=1

# 2. Install Docker in LXC
pct start 100
pct exec 100 -- bash -c "apt update && apt install -y docker.io docker-compose git"

# 3. Clone and configure
pct exec 100 -- git clone https://github.com/yokoszn/CreatureGRC.git /opt/creaturegrc
pct exec 100 -- cp /opt/creaturegrc/config/.env.minimal.example /opt/creaturegrc/.env

# 4. Edit .env with your LXC IPs
pct exec 100 -- nano /opt/creaturegrc/.env

# 5. Deploy
pct exec 100 -- bash -c "cd /opt/creaturegrc/deployments && docker-compose -f docker-compose.grc-core.yml up -d"

# 6. Import control libraries
pct exec 100 -- docker exec grc-cli python /app/scripts/import_oscal_controls.py
pct exec 100 -- docker exec grc-cli python /app/scripts/import_scf_controls.py
pct exec 100 -- docker exec grc-cli python /app/scripts/import_csa_ccm.py

# 7. Sync infrastructure from Netbox
pct exec 100 -- docker exec grc-cli creaturegrc creatures sync --source netbox

# 8. Collect evidence
pct exec 100 -- docker exec grc-cli creaturegrc collect evidence --source wazuh
```

### Option 2: Full Deployment (GRC Core + AI Foundry)

**Resource Requirements**: 2 LXCs, 5 vCPU, 10GB RAM, 70GB disk total

See [docs/quickstart.md](docs/quickstart.md) for detailed AI Foundry deployment.

## Repository Structure

```
CreatureGRC/
├── README.md                       # This file
├── cli/                            # CLI application
│   ├── creaturegrc/               # CLI package
│   │   ├── __init__.py
│   │   └── cli.py                 # Click-based CLI
│   └── setup.py
├── database/                       # Database schemas
│   ├── schema.sql                 # Full GRC schema
│   └── migrations/                # Future schema migrations
├── scripts/                        # Utility scripts
│   ├── import_oscal_controls.py   # Import NIST 800-53
│   ├── import_scf_controls.py     # Import ComplianceForge SCF
│   ├── import_csa_ccm.py          # Import CSA CCM
│   ├── evidence_collector.py      # Automated evidence collection
│   ├── map_creatures_to_controls.py  # Infrastructure mapping
│   ├── generate_audit_package.py  # Audit package generation
│   ├── litellm_integration.py     # Multi-LLM client
│   └── questionnaire_engine.py    # AI questionnaire engine
├── workflows/                      # Workflow definitions
│   ├── temporal/                  # Temporal workflows
│   │   └── temporal_workflows.py
│   └── obot/                      # Obot workflow YAMLs
│       ├── control-gap-analysis.yaml
│       ├── evidence-ingestion.yaml
│       └── vendor-risk-assessment.yaml
├── deployments/                    # Deployment configurations
│   ├── docker-compose.grc-core.yml      # Minimal GRC (PostgreSQL + CLI)
│   ├── docker-compose.ai-foundry.yml    # AI stack (Temporal, LiteLLM, etc.)
│   ├── docker-compose.yml               # Legacy full-featured (deprecated)
│   └── Dockerfile.cli                   # CLI container image
├── config/                         # Configuration files
│   ├── .env.minimal.example       # Environment variables template
│   ├── config.example.yaml        # YAML config template
│   └── litellm-config.yaml        # LiteLLM model routing
├── docs/                           # Documentation
│   ├── architecture/              # Architecture docs
│   │   ├── overview.md            # High-level architecture
│   │   ├── minimal-deployment.md  # Minimal integration approach
│   │   └── v2-zoned.md            # Legacy zoned architecture
│   ├── quickstart.md              # Quick start guide (current)
│   ├── deployment.md              # Detailed deployment guide
│   └── implementation-summary.md  # Implementation details
├── collectors/                     # Custom evidence collectors (future)
└── playbooks/                      # Ansible playbooks (future)
```

## CLI Usage

```bash
# List supported frameworks
creaturegrc frameworks list

# List controls for a framework
creaturegrc controls list --framework soc2

# Sync infrastructure from Netbox
creaturegrc creatures sync --source netbox

# Map controls to infrastructure
creaturegrc controls map-creatures

# Collect evidence from Wazuh
creaturegrc collect evidence --source wazuh

# Generate audit package
creaturegrc audit generate --framework soc2 --output /var/lib/grc/audit-packages/
```

## Control Libraries

| Framework | Controls | Source | Import Script |
|-----------|----------|--------|---------------|
| **NIST 800-53 Rev 5** | 1000+ | [NIST OSCAL](https://github.com/usnistgov/oscal-content) | `import_oscal_controls.py` |
| **ComplianceForge SCF** | 200+ | [ComplianceForge](https://www.complianceforge.com) | `import_scf_controls.py` |
| **CSA CCM v4** | 197 | [CSA](https://cloudsecurityalliance.org) | `import_csa_ccm.py` |

All frameworks are imported into a unified control taxonomy with automatic cross-mappings.

## AI Features

When AI Foundry is deployed, you get:

- **Multi-LLM Gateway**: Automatic fallback between Claude, GPT-4, Gemini
- **Control Gap Analysis**: AI-powered analysis of control implementation gaps
- **Automated Questionnaires**: AI generates and collects evidence via questionnaires
- **Vendor Risk Assessment**: Automated vendor security assessments
- **Evidence Ingestion**: AI extracts compliance evidence from unstructured data
- **Observability**: Full LLM call tracking via Langfuse

## Integration Points

CreatureGRC connects to your existing services via REST APIs:

- **Wazuh**: Security event evidence, vulnerability scans
- **Netbox**: Infrastructure inventory, IP management
- **Keycloak**: Authentication logs, access reviews
- **FreeIPA**: Identity management, user lifecycle
- **Infisical**: Secrets audit trail
- **Vaultwarden**: Password policy compliance
- **OneDev**: Code review evidence, branch protection
- **Zot**: Container image scanning

## Documentation

- **[Quickstart Guide](docs/quickstart.md)** - Get running in 5 minutes
- **[Architecture Overview](docs/architecture/overview.md)** - Detailed design
- **[Minimal Deployment](docs/architecture/minimal-deployment.md)** - Integration layer approach
- **[Deployment Guide](docs/deployment.md)** - Production deployment
- **[Implementation Summary](docs/implementation-summary.md)** - Technical details

## Development

```bash
# Install CLI in development mode
cd cli
pip install -e .

# Run tests (future)
pytest tests/

# Run linting
flake8 cli/ scripts/

# Format code
black cli/ scripts/
```

## Roadmap

- [ ] Ansible playbooks for automated LXC provisioning
- [ ] Custom evidence collector SDK
- [ ] REST API (optional, for integrations)
- [ ] Web UI (trust center portal)
- [ ] Real-time control testing
- [ ] Compliance dashboard exports (PDF, Excel)
- [ ] RBAC for multi-tenant deployments

## License

[Specify license - MIT, Apache 2.0, proprietary, etc.]

## Contributing

Contributions welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Support

- **Issues**: [GitHub Issues](https://github.com/yokoszn/CreatureGRC/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yokoszn/CreatureGRC/discussions)
- **Documentation**: [docs/](docs/)

---

**CreatureGRC** - Extend your Creature Database with enterprise GRC capabilities.
