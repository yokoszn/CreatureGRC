# CreatureGRC Minimal - Quick Start

## What This Is

**CreatureGRC Minimal** = Just PostgreSQL + CLI container

- ✅ No bundled services (Wazuh, Keycloak, Netbox, etc.)
- ✅ Connects to your **existing Proxmox LXC services** via IP/API
- ✅ AI Foundry is **separate compose** (optional)
- ✅ Total footprint: **1-2 LXCs, 2-10GB RAM**

---

## Your Existing Infrastructure

These are already deployed in **individual Proxmox LXCs** (via helper scripts):

| Service | LXC IP | Purpose |
|---------|---------|---------|
| **Wazuh** | 192.168.1.10:55000 | SIEM/EDR |
| **Netbox** | 192.168.1.11:8000 | IPAM/DCIM |
| **Keycloak** | 192.168.1.20:8080 | SSO/Identity |
| **FreeIPA** | 192.168.1.21:443 | LDAP/CA |
| **Infisical** | 192.168.1.22:8080 | Secrets |
| **Vaultwarden** | 192.168.1.23:8080 | Passwords |
| **OneDev** | 192.168.1.30:6610 | Git |
| **Zot** | 192.168.1.31:5000 | Registry |

CreatureGRC **connects to these via API** - no bundling!

---

## Deploy GRC Core (Minimal - 5 minutes)

### Step 1: Create LXC for GRC Core

```bash
# Create minimal LXC (1 vCPU, 2GB RAM, 20GB disk)
pct create 100 local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst \
  --hostname grc-core \
  --memory 2048 \
  --cores 1 \
  --rootfs local-lvm:20 \
  --net0 name=eth0,bridge=vmbr0,ip=192.168.1.100/24,gw=192.168.1.1 \
  --unprivileged 1 \
  --features nesting=1 \
  --onboot 1

# Start LXC
pct start 100

# Install Docker
pct exec 100 -- bash -c "curl -fsSL https://get.docker.com | sh"
```

### Step 2: Copy Files and Deploy

```bash
# Copy compose file and env
pct push 100 docker-compose.grc-core.yml /root/docker-compose.yml
pct push 100 .env.minimal.example /root/.env

# Edit .env with your IPs and passwords
pct exec 100 -- vim /root/.env

# Deploy
pct exec 100 -- docker compose -f /root/docker-compose.yml up -d

# Check status
pct exec 100 -- docker compose ps
```

### Step 3: Verify

```bash
# Enter CLI container
pct exec 100 -- docker exec -it grc-cli bash

# List frameworks (should be empty initially)
creaturegrc frameworks list

# Test connectivity to existing services
curl -k https://192.168.1.10:55000  # Wazuh
curl http://192.168.1.11:8000       # Netbox
curl http://192.168.1.20:8080       # Keycloak
```

---

## Deploy AI Foundry (Optional - Separate LXC)

### Step 1: Create AI Foundry LXC

```bash
# Create LXC for AI Foundry (4 vCPU, 8GB RAM, 50GB disk)
pct create 101 local:vztmpl/ubuntu-22.04-standard_22.04-1_amd64.tar.zst \
  --hostname ai-foundry \
  --memory 8192 \
  --cores 4 \
  --rootfs local-lvm:50 \
  --net0 name=eth0,bridge=vmbr0,ip=192.168.1.101/24,gw=192.168.1.1 \
  --unprivileged 1 \
  --features nesting=1 \
  --onboot 1

# Start and install Docker
pct start 101
pct exec 101 -- bash -c "curl -fsSL https://get.docker.com | sh"
```

### Step 2: Deploy AI Stack

```bash
# Copy compose file
pct push 101 docker-compose.ai-foundry.yml /root/docker-compose.yml
pct push 101 .env.minimal.example /root/.env

# Edit .env
pct exec 101 -- vim /root/.env

# Deploy
pct exec 101 -- docker compose -f /root/docker-compose.yml up -d

# Check status
pct exec 101 -- docker compose ps
```

---

## Import Control Libraries

```bash
# Enter GRC CLI container
pct exec 100 -- docker exec -it grc-cli bash

# NIST 800-53 Rev 5 (1000+ controls)
python /app/import_oscal_controls.py --config /app/config/config.yaml

# ComplianceForge SCF (requires manual download)
# 1. Download from https://www.complianceforge.com/scf
# 2. Copy to LXC:
exit
pct push 100 SCF_2024.1.xlsx /tmp/SCF_2024.1.xlsx
pct exec 100 -- docker exec -it grc-cli bash
python /app/import_scf_controls.py --config /app/config/config.yaml --scf-excel /tmp/SCF_2024.1.xlsx

# CSA CCM (auto-downloads)
python /app/import_csa_ccm.py --config /app/config/config.yaml --download

# Verify
creaturegrc frameworks list
```

---

## Collect Evidence from Existing LXCs

### From Wazuh (LXC 192.168.1.10)

```bash
# Collect authentication logs
docker exec grc-cli python /app/evidence_collector.py \
  --config /app/config/config.yaml \
  --framework SOC2

# Or use CLI
docker exec grc-cli creaturegrc collect evidence --source wazuh --days 90
```

### From Netbox (LXC 192.168.1.11)

```bash
# Sync infrastructure creatures
docker exec grc-cli creaturegrc creatures sync --source netbox

# List synced creatures
docker exec grc-cli creaturegrc creatures list
```

### From Keycloak (LXC 192.168.1.20)

```bash
# Collect MFA configuration
docker exec grc-cli python /app/evidence_collector.py \
  --config /app/config/config.yaml \
  --source keycloak

# Or use CLI
docker exec grc-cli creaturegrc collect evidence --source keycloak
```

---

## Generate Audit Package

```bash
docker exec grc-cli python /app/generate_audit_package.py \
  --client "Your Company" \
  --framework SOC2 \
  --config /app/config/config.yaml

# Output: /var/lib/grc/audit-packages/Your-Company-SOC2-evidence-20251028.zip

# Copy from LXC to Proxmox host
pct pull 100 /var/lib/grc/evidence/audit-packages/... /tmp/
```

---

## Resource Usage

### GRC Core Only (Minimal):
- **LXC 100 (grc-core)**: 1 vCPU, 2GB RAM, 20GB disk
- **Services**: PostgreSQL + CLI container
- **Footprint**: Tiny

### With AI Foundry (Optional):
- **LXC 100 (grc-core)**: 1 vCPU, 2GB RAM, 20GB disk
- **LXC 101 (ai-foundry)**: 4 vCPU, 8GB RAM, 50GB disk
- **Total**: 5 vCPU, 10GB RAM, 70GB disk

---

## Network Diagram

```
Proxmox vmbr0 (192.168.1.0/24)
│
├─ 192.168.1.10  - Wazuh (existing) ◄────────┐
├─ 192.168.1.11  - Netbox (existing) ◄───────┤
├─ 192.168.1.20  - Keycloak (existing) ◄─────┤
├─ 192.168.1.21  - FreeIPA (existing) ◄──────┤
├─ 192.168.1.22  - Infisical (existing) ◄────┤  API Connections
├─ 192.168.1.23  - Vaultwarden (existing) ◄──┤
├─ 192.168.1.30  - OneDev (existing) ◄───────┤
├─ 192.168.1.31  - Zot (existing) ◄──────────┘
│
├─ 192.168.1.100 - GRC Core (NEW) ◄──────────── Just PostgreSQL + CLI
│
└─ 192.168.1.101 - AI Foundry (OPTIONAL) ◄──── Separate LXC
```

---

## CLI Commands

```bash
# List frameworks
docker exec grc-cli creaturegrc frameworks list

# List controls
docker exec grc-cli creaturegrc controls list --framework soc2

# Show control details
docker exec grc-cli creaturegrc controls show CC6.1

# Show compliance status
docker exec grc-cli creaturegrc status --framework soc2

# List creatures
docker exec grc-cli creaturegrc creatures list --criticality critical

# Sync from Netbox
docker exec grc-cli creaturegrc creatures sync --source netbox
```

---

## Advantages of Minimal Approach

1. ✅ **90% Smaller** - 2-10GB RAM vs 28GB+ for bundled
2. ✅ **No Duplication** - Uses existing LXCs
3. ✅ **Flexible** - Deploy AI Foundry separately or not at all
4. ✅ **Clean** - Each service in its own LXC (via Proxmox helpers)
5. ✅ **Maintainable** - Update services independently

---

## Troubleshooting

### Can't connect to existing LXCs?

```bash
# From GRC Core LXC, test connectivity
pct exec 100 -- docker exec grc-cli curl -k https://192.168.1.10:55000  # Wazuh
pct exec 100 -- docker exec grc-cli curl http://192.168.1.11:8000       # Netbox

# Check .env has correct IPs
pct exec 100 -- cat /root/.env | grep API_URL
```

### Database not initializing?

```bash
# Manual schema load
pct exec 100 -- docker exec -i grc-postgres psql -U grc_user -d grc_platform < /docker-entrypoint-initdb.d/01-schema.sql
```

### Check logs

```bash
pct exec 100 -- docker compose -f /root/docker-compose.yml logs -f
```

---

**CreatureGRC Minimal is production-ready!** 🚀

Deploy in 5 minutes with just PostgreSQL + CLI.
