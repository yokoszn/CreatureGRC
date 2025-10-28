# CreatureGRC V2 Quick Start
## Modular Zoned Architecture for Proxmox/LXC

---

## Architecture Overview

CreatureGRC V2 is **modular** - each zone is a self-contained stack that can be deployed independently or combined into a megamonolith.

### Zones (Each is a complete docker-compose stack):

1. **Zone 1: Dev & Artifacts** - OneDev (git) + Zot Registry (OCI)
2. **Zone 2: Security & Monitoring** - Wazuh + Tetragon + Netbox + Prometheus/Loki/Tempo/Grafana
3. **Zone 3: Secrets Management** - Infisical + Vaultwarden
4. **Zone 4: AI Agent Stack** - Temporal + LiteLLM + Obot + GooseAI + Langfuse
5. **Zone 6: Identity** - Keycloak + FreeIPA
6. **Zone 7: GRC Core** - PostgreSQL + CreatureGRC CLI (NO WEB UI)

---

## Deployment Options

### Option A: Full Megamonolith (All zones on one host)
```bash
# Copy all compose files to /opt/zones
mkdir -p /opt/zones
cp compose/*.yml /opt/zones/
cp compose/.env.example /opt/zones/.env

# Edit .env with your secrets
cd /opt/zones
vim .env

# Deploy all zones
docker-compose -f zone1-dev-artifacts.yml up -d
docker-compose -f zone2-security-monitoring.yml up -d
docker-compose -f zone3-secrets.yml up -d
docker-compose -f zone4-ai-agents.yml up -d
docker-compose -f zone6-identity.yml up -d
docker-compose -f zone7-grc-core.yml up -d
```

### Option B: Distributed Zones (Each zone in separate LXC)
```bash
# On Proxmox host, create LXCs for each zone
pct create 101 local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst \
  --hostname dev-artifacts \
  --memory 4096 --cores 2 --rootfs local-lvm:32 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp \
  --unprivileged 1 --features nesting=1

pct create 102 local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst \
  --hostname security-monitoring \
  --memory 8192 --cores 4 --rootfs local-lvm:64 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp \
  --unprivileged 1 --features nesting=1

# ... (repeat for other zones)

# Start all LXCs
pct start 101 && pct start 102 && pct start 103 && pct start 104 && pct start 106 && pct start 107

# Install Docker in each LXC
for id in 101 102 103 104 106 107; do
  pct exec $id -- bash -c "curl -fsSL https://get.docker.com | sh"
done

# Deploy each zone to its LXC
pct push 101 compose/zone1-dev-artifacts.yml /root/docker-compose.yml
pct push 101 compose/.env /root/.env
pct exec 101 -- docker-compose -f /root/docker-compose.yml up -d

# (Repeat for other zones)
```

---

## Quick Start: Zone 7 (GRC Core) Only

If you just want CreatureGRC CLI and database (minimum viable):

```bash
cd compose

# Copy and edit env
cp .env.example .env
vim .env  # Set at minimum: GRC_DB_PASSWORD

# Deploy GRC Core only
docker-compose -f zone7-grc-core.yml up -d

# Wait for database
docker-compose -f zone7-grc-core.yml ps

# Initialize database
docker-compose -f zone7-grc-core.yml exec cli psql \
  -h postgres -U grc_user -d grc_platform -f /app/schema.sql

# Verify
docker-compose -f zone7-grc-core.yml exec cli creaturegrc frameworks list
```

---

## Using the CLI

### Run commands in the CLI container

```bash
# Enter CLI container
docker exec -it grc-cli bash

# Or run commands directly
docker exec grc-cli creaturegrc frameworks list
docker exec grc-cli creaturegrc controls list --framework soc2
docker exec grc-cli creaturegrc creatures list
```

### Install CLI locally (alternative)

```bash
# Install CreatureGRC CLI package
cd cli
pip install -e .

# Configure connection (via .env or exports)
export GRC_DB_HOST=localhost
export GRC_DB_PORT=5432
export GRC_DB_NAME=grc_platform
export GRC_DB_USER=grc_user
export GRC_DB_PASSWORD=your-password

# Run commands
creaturegrc frameworks list
creaturegrc controls list --framework soc2
```

---

## Import Control Libraries

```bash
# NIST 800-53 (1000+ controls)
docker exec grc-cli python /app/import_oscal_controls.py \
  --config /app/config/config.yaml

# ComplianceForge SCF (requires manual download)
# 1. Download SCF_2024.1.xlsx from https://www.complianceforge.com/scf
# 2. Copy to container:
docker cp SCF_2024.1.xlsx grc-cli:/tmp/
docker exec grc-cli python /app/import_scf_controls.py \
  --config /app/config/config.yaml \
  --scf-excel /tmp/SCF_2024.1.xlsx

# CSA CCM (auto-downloads)
docker exec grc-cli python /app/import_csa_ccm.py \
  --config /app/config/config.yaml --download
```

---

## Integrate with Existing Services

### Connect to Wazuh (Zone 2)
```bash
# In .env:
WAZUH_API_URL=https://wazuh.example.com:55000
WAZUH_USER=grc-collector
WAZUH_PASSWORD=your-wazuh-password

# Collect evidence
docker exec grc-cli python /app/evidence_collector.py \
  --config /app/config/config.yaml \
  --framework SOC2
```

### Connect to Keycloak (Zone 6)
```bash
# In .env:
KEYCLOAK_URL=https://auth.example.com
KEYCLOAK_REALM=master
KEYCLOAK_CLIENT_ID=creaturegrc
KEYCLOAK_CLIENT_SECRET=your-secret

# Collect MFA config
docker exec grc-cli creaturegrc collect evidence \
  --source keycloak
```

### Sync Creatures from Netbox (Zone 2)
```bash
# In .env:
NETBOX_API_URL=https://netbox.example.com
NETBOX_TOKEN=your-token

# Sync infrastructure
docker exec grc-cli creaturegrc creatures sync --source netbox
```

---

## Using Infisical for Secrets (Zone 3)

Instead of .env files, use Infisical:

```bash
# Deploy Infisical first
cd compose
docker-compose -f zone3-secrets.yml up -d

# Install Infisical CLI in GRC container
docker exec grc-cli bash -c \
  "curl -1sLf 'https://dl.cloudsmith.io/public/infisical/infisical-cli/setup.deb.sh' | bash && \
   apt-get update && apt-get install -y infisical"

# Login to Infisical
docker exec -it grc-cli infisical login

# Run commands with secrets injected
docker exec grc-cli infisical run --env=production -- \
  creaturegrc collect evidence --framework soc2
```

---

## Zone Inter-connectivity

Zones communicate via:
- **DNS** (docker network or external DNS)
- **API endpoints** (configured in .env)
- **Shared networks** (optional bridge for megamonolith)

### Example: GRC Core → All Zones

```
Zone 7 (GRC Core)
  ↓ API calls ↓

├─→ Zone 1: OneDev API (git audit logs)
├─→ Zone 2: Wazuh API (security events)
├─→ Zone 2: Netbox API (asset inventory)
├─→ Zone 3: Infisical API (secret metadata)
├─→ Zone 4: LiteLLM API (AI questionnaires)
├─→ Zone 4: Temporal API (workflow triggers)
├─→ Zone 6: Keycloak API (MFA status)
└─→ Zone 6: FreeIPA API (cert issuance logs)
```

---

## Resource Requirements

### Minimum (GRC Core only):
- 1 vCPU, 2GB RAM, 10GB disk

### Recommended per Zone:
- **Zone 1** (Dev): 2 vCPU, 4GB RAM, 50GB disk
- **Zone 2** (Security): 4 vCPU, 8GB RAM, 100GB disk
- **Zone 3** (Secrets): 1 vCPU, 2GB RAM, 10GB disk
- **Zone 4** (AI): 4 vCPU, 8GB RAM, 50GB disk
- **Zone 6** (Identity): 2 vCPU, 4GB RAM, 20GB disk
- **Zone 7** (GRC Core): 1 vCPU, 2GB RAM, 20GB disk

### Total Megamonolith:
- 14 vCPU, 28GB RAM, 250GB disk

---

## Proxmox LXC Best Practices

### Create unprivileged LXC with nested Docker:

```bash
# Download Ubuntu template
pveam download local ubuntu-22.04-standard_22.04-1_amd64.tar.zst

# Create LXC
pct create 107 local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst \
  --hostname grc-core \
  --ostype ubuntu \
  --memory 2048 \
  --swap 512 \
  --cores 1 \
  --rootfs local-lvm:20 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp,firewall=1 \
  --unprivileged 1 \
  --features nesting=1,keyctl=1 \
  --onboot 1

# Start LXC
pct start 107

# Install Docker
pct exec 107 -- bash -c "apt-get update && apt-get install -y curl"
pct exec 107 -- bash -c "curl -fsSL https://get.docker.com | sh"
pct exec 107 -- bash -c "apt-get install -y docker-compose-plugin"

# Copy compose files
pct push 107 compose/zone7-grc-core.yml /root/docker-compose.yml
pct push 107 compose/.env /root/.env

# Deploy
pct exec 107 -- docker compose -f /root/docker-compose.yml up -d
```

---

## Next Steps

1. ✅ **Deploy zones** (start with Zone 7 GRC Core)
2. ✅ **Import control libraries** (NIST, SCF, CCM)
3. ✅ **Sync creatures** from Netbox
4. ✅ **Collect evidence** from Wazuh, Keycloak, etc.
5. ✅ **Generate audit packages**

---

## Troubleshooting

### Check zone health:
```bash
docker-compose -f compose/zone7-grc-core.yml ps
docker-compose -f compose/zone7-grc-core.yml logs -f
```

### Database not initializing:
```bash
# Manual schema load
docker exec -i grc-postgres psql -U grc_user -d grc_platform < schema.sql
```

### Can't connect to other zones:
```bash
# Check network connectivity
docker exec grc-cli ping wazuh.example.com
docker exec grc-cli curl -v https://auth.example.com
```

---

## Architecture Differences from V1

| Aspect | V1 (Monolithic) | V2 (Modular Zones) |
|--------|-----------------|---------------------|
| **Deployment** | Single docker-compose | 6+ separate compose files |
| **Services** | All bundled | Each zone self-contained |
| **UI** | Web UI planned | CLI-only |
| **Secrets** | .env files | Infisical integration |
| **Infrastructure** | Generic Docker | Proxmox + LXCs |
| **Scale** | Vertical (bigger host) | Horizontal (more LXCs) |

---

**CreatureGRC V2 is production-ready. Deploy your zones today!** 🚀
