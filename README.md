# CreatureGRC

**Open-source compliance automation platform that connects your infrastructure to security controls**

CreatureGRC automates compliance workflows by continuously collecting evidence from your infrastructure and mapping it to security frameworks like SOC 2, ISO 27001, and NIST 800-53. It's designed for teams running self-hosted infrastructure who need to prove compliance without expensive enterprise GRC tools.

## What It Does

CreatureGRC solves three core problems:

1. **Control Management**: Import and organize security controls from major frameworks (NIST, SOC 2, ISO 27001, PCI-DSS, HIPAA)
2. **Evidence Collection**: Automatically gather compliance evidence from your infrastructure tools (Wazuh, Keycloak, Netbox, FreeIPA, etc.)
3. **Infrastructure Mapping**: Connect your servers, containers, and services to specific security controls so auditors can see what protects what

Instead of manually taking screenshots and writing documentation for audits, CreatureGRC continuously collects evidence and generates audit packages automatically.

## The Creature Concept

In CreatureGRC, a "**Creature**" is any piece of infrastructure you manage:

- A physical server or VM
- A container or LXC
- A network device (firewall, switch, router)
- A database instance
- A Kubernetes cluster
- A SaaS application you integrate with

The name "Creature" represents the idea that your infrastructure is alive - constantly changing, scaling, and evolving. CreatureGRC tracks these changes and ensures your compliance documentation stays current.

**Example Creature taxonomy:**
```
Creature: prod-web-01
├─ Type: LXC Container
├─ Zone: DMZ (Zone 5)
├─ IP: 192.168.1.50
├─ Services: Nginx, Node.js API
├─ Controls: AC-3 (Access Control), SI-7 (Software Integrity)
└─ Evidence: Wazuh vulnerability scans, Netbox configuration
```

When you map Creatures to Controls, you're documenting which infrastructure implements which security requirements. This creates an auditable trail from security policy to actual implementation.

## Key Features

### Compliance Automation
- **1,400+ Security Controls**: NIST 800-53, ComplianceForge SCF, CSA Cloud Controls Matrix
- **Framework Mapping**: Automatic cross-mapping between frameworks (e.g., NIST AC-2 → SOC 2 CC6.1)
- **Control Implementation Tracking**: Document which infrastructure implements each control
- **Audit Package Generation**: Export evidence bundles for auditors (PDF, Excel, ZIP)

### Evidence Collection
Automatically collect compliance evidence from your existing tools:
- **Security**: Wazuh SIEM, vulnerability scans, intrusion detection alerts
- **Identity**: Keycloak authentication logs, FreeIPA user lifecycle events
- **Infrastructure**: Netbox asset inventory, IP address management, configuration changes
- **Secrets**: Infisical secret access logs, Vaultwarden password policy checks
- **Code**: OneDev code reviews, branch protection rules, CI/CD evidence
- **Containers**: Zot registry image scans, vulnerability reports

### AI-Powered Workflows (Optional)
When deployed with the AI Foundry stack:
- **Gap Analysis**: AI identifies missing controls or incomplete implementations
- **Smart Questionnaires**: Generate and process control questionnaires using LLMs
- **Evidence Extraction**: Parse unstructured logs and documents to extract compliance evidence
- **Vendor Assessment**: Automate security questionnaires for third-party vendors
- **Multi-LLM Support**: Use Claude, GPT-4, Gemini with automatic fallback and cost tracking

### Self-Hosted & Lightweight
- **Minimal Core**: 2GB RAM, single container (PostgreSQL + CLI)
- **No Bloat**: Connects to your existing infrastructure via APIs, doesn't re-deploy services
- **CLI-First**: Designed for automation, IaC, and scripting
- **API-Driven**: Integrate with CI/CD pipelines and existing workflows
- **Privacy**: Your compliance data stays on your infrastructure

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│  1. INFRASTRUCTURE (Your Existing Tools)                     │
│                                                              │
│  Security       Identity        Infrastructure   Secrets    │
│  ┌─────────┐   ┌─────────┐    ┌──────────┐    ┌─────────┐ │
│  │ Wazuh   │   │Keycloak │    │ Netbox   │    │Infisical│ │
│  │ SIEM    │   │FreeIPA  │    │ Network  │    │Vault-   │ │
│  │         │   │         │    │ Inventory│    │ warden  │ │
│  └────┬────┘   └────┬────┘    └────┬─────┘    └────┬────┘ │
│       │             │              │               │       │
│       └─────────────┴──────────────┴───────────────┘       │
│                           │ REST APIs                       │
└───────────────────────────┼─────────────────────────────────┘
                            ↓
┌───────────────────────────────────────────────────────────────┐
│  2. CREATUREGRC (Compliance Automation Layer)                 │
│                                                               │
│  ┌──────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ Control      │  │ Evidence        │  │ Creature        │ │
│  │ Library      │  │ Collector       │  │ Mapper          │ │
│  │              │  │                 │  │                 │ │
│  │ • NIST       │  │ Pulls from APIs │  │ Infrastructure  │ │
│  │ • SOC 2      │→ │ Daily/Weekly    │→ │ → Controls      │ │
│  │ • ISO 27001  │  │ Stores evidence │  │ Mapping         │ │
│  │ • PCI-DSS    │  │ in database     │  │                 │ │
│  └──────────────┘  └─────────────────┘  └─────────────────┘ │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ PostgreSQL Database                                  │    │
│  │ • Controls • Evidence • Creatures • Risk Register    │    │
│  └──────────────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────────────┘
                            ↓
┌───────────────────────────────────────────────────────────────┐
│  3. OUTPUT                                                    │
│                                                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ Audit Packages  │  │ Gap Analysis    │  │ CLI Reports  │ │
│  │                 │  │                 │  │              │ │
│  │ • Evidence ZIP  │  │ • Missing       │  │ creaturegrc  │ │
│  │ • Control       │  │   controls      │  │ controls     │ │
│  │   matrix (Excel)│  │ • Weak areas    │  │ list         │ │
│  │ • PDF reports   │  │ • Remediation   │  │              │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└───────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

CreatureGRC can be deployed anywhere Docker runs, but is optimized for:
- **Proxmox/LXC environments** with existing infrastructure services
- **Bare metal servers** with Docker
- **Cloud VMs** (AWS, GCP, Azure)

**Minimum requirements:**
- 2GB RAM (core only), 10GB RAM (with AI features)
- Docker and Docker Compose
- API access to your infrastructure tools (Wazuh, Netbox, etc.)

### Basic Installation

```bash
# Clone repository
git clone https://github.com/yokoszn/CreatureGRC.git
cd CreatureGRC

# Configure environment
cp config/.env.minimal.example .env
nano .env  # Add your API endpoints and credentials

# Deploy core platform
cd deployments
docker-compose -f docker-compose.grc-core.yml up -d

# Import security control frameworks
docker exec grc-cli python /app/scripts/import_oscal_controls.py     # NIST 800-53
docker exec grc-cli python /app/scripts/import_scf_controls.py       # ComplianceForge SCF
docker exec grc-cli python /app/scripts/import_csa_ccm.py            # CSA Cloud Controls

# Sync your infrastructure (Creatures) from Netbox
docker exec grc-cli creaturegrc creatures sync --source netbox

# Collect initial evidence
docker exec grc-cli creaturegrc collect evidence --source wazuh
docker exec grc-cli creaturegrc collect evidence --source keycloak

# Generate your first audit package
docker exec grc-cli creaturegrc audit generate --framework soc2 --output /var/lib/grc/audit-packages/
```

See [docs/quickstart.md](docs/quickstart.md) for detailed installation instructions including the optional AI Foundry deployment.

## Usage Examples

### List Available Compliance Frameworks

```bash
$ creaturegrc frameworks list

Available Compliance Frameworks:
┌──────────────┬─────────────┬──────────┐
│ Framework    │ Version     │ Controls │
├──────────────┼─────────────┼──────────┤
│ NIST 800-53  │ Revision 5  │ 1,084    │
│ SOC 2        │ 2017        │ 64       │
│ ISO 27001    │ 2022        │ 93       │
│ PCI-DSS      │ 4.0         │ 362      │
│ SCF          │ 2024.1      │ 212      │
│ CSA CCM      │ v4.0        │ 197      │
└──────────────┴─────────────┴──────────┘
```

### View Your Infrastructure (Creatures)

```bash
$ creaturegrc creatures list

Infrastructure Assets (Creatures):
┌─────────────────┬──────────┬────────────────┬──────────┬──────────┐
│ Name            │ Type     │ IP             │ Zone     │ Controls │
├─────────────────┼──────────┼────────────────┼──────────┼──────────┤
│ prod-web-01     │ LXC      │ 192.168.1.50   │ DMZ      │ 12       │
│ prod-db-01      │ LXC      │ 192.168.1.60   │ Data     │ 18       │
│ wazuh-server    │ LXC      │ 192.168.1.10   │ Security │ 8        │
│ k8s-cluster-01  │ Cluster  │ 192.168.1.70-79│ App      │ 24       │
└─────────────────┴──────────┴────────────────┴──────────┴──────────┘

Total: 47 creatures tracked
```

### Map Infrastructure to Controls

```bash
$ creaturegrc controls map-creatures --framework soc2

Analyzing infrastructure coverage for SOC 2...
✓ CC6.1 (Logical Access): 8 creatures mapped
✓ CC6.2 (Privileged Access): 3 creatures mapped
✓ CC7.2 (Change Management): 12 creatures mapped
✗ CC7.3 (Data Backup): No creatures mapped (Gap!)

Recommendation: Add backup infrastructure for CC7.3 compliance
```

### Collect Evidence Automatically

```bash
$ creaturegrc collect evidence --source wazuh --days 30

Collecting evidence from Wazuh (last 30 days)...
✓ Vulnerability scans: 127 events collected
✓ Security alerts: 1,842 events collected
✓ Compliance checks: 94 events collected
✓ File integrity monitoring: 312 events collected

Evidence stored and mapped to 23 controls
```

### Generate Audit Package

```bash
$ creaturegrc audit generate --framework soc2 --output ./audit-package-2024-q4/

Generating SOC 2 Type II audit package...
✓ Control matrix (Excel): control-matrix.xlsx
✓ Evidence bundle (ZIP): evidence-bundle.zip (1,247 files)
✓ Infrastructure map (PDF): infrastructure-map.pdf
✓ Gap analysis report (PDF): gap-analysis.pdf
✓ Risk register (Excel): risk-register.xlsx

Audit package ready: ./audit-package-2024-q4/
```

## Configuration

### Connecting Your Infrastructure

Edit `.env` to point to your existing services:

```bash
# Security Tools
WAZUH_API_URL=https://wazuh.example.com:55000
WAZUH_USER=admin
WAZUH_PASSWORD=your-password

# Infrastructure Inventory
NETBOX_API_URL=https://netbox.example.com
NETBOX_TOKEN=your-netbox-api-token

# Identity & Access
KEYCLOAK_URL=https://keycloak.example.com
KEYCLOAK_CLIENT_ID=creaturegrc
KEYCLOAK_CLIENT_SECRET=your-secret

FREEIPA_API_URL=https://ipa.example.com
FREEIPA_USER=admin
FREEIPA_PASSWORD=your-password

# Secrets Management
INFISICAL_API_URL=https://infisical.example.com
INFISICAL_TOKEN=your-token

VAULTWARDEN_API_URL=https://vault.example.com
VAULTWARDEN_TOKEN=your-token
```

See [config/.env.minimal.example](config/.env.minimal.example) for the complete configuration template.

## Architecture

CreatureGRC uses a **minimal integration architecture** - it doesn't replace your existing tools, it connects to them via APIs.

### Components

**GRC Core** (Required, 2GB RAM):
- PostgreSQL database (controls, evidence, creatures, risk register)
- CLI application (evidence collection, reporting)
- Python scripts (framework imports, evidence collectors)

**AI Foundry** (Optional, 8GB RAM):
- **LiteLLM**: Multi-LLM gateway with automatic fallback (Claude, GPT-4, Gemini)
- **Temporal**: Durable workflow orchestration (scheduled evidence collection)
- **Obot**: Workflow automation (gap analysis, vendor assessments)
- **Langfuse**: LLM observability and cost tracking
- **GooseAI**: AI agent framework

### Deployment Patterns

**Pattern 1: Standalone Container** (Simplest)
```
Single host running docker-compose with GRC Core
Connects to infrastructure APIs over the network
```

**Pattern 2: Proxmox LXC** (Recommended for self-hosted)
```
Separate LXC containers for each service
GRC Core in one LXC, AI Foundry in another
Infrastructure services in their own LXCs
All communicate via API over virtual network
```

**Pattern 3: Kubernetes** (Enterprise)
```
Deploy as Helm chart
Scale evidence collectors horizontally
High availability database with replicas
```

## Control Libraries

CreatureGRC imports controls from industry-standard frameworks:

| Framework | Purpose | Controls | Mappings |
|-----------|---------|----------|----------|
| **NIST 800-53 Rev 5** | Federal security controls | 1,084 | Foundation for all mappings |
| **ComplianceForge SCF** | Unified security framework | 212 | Maps to 137+ other frameworks |
| **CSA CCM v4** | Cloud security controls | 197 | Cloud-specific mappings |

These frameworks automatically cross-map to common compliance requirements:
- **SOC 2 Type II** (Trust Services Criteria)
- **ISO/IEC 27001:2022** (Information Security)
- **PCI-DSS v4.0** (Payment Card Industry)
- **HIPAA** (Healthcare Privacy)
- **GDPR** (EU Data Protection)
- **FedRAMP** (US Federal Cloud)

When you implement NIST AC-2 (Account Management), CreatureGRC automatically knows it satisfies:
- SOC 2 CC6.1
- ISO 27001 A.9.2.1
- PCI-DSS Requirement 8.1

## AI Features (Optional)

Deploy the AI Foundry stack to enable advanced automation:

### Intelligent Gap Analysis
```bash
$ creaturegrc analyze gaps --framework soc2 --use-ai

AI Gap Analysis (Claude 3.5 Sonnet)...

Critical Gaps Found:
1. CC7.3 - System Operations: No automated backup verification detected
   Recommendation: Implement Veeam backup monitoring in Wazuh
   Effort: Medium (2-4 hours)

2. CC6.7 - Access Removal: Offboarding process not documented
   Recommendation: Create FreeIPA → Keycloak deprovisioning workflow
   Effort: Low (1-2 hours)

3. CC8.1 - Risk Assessment: No formal risk register maintained
   Recommendation: Use CreatureGRC risk module to track findings
   Effort: Low (30 mins)
```

### Smart Questionnaires
```bash
$ creaturegrc questionnaire generate --control nist-ac-2 --use-ai

Generating AI questionnaire for NIST AC-2 (Account Management)...

Questions generated (10 questions):
1. How are user accounts provisioned in your environment?
2. What is the approval process for granting elevated privileges?
3. How often are user accounts reviewed for appropriateness?
...

Send to stakeholder? [y/N]: y
✓ Questionnaire sent to security-team@example.com
```

### Evidence Extraction from Unstructured Data
```bash
$ creaturegrc evidence extract --file security-policy.pdf --use-ai

Extracting compliance evidence from security-policy.pdf...

AI Extracted Evidence:
✓ Access Control Policy → Maps to NIST AC-1, SOC 2 CC6.1
✓ Password Requirements → Maps to NIST IA-5, SOC 2 CC6.1
✓ Incident Response Plan → Maps to NIST IR-1, SOC 2 CC7.3
✓ Change Management Process → Maps to NIST CM-3, SOC 2 CC8.1

12 controls evidenced from document
```

## Repository Structure

```
CreatureGRC/
├── cli/                  # CLI application (Click-based)
├── database/             # PostgreSQL schemas
├── scripts/              # Evidence collectors, importers, generators
├── workflows/            # Temporal and Obot workflow definitions
├── deployments/          # Docker Compose files
├── config/               # Configuration templates
├── docs/                 # Documentation
│   ├── architecture/     # Design documents
│   ├── quickstart.md     # Getting started guide
│   └── deployment.md     # Production deployment
└── README.md             # This file
```

See the [full repository structure](docs/architecture/overview.md) for details.

## Documentation

- **[Quick Start Guide](docs/quickstart.md)** - Get running in 5 minutes
- **[Architecture Overview](docs/architecture/overview.md)** - System design and components
- **[Deployment Guide](docs/deployment.md)** - Production deployment patterns
- **[API Integration Guide](docs/api-integration.md)** - Connect your infrastructure tools
- **[Control Mapping Guide](docs/control-mapping.md)** - Map infrastructure to controls
- **[Evidence Collection Guide](docs/evidence-collection.md)** - Automate compliance evidence

## Roadmap

- [ ] Web UI (trust center portal for customers)
- [ ] Real-time control monitoring dashboards
- [ ] Ansible playbooks for infrastructure provisioning
- [ ] Custom evidence collector SDK
- [ ] REST API for third-party integrations
- [ ] RBAC for multi-tenant deployments
- [ ] Compliance dashboard exports (PowerPoint, PDF)
- [ ] Jira integration for remediation tracking
- [ ] Slack/Teams notifications for control failures

## Contributing

Contributions are welcome! CreatureGRC is built for the community.

**Areas we need help:**
- Additional evidence collectors (AWS, Azure, GCP, Datadog, etc.)
- Framework mapping improvements
- UI/UX design for web portal
- Documentation and tutorials
- Translation (i18n)

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/yokoszn/CreatureGRC/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yokoszn/CreatureGRC/discussions)
- **Security**: Report vulnerabilities to security@creaturegrc.dev

## License

[Specify license - recommend Apache 2.0 or MIT for open source]

## Acknowledgments

CreatureGRC builds on excellent open source projects:
- [OSCAL](https://pages.nist.gov/OSCAL/) - NIST Open Security Controls Assessment Language
- [ComplianceForge](https://www.complianceforge.com/) - Secure Controls Framework
- [CSA](https://cloudsecurityalliance.org/) - Cloud Controls Matrix
- [LiteLLM](https://github.com/BerriAI/litellm) - Multi-LLM gateway
- [Temporal](https://temporal.io/) - Durable workflow orchestration

---

**Built for teams who need compliance without compromise.**
