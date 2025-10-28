# CreatureGRC Architecture: Minimal Integration Layer

## Design Philosophy

CreatureGRC is a **minimal GRC overlay** that connects to your **existing Proxmox LXC infrastructure**.

**Zero Bloat:**
- ✅ No bundled services (Wazuh, Keycloak, Netbox, etc.)
- ✅ Just GRC database + CLI
- ✅ Connects via IP/API to your existing LXCs
- ✅ AI Foundry is separate compose, connected via config

---

## Your Existing Infrastructure (Already Deployed)

These services are **already running** in individual Proxmox LXCs (via helper scripts):

### Security & Monitoring LXCs
- **Wazuh** (LXC) - `192.168.1.10:55000` - SIEM/EDR
- **Netbox** (LXC) - `192.168.1.11:8000` - IPAM/DCIM

### Identity & Secrets LXCs
- **Keycloak** (LXC) - `192.168.1.20:8080` - Identity/SSO
- **FreeIPA** (LXC) - `192.168.1.21:443` - LDAP/CA
- **Infisical** (LXC) - `192.168.1.22:8080` - Secrets management
- **Vaultwarden** (LXC) - `192.168.1.23:8080` - Password manager

### Development LXCs
- **OneDev** (LXC) - `192.168.1.30:6610` - Git server
- **Zot Registry** (LXC) - `192.168.1.31:5000` - Container registry

---

## CreatureGRC Components (Minimal)

### 1. GRC Core (Minimal - Just Database + CLI)
**Location**: Single LXC or VM
**Services**: PostgreSQL + CreatureGRC CLI container
**Compose**: `docker-compose.grc-core.yml`
**Purpose**: GRC database, evidence storage, CLI operations

### 2. AI Foundry (Separate Stack)
**Location**: Separate LXC or same LXC as GRC Core
**Services**: Temporal, LiteLLM, Obot, GooseAI, Langfuse, Redis
**Compose**: `docker-compose.ai-foundry.yml`
**Purpose**: AI orchestration (questionnaires, workflows)

---

## Deployment Architecture

```
PROXMOX HYPERVISOR
│
├─ LXC: Wazuh (192.168.1.10) ────────────┐
├─ LXC: Netbox (192.168.1.11) ───────────┤
├─ LXC: Keycloak (192.168.1.20) ─────────┤
├─ LXC: FreeIPA (192.168.1.21) ──────────┤
├─ LXC: Infisical (192.168.1.22) ────────┤    API Connections
├─ LXC: Vaultwarden (192.168.1.23) ──────┤         ↓
├─ LXC: OneDev (192.168.1.30) ───────────┤         ↓
├─ LXC: Zot (192.168.1.31) ──────────────┘         ↓
│                                                   ↓
├─ LXC: GRC-Core (192.168.1.100) ◄─────────────────┘
│   └─ Docker: PostgreSQL + CLI
│
└─ LXC: AI-Foundry (192.168.1.101) ◄──── Connected via config
    └─ Docker: Temporal + LiteLLM + Obot + GooseAI + Langfuse
```

---

## GRC Core Configuration

### `.env` (Connection strings only)
```bash
# Database (local to GRC Core LXC)
GRC_DB_HOST=localhost
GRC_DB_PORT=5432
GRC_DB_NAME=grc_platform
GRC_DB_USER=grc_user
GRC_DB_PASSWORD=secure_password

# ========================================
# External LXC Connections (via IP/API)
# ========================================

# Wazuh (LXC 192.168.1.10)
WAZUH_API_URL=https://192.168.1.10:55000
WAZUH_USER=grc-collector
WAZUH_PASSWORD=${WAZUH_PASSWORD}

# Netbox (LXC 192.168.1.11)
NETBOX_API_URL=http://192.168.1.11:8000
NETBOX_TOKEN=${NETBOX_TOKEN}

# Keycloak (LXC 192.168.1.20)
KEYCLOAK_URL=http://192.168.1.20:8080
KEYCLOAK_REALM=master
KEYCLOAK_CLIENT_ID=creaturegrc
KEYCLOAK_CLIENT_SECRET=${KEYCLOAK_CLIENT_SECRET}

# FreeIPA (LXC 192.168.1.21)
FREEIPA_API_URL=https://192.168.1.21
FREEIPA_USER=grc-collector
FREEIPA_PASSWORD=${FREEIPA_PASSWORD}

# Infisical (LXC 192.168.1.22)
INFISICAL_API_URL=http://192.168.1.22:8080
INFISICAL_TOKEN=${INFISICAL_TOKEN}

# Vaultwarden (LXC 192.168.1.23)
VAULTWARDEN_API_URL=http://192.168.1.23:8080
VAULTWARDEN_TOKEN=${VAULTWARDEN_TOKEN}

# OneDev (LXC 192.168.1.30)
ONEDEV_API_URL=http://192.168.1.30:6610
ONEDEV_TOKEN=${ONEDEV_TOKEN}

# Zot Registry (LXC 192.168.1.31)
ZOT_API_URL=http://192.168.1.31:5000
ZOT_USER=grc-collector
ZOT_PASSWORD=${ZOT_PASSWORD}

# AI Foundry (LXC 192.168.1.101)
LITELLM_API_URL=http://192.168.1.101:4000
TEMPORAL_HOST=192.168.1.101:7233
OBOT_API_URL=http://192.168.1.101:9000
LANGFUSE_API_URL=http://192.168.1.101:3001
LANGFUSE_PUBLIC_KEY=${LANGFUSE_PUBLIC_KEY}
LANGFUSE_SECRET_KEY=${LANGFUSE_SECRET_KEY}

# LLM API Keys (for LiteLLM)
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
OPENAI_API_KEY=${OPENAI_API_KEY}
GOOGLE_API_KEY=${GOOGLE_API_KEY}

# Ticketing (External - M365/Jira)
JIRA_URL=https://yourorg.atlassian.net
JIRA_EMAIL=grc@example.com
JIRA_API_TOKEN=${JIRA_API_TOKEN}

SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=grc@example.com
SMTP_PASSWORD=${SMTP_PASSWORD}
```

---

## Deployment Steps

### Step 1: Deploy GRC Core (Minimal)

```bash
# Create LXC for GRC Core
pct create 100 local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst \
  --hostname grc-core \
  --memory 2048 --cores 1 --rootfs local-lvm:20 \
  --net0 name=eth0,bridge=vmbr0,ip=192.168.1.100/24,gw=192.168.1.1 \
  --unprivileged 1 --features nesting=1

# Install Docker
pct start 100
pct exec 100 -- bash -c "curl -fsSL https://get.docker.com | sh"

# Copy compose files
pct push 100 docker-compose.grc-core.yml /root/docker-compose.yml
pct push 100 .env /root/.env

# Deploy
pct exec 100 -- docker compose -f /root/docker-compose.yml up -d
```

### Step 2: Deploy AI Foundry (Optional, Separate LXC)

```bash
# Create LXC for AI Foundry
pct create 101 local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst \
  --hostname ai-foundry \
  --memory 8192 --cores 4 --rootfs local-lvm:50 \
  --net0 name=eth0,bridge=vmbr0,ip=192.168.1.101/24,gw=192.168.1.1 \
  --unprivileged 1 --features nesting=1

# Install Docker
pct start 101
pct exec 101 -- bash -c "curl -fsSL https://get.docker.com | sh"

# Copy compose files
pct push 101 docker-compose.ai-foundry.yml /root/docker-compose.yml
pct push 101 .env.ai-foundry /root/.env

# Deploy
pct exec 101 -- docker compose -f /root/docker-compose.yml up -d
```

### Step 3: Configure Integration with Existing LXCs

```bash
# Test connectivity from GRC Core to existing services
pct exec 100 -- curl -k https://192.168.1.10:55000  # Wazuh
pct exec 100 -- curl http://192.168.1.11:8000       # Netbox
pct exec 100 -- curl http://192.168.1.20:8080       # Keycloak

# Collect evidence from existing services
pct exec 100 -- docker exec grc-cli creaturegrc collect evidence --source wazuh
pct exec 100 -- docker exec grc-cli creaturegrc creatures sync --source netbox
```

---

## Integration Collectors

CreatureGRC CLI includes collectors that connect to your existing LXCs:

### Wazuh Collector (connects to LXC 192.168.1.10)
```python
# collectors/wazuh_collector.py
class WazuhCollector:
    def __init__(self, api_url, user, password):
        self.api_url = api_url  # https://192.168.1.10:55000
        self.user = user
        self.password = password

    def collect_auth_logs(self):
        # Connect via API to existing Wazuh LXC
        response = requests.get(f"{self.api_url}/security/user/authenticate")
        # ... collect evidence
```

### Netbox Collector (connects to LXC 192.168.1.11)
```python
# collectors/netbox_collector.py
class NetboxCollector:
    def __init__(self, api_url, token):
        self.api_url = api_url  # http://192.168.1.11:8000
        self.token = token

    def sync_devices(self):
        # Connect via API to existing Netbox LXC
        response = requests.get(f"{self.api_url}/api/dcim/devices/")
        # ... sync creatures
```

### Keycloak Collector (connects to LXC 192.168.1.20)
```python
# collectors/keycloak_collector.py
class KeycloakCollector:
    def __init__(self, url, realm, client_id, client_secret):
        self.url = url  # http://192.168.1.20:8080
        # ... rest of config

    def collect_mfa_config(self):
        # Connect via API to existing Keycloak LXC
        token = self._get_token()
        response = requests.get(f"{self.url}/admin/realms/{self.realm}/authentication/flows")
        # ... collect evidence
```

---

## Resource Requirements

### GRC Core (Minimal)
- **CPU**: 1 vCPU
- **RAM**: 2GB
- **Disk**: 20GB
- **Services**: PostgreSQL + CLI container only

### AI Foundry (Optional)
- **CPU**: 4 vCPU
- **RAM**: 8GB
- **Disk**: 50GB
- **Services**: Temporal, LiteLLM, Obot, GooseAI, Langfuse, Redis

### Total
- **With AI Foundry**: 5 vCPU, 10GB RAM, 70GB disk
- **Without AI Foundry**: 1 vCPU, 2GB RAM, 20GB disk

---

## Key Advantages

1. ✅ **Zero Bloat** - No bundled services
2. ✅ **Minimal Footprint** - Just 1-2 LXCs for GRC
3. ✅ **Leverages Existing Infrastructure** - Uses your Proxmox helper script LXCs
4. ✅ **Flexible** - Deploy AI Foundry separately or not at all
5. ✅ **Integration-First** - Connects via API to existing services
6. ✅ **No Duplication** - Doesn't bundle Wazuh, Keycloak, etc.

---

## Network Architecture

```
Proxmox vmbr0 (192.168.1.0/24)
│
├─ 192.168.1.10  - Wazuh (existing LXC)
├─ 192.168.1.11  - Netbox (existing LXC)
├─ 192.168.1.20  - Keycloak (existing LXC)
├─ 192.168.1.21  - FreeIPA (existing LXC)
├─ 192.168.1.22  - Infisical (existing LXC)
├─ 192.168.1.23  - Vaultwarden (existing LXC)
├─ 192.168.1.30  - OneDev (existing LXC)
├─ 192.168.1.31  - Zot (existing LXC)
│
├─ 192.168.1.100 - GRC Core (new minimal LXC)
└─ 192.168.1.101 - AI Foundry (new LXC, optional)
```

All communication via standard IP networking - no Docker networking required!

---

## Comparison: Bloated vs Minimal

| Aspect | Bloated (V2.0) | Minimal (V2.1) |
|--------|----------------|----------------|
| **GRC Core** | PostgreSQL + CLI | PostgreSQL + CLI |
| **Wazuh** | Bundled in compose | External LXC (API connection) |
| **Netbox** | Bundled in compose | External LXC (API connection) |
| **Keycloak** | Bundled in compose | External LXC (API connection) |
| **FreeIPA** | Bundled in compose | External LXC (API connection) |
| **Infisical** | Bundled in compose | External LXC (API connection) |
| **OneDev** | Bundled in compose | External LXC (API connection) |
| **Zot** | Bundled in compose | External LXC (API connection) |
| **AI Foundry** | Bundled in GRC compose | Separate compose, optional |
| **LXCs Required** | 1-2 (huge) | 1-2 (minimal) |
| **Total vCPU** | 14+ | 1-5 |
| **Total RAM** | 28GB+ | 2-10GB |
| **Disk** | 250GB+ | 20-70GB |

**Result: 90% smaller footprint!**

---

## Next: Creating Minimal Compose Files

Now creating:
1. ✅ `docker-compose.grc-core.yml` - Just PostgreSQL + CLI
2. ✅ `docker-compose.ai-foundry.yml` - AI stack (separate)
3. ✅ `.env.example` - External service connections only
4. ✅ Integration collectors for existing LXCs
