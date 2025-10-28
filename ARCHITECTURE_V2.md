# CreatureGRC Architecture V2: Zoned, CLI-Driven, Integration-First

## Design Philosophy

CreatureGRC is a **minimal GRC overlay** that integrates with your existing infrastructure stack.

**Key Principles:**
1. ✅ **CLI-first** - All operations via command line (no web UI dependency)
2. ✅ **Modular/Zoned** - Separate docker-compose files per infrastructure zone
3. ✅ **Integration-focused** - Connects to existing services, doesn't bundle them
4. ✅ **Ansible-driven** - Automated cross-service configuration
5. ✅ **Proxmox-native** - Designed for Proxmox VMs + unprivileged LXCs

---

## Infrastructure Zones

### Zone 1: Development & Artifacts
**Purpose:** Code storage, artifact registry, CI/CD

**Components:**
- **OneDev** - Self-hosted Git server (git.example.com)
- **Zot Registry** - OCI container registry (registry.example.com)

**Docker Compose:** `compose/zone1-dev-artifacts.yml`

**CreatureGRC Integration:**
- Collect source code audit logs from OneDev
- Track container image SBOMs from Zot
- Evidence: Git commits, code reviews, container scans

---

### Zone 2: Security & Monitoring
**Purpose:** SIEM, threat detection, infrastructure monitoring

**Components:**
- **Wazuh** - SIEM/EDR (wazuh.example.com:55000)
- **Tetragon** - eBPF-based security observability
- **Netbox** - IPAM/DCIM for asset tracking
- **Prometheus** - Metrics
- **Loki** - Logs
- **Tempo** - Traces
- **Mimir** - Long-term metrics storage
- **Pyroscope** - Continuous profiling
- **Grafana** - Visualization

**Docker Compose:** `compose/zone2-security-monitoring.yml`

**CreatureGRC Integration:**
- Evidence: Wazuh auth logs, security alerts, agent status
- Evidence: Tetragon process executions, network policies
- Evidence: Netbox asset inventory, change logs
- Evidence: Grafana compliance dashboards

---

### Zone 3: Secrets Management
**Purpose:** Secrets storage, password management

**Components:**
- **Infisical** - Secrets management (infisical.example.com)
- **Vaultwarden** - Password manager (vault.example.com)

**Docker Compose:** `compose/zone3-secrets.yml`

**CreatureGRC Integration:**
- Evidence: Secret rotation logs from Infisical
- Evidence: Password policy compliance from Vaultwarden
- Control: CC6.1 (secrets management)

---

### Zone 4: AI Agent Stack
**Purpose:** LLM orchestration, workflow automation

**Components:**
- **obot** - Workflow automation
- **LiteLLM** - Multi-LLM gateway
- **Temporal** - Durable workflow execution
- **GooseAI** - AI agent framework
- **Langfuse** - LLM observability

**Compatible with:** CrewAI, LangChain, LlamaIndex (framework-agnostic)

**Docker Compose:** `compose/zone4-ai-agents.yml`

**CreatureGRC Integration:**
- Uses Temporal for evidence collection workflows
- Uses LiteLLM for questionnaire answering
- Uses obot for high-level automation

---

### Zone 5: Ticketing & Collaboration
**Purpose:** Issue tracking, documentation, email

**Components:**
- **Jira / JSM / Confluence** (Free tier, or Zammad future)
- **M365 Email** (external, via SMTP)

**Docker Compose:** `compose/zone5-ticketing.yml` (optional, if self-hosting Zammad)

**CreatureGRC Integration:**
- Create findings as Jira tickets
- Link controls to Confluence policies
- Send audit notifications via M365 email

---

### Zone 6: Identity & Authentication
**Purpose:** SSO, user management, certificate authority

**Components:**
- **Keycloak** - Identity provider (auth.example.com)
- **FreeIPA** - LDAP + Certificate Authority

**Docker Compose:** `compose/zone6-identity.yml`

**CreatureGRC Integration:**
- Evidence: Keycloak MFA config, user provisioning logs
- Evidence: FreeIPA certificate issuance logs
- Control: CC6.1, CC6.2, CC6.3 (authentication, authorization, access reviews)

---

### Zone 7: CreatureGRC Core (Minimal)
**Purpose:** GRC database, CLI, evidence orchestration

**Components:**
- **PostgreSQL** - GRC database
- **CreatureGRC CLI** - Command-line interface
- **Evidence Collectors** - Integration adapters

**Docker Compose:** `compose/zone7-grc-core.yml`

**No Web UI** - All operations via CLI

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     PROXMOX HYPERVISOR                          │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ VM/LXC: dev-artifacts                                    │  │
│  │ - OneDev (git)                                           │  │
│  │ - Zot Registry (OCI)                                     │  │
│  │ Docker Compose: zone1-dev-artifacts.yml                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ VM/LXC: security-monitoring                              │  │
│  │ - Wazuh, Tetragon, Netbox                                │  │
│  │ - Prometheus, Loki, Tempo, Grafana                       │  │
│  │ Docker Compose: zone2-security-monitoring.yml            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ VM/LXC: secrets                                          │  │
│  │ - Infisical, Vaultwarden                                 │  │
│  │ Docker Compose: zone3-secrets.yml                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ VM/LXC: ai-agents                                        │  │
│  │ - obot, LiteLLM, Temporal, GooseAI, Langfuse             │  │
│  │ Docker Compose: zone4-ai-agents.yml                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ VM/LXC: identity                                         │  │
│  │ - Keycloak, FreeIPA                                      │  │
│  │ Docker Compose: zone6-identity.yml                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ VM/LXC: grc-core                                         │  │
│  │ - PostgreSQL                                             │  │
│  │ - CreatureGRC CLI                                        │  │
│  │ Docker Compose: zone7-grc-core.yml                       │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Setup Flow (Ansible-Driven)

### Step 1: Provision Proxmox Guests
```bash
# Create unprivileged LXCs or VMs for each zone
ansible-playbook playbooks/01-provision-proxmox-guests.yml \
  --extra-vars "proxmox_host=pve.example.com"
```

**What it does:**
- Creates LXC containers for each zone
- Installs Docker in each LXC
- Configures networking (bridge, VLANs)
- Sets up storage mounts

---

### Step 2: Deploy Zone Services
```bash
# Deploy all zones
ansible-playbook playbooks/02-deploy-zones.yml \
  --tags "zone1,zone2,zone3,zone4,zone6,zone7"

# Or deploy individually
ansible-playbook playbooks/02-deploy-zones.yml --tags "zone2"
```

**What it does:**
- Copies docker-compose files to each LXC
- Creates `.env` files with zone-specific configs
- Runs `docker-compose up -d` in each zone
- Waits for health checks

---

### Step 3: Configure Cross-Zone Integrations
```bash
# Wire up CreatureGRC to all zones
ansible-playbook playbooks/03-configure-integrations.yml
```

**What it does:**
- Configures CreatureGRC to connect to Wazuh API
- Configures CreatureGRC to connect to Keycloak
- Configures CreatureGRC to use Temporal for workflows
- Configures CreatureGRC to use LiteLLM for AI
- Tests all API connections

---

### Step 4: Import Control Libraries
```bash
# Run from CreatureGRC CLI container
creaturegrc import-controls --framework nist-800-53
creaturegrc import-controls --framework scf
creaturegrc import-controls --framework ccm
```

---

### Step 5: Map Infrastructure (Creatures)
```bash
# Sync from Netbox
creaturegrc sync-creatures --source netbox

# Or import from YAML
creaturegrc import-creatures --file inventory/creatures.yaml
```

---

### Step 6: Start Evidence Collection
```bash
# One-time collection
creaturegrc collect-evidence --framework soc2

# Schedule daily collection via cron or Temporal
creaturegrc schedule-evidence-collection --cron "0 2 * * *"
```

---

## CreatureGRC CLI Commands

### Evidence Collection
```bash
# Collect from all sources
creaturegrc collect --framework soc2

# Collect from specific source
creaturegrc collect --source wazuh --days 90
creaturegrc collect --source keycloak
creaturegrc collect --source tetragon --namespace production

# List collected evidence
creaturegrc evidence list --control CC6.1
```

### Creature Management
```bash
# Sync from Netbox
creaturegrc creatures sync --source netbox

# List creatures
creaturegrc creatures list --class server
creaturegrc creatures list --criticality critical

# Map to controls
creaturegrc creatures map --creature-id <uuid> --control CC6.1
```

### Control Management
```bash
# List frameworks
creaturegrc frameworks list

# List controls
creaturegrc controls list --framework soc2
creaturegrc controls list --domain CC6

# Show control details
creaturegrc controls show CC6.1

# Implementation status
creaturegrc controls status --framework soc2
```

### Audit Packages
```bash
# Generate package
creaturegrc audit-package generate \
  --client "Customer Name" \
  --framework soc2 \
  --output /tmp/audit-pkg.zip

# List packages
creaturegrc audit-package list
```

### Questionnaire Answering
```bash
# Import questionnaire template
creaturegrc questionnaire import --file vendor-questionnaire.yaml

# Auto-answer with AI
creaturegrc questionnaire answer \
  --template-id <uuid> \
  --output answers.html

# Review answers
creaturegrc questionnaire review --template-id <uuid>
```

### Risk Management
```bash
# List risks
creaturegrc risks list --status open

# Add risk
creaturegrc risks add \
  --name "Vendor dependency on AWS" \
  --likelihood high \
  --impact high \
  --owner alice@example.com

# Link control to risk
creaturegrc risks link-control --risk-id <uuid> --control CC6.1
```

### Compliance Status
```bash
# Dashboard
creaturegrc status --framework soc2

# Coverage report
creaturegrc coverage --framework soc2 --format html > coverage.html

# Gap analysis
creaturegrc gap-analysis --framework soc2 --target-date 2025-12-31
```

### Workflow Management (Temporal Integration)
```bash
# Trigger workflow
creaturegrc workflow start daily-evidence-collection

# List workflows
creaturegrc workflow list

# Workflow status
creaturegrc workflow status --id <workflow-id>
```

---

## Configuration

### Global Config: `~/.creaturegrc/config.yaml`
```yaml
# Database
database:
  host: grc-core.example.com
  port: 5432
  database: grc_platform
  user: grc_user
  password_env: GRC_DB_PASSWORD

# Zone 2: Security & Monitoring
integrations:
  wazuh:
    api_url: https://wazuh.example.com:55000
    user: grc-collector
    password_env: WAZUH_PASSWORD
    verify_ssl: true

  tetragon:
    api_url: http://tetragon.example.com:2112
    namespace: production

  netbox:
    api_url: https://netbox.example.com
    token_env: NETBOX_TOKEN

  grafana:
    api_url: https://grafana.example.com
    token_env: GRAFANA_TOKEN

# Zone 3: Secrets
  infisical:
    api_url: https://infisical.example.com
    token_env: INFISICAL_TOKEN

# Zone 4: AI Agents
  litellm:
    api_url: http://litellm.example.com:4000
    api_key_env: LITELLM_KEY

  temporal:
    host: temporal.example.com:7233
    namespace: grc

  obot:
    api_url: http://obot.example.com:9000
    token_env: OBOT_TOKEN

  langfuse:
    api_url: https://langfuse.example.com
    public_key_env: LANGFUSE_PUBLIC_KEY
    secret_key_env: LANGFUSE_SECRET_KEY

# Zone 5: Ticketing
  jira:
    url: https://yourorg.atlassian.net
    email: grc@example.com
    api_token_env: JIRA_API_TOKEN
    project: COMPLIANCE

  confluence:
    url: https://yourorg.atlassian.net/wiki
    email: grc@example.com
    api_token_env: CONFLUENCE_API_TOKEN
    space: GRC

  smtp:
    host: smtp.office365.com
    port: 587
    user: grc@example.com
    password_env: SMTP_PASSWORD
    from: grc@example.com

# Zone 6: Identity
  keycloak:
    url: https://auth.example.com
    realm: master
    client_id: creaturegrc
    client_secret_env: KEYCLOAK_CLIENT_SECRET

  freeipa:
    api_url: https://ipa.example.com
    user: grc-collector
    password_env: FREEIPA_PASSWORD

# Zone 1: Dev & Artifacts
  onedev:
    api_url: https://git.example.com
    token_env: ONEDEV_TOKEN

  zot:
    api_url: https://registry.example.com
    user: grc-collector
    password_env: ZOT_PASSWORD

# LLM Config (via LiteLLM)
llm:
  primary_model: claude-sonnet-4
  fallback_models:
    - gpt-4-turbo
    - gemini-1.5-pro
  daily_cost_limit_usd: 100
```

---

## Environment Variable Management

### Using Infisical for Secrets
```bash
# Install Infisical CLI
curl -1sLf 'https://dl.cloudsmith.io/public/infisical/infisical-cli/setup.deb.sh' | sudo bash
sudo apt-get install infisical

# Login
infisical login

# Run CreatureGRC with secrets injected
infisical run --env=production -- creaturegrc collect --framework soc2
```

### Using .env Files (Development)
```bash
# .env.example provided
cp .env.example .env
vim .env  # Fill in secrets

# Load and run
export $(cat .env | xargs)
creaturegrc collect --framework soc2
```

---

## Ansible Inventory

### `inventory/hosts.yml`
```yaml
all:
  children:
    proxmox:
      hosts:
        pve.example.com:
          ansible_user: root

    zone1_dev_artifacts:
      hosts:
        dev-artifacts.example.com:
          ansible_user: root
          zone: zone1
          services:
            - onedev
            - zot

    zone2_security_monitoring:
      hosts:
        security.example.com:
          ansible_user: root
          zone: zone2
          services:
            - wazuh
            - tetragon
            - netbox
            - prometheus
            - loki
            - tempo
            - grafana

    zone3_secrets:
      hosts:
        secrets.example.com:
          ansible_user: root
          zone: zone3
          services:
            - infisical
            - vaultwarden

    zone4_ai_agents:
      hosts:
        ai-agents.example.com:
          ansible_user: root
          zone: zone4
          services:
            - obot
            - litellm
            - temporal
            - gooseai
            - langfuse

    zone6_identity:
      hosts:
        identity.example.com:
          ansible_user: root
          zone: zone6
          services:
            - keycloak
            - freeipa

    zone7_grc_core:
      hosts:
        grc-core.example.com:
          ansible_user: root
          zone: zone7
          services:
            - postgresql
            - creaturegrc-cli
```

---

## Proxmox LXC Template

### Unprivileged LXC with Nested Docker
```bash
# Create LXC
pct create 100 local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst \
  --hostname grc-core \
  --memory 4096 \
  --cores 2 \
  --rootfs local-lvm:32 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp \
  --unprivileged 1 \
  --features nesting=1

# Start
pct start 100

# Install Docker
pct exec 100 -- bash -c "curl -fsSL https://get.docker.com | sh"
pct exec 100 -- bash -c "apt-get install -y docker-compose-plugin"
```

---

## Key Differences from V1

| Aspect | V1 (Monolithic) | V2 (Zoned/Modular) |
|--------|-----------------|---------------------|
| **Deployment** | Single docker-compose | 7+ zone-specific compose files |
| **Services** | Bundled (Temporal, Postgres, etc.) | Integrates with existing services |
| **UI** | Web UI planned | CLI-only |
| **Configuration** | Single config.yaml | Distributed configs + Ansible |
| **Infrastructure** | Generic Docker host | Proxmox + LXCs |
| **Secrets** | .env files | Infisical integration |
| **Identity** | Assumes external | Integrates with Keycloak + FreeIPA |
| **Monitoring** | Basic | Full observability stack |
| **AI** | Bundled LiteLLM | Full AI agent stack (obot, Temporal, etc.) |

---

## Next: Implementation Files

Now creating:
1. ✅ Zone-specific docker-compose files
2. ✅ Ansible playbooks
3. ✅ CLI implementation
4. ✅ Proxmox/LXC setup scripts
5. ✅ Integration collectors for each zone
