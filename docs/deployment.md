# CreatureGRC Deployment Guide

## Quick Start (10 Minutes)

### Prerequisites

- Docker & Docker Compose
- 8GB RAM minimum
- API keys (Anthropic, OpenAI, or both)

### 1. Clone and Configure

```bash
git clone <your-repo>
cd CreatureGRC

# Copy example config
cp config.example.yaml config.yaml

# Set environment variables
cat > .env <<EOF
DB_PASSWORD=your-secure-password
ANTHROPIC_API_KEY=sk-ant-your-key
OPENAI_API_KEY=sk-your-key
GOOGLE_API_KEY=your-key
LITELLM_MASTER_KEY=your-master-key
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
EOF

# Load environment
source .env
export $(cat .env | xargs)
```

### 2. Start Infrastructure

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### 3. Initialize Database

```bash
# Database is auto-initialized from schema.sql

# Verify
docker-compose exec postgres psql -U grc_user -d grc_platform -c \
  "SELECT name, version FROM compliance_frameworks;"
```

### 4. Import Control Libraries

```bash
# Install Python dependencies
pip install -r requirements.txt

# Import NIST 800-53 (1000+ controls)
python import_oscal_controls.py --config config.yaml

# Import ComplianceForge SCF (download required)
# 1. Download from https://www.complianceforge.com/scf
# 2. Save as SCF_2024.1.xlsx
python import_scf_controls.py --config config.yaml --scf-excel SCF_2024.1.xlsx

# Import CSA CCM (auto-downloads)
python import_csa_ccm.py --config config.yaml --download
```

### 5. Map Creatures to Controls

```bash
# Populate example creatures
python map_creatures_to_controls.py \
  --config config.yaml \
  --populate-examples \
  --auto-approve \
  --framework SOC2
```

### 6. Start Evidence Collection

```bash
# Manual one-time collection
python evidence_collector.py --config config.yaml --framework SOC2

# Or trigger via Temporal workflow
docker-compose exec temporal-worker python -c "
from temporal_workflows import DailyEvidenceCollectionWorkflow
from temporalio.client import Client
import asyncio

async def main():
    client = await Client.connect('temporal:7233')
    result = await client.execute_workflow(
        DailyEvidenceCollectionWorkflow.run,
        'SOC2',
        id='evidence-collection-manual',
        task_queue='grc-compliance'
    )
    print(result)

asyncio.run(main())
"
```

### 7. Generate Audit Package

```bash
python generate_audit_package.py \
  --client your-company \
  --framework SOC2 \
  --config config.yaml

# Output: /var/lib/grc/audit-packages/your-company-SOC2-evidence-20251028.zip
```

---

## Architecture Overview

```
                    ┌─────────────────────┐
                    │   Trust Center UI   │
                    │   (Port 3000)       │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │     API Server      │
                    │     (Port 8000)     │
                    └──────────┬──────────┘
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                  │
            ▼                  ▼                  ▼
    ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
    │   LiteLLM    │   │  Temporal.io │   │     Obot     │
    │ Multi-LLM    │   │  Workflows   │   │  Automation  │
    │ (Port 4000)  │   │  (Port 7233) │   │  (Port 9000) │
    └──────────────┘   └──────────────┘   └──────────────┘
            │                  │                  │
            └──────────────────┼──────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    PostgreSQL       │
                    │    (Port 5432)      │
                    └─────────────────────┘
```

---

## Service Details

### PostgreSQL (Port 5432)
- **Purpose**: GRC data storage
- **Access**: `psql -U grc_user -d grc_platform -h localhost`
- **Backup**: `docker-compose exec postgres pg_dump -U grc_user grc_platform > backup.sql`

### Temporal.io (Port 7233)
- **Purpose**: Durable workflow orchestration
- **Web UI**: http://localhost:8080
- **Workflows**:
  - Daily evidence collection
  - Continuous control testing
  - Audit package generation

### Temporal Worker
- **Purpose**: Executes workflows
- **Logs**: `docker-compose logs -f temporal-worker`

### LiteLLM (Port 4000)
- **Purpose**: Multi-LLM gateway (Claude, GPT-4, Gemini)
- **API**: http://localhost:4000
- **Test**: `curl http://localhost:4000/health`

### Obot (Port 9000)
- **Purpose**: High-level workflow automation
- **Workflows**: `./obot_workflows/*.yaml`
- **Triggers**: API webhooks, schedules, file watches

### API Server (Port 8000)
- **Purpose**: REST API for GRC operations
- **Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health

### Trust Center UI (Port 3000)
- **Purpose**: Public compliance portal
- **URL**: http://localhost:3000

---

## Scheduled Workflows

### Daily (2 AM)
```yaml
# Evidence collection from all sources
workflow: DailyEvidenceCollectionWorkflow
sources:
  - Wazuh (auth logs, security alerts)
  - Keycloak (MFA config, user lists)
  - OpenSCAP (compliance scans)
  - GitHub (audit logs)
```

### Continuous
```yaml
# Control testing based on frequency
workflow: ContinuousControlTestingWorkflow
frequency:
  daily: High-priority controls
  weekly: Standard controls
  monthly: Low-priority controls
```

### Quarterly
```yaml
# Vendor risk assessment
workflow: vendor-risk-assessment (Obot)
actions:
  - Check SOC2 report validity
  - Search vendor security pages
  - Calculate risk scores
  - Create Jira tickets for high-risk vendors
```

---

## Configuration

### Environment Variables

```bash
# Required
DB_PASSWORD=<secure-password>
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# Optional (for specific integrations)
WAZUH_PASSWORD=...
KEYCLOAK_CLIENT_SECRET=...
GITHUB_TOKEN=...
SLACK_WEBHOOK_URL=...
JIRA_API_TOKEN=...
```

### config.yaml

See `config.example.yaml` for full configuration options.

Key sections:
- **database**: PostgreSQL connection
- **llm**: LiteLLM configuration (primary + fallback models)
- **evidence**: Collection settings and schedules
- **wazuh/keycloak/github**: Integration credentials
- **temporal**: Workflow orchestration settings
- **notifications**: Slack, email settings

---

## Monitoring & Troubleshooting

### Health Checks

```bash
# Check all services
docker-compose ps

# Check API health
curl http://localhost:8000/health

# Check LiteLLM
curl http://localhost:4000/health

# Check Temporal
curl http://localhost:8080
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f temporal-worker
docker-compose logs -f api
docker-compose logs -f litellm
```

### Database Queries

```bash
# View compliance coverage
docker-compose exec postgres psql -U grc_user -d grc_platform -c \
  "SELECT * FROM v_compliance_coverage LIMIT 10;"

# View risk register
docker-compose exec postgres psql -U grc_user -d grc_platform -c \
  "SELECT * FROM v_risk_register;"

# View audit readiness
docker-compose exec postgres psql -U grc_user -d grc_platform -c \
  "SELECT * FROM v_audit_readiness;"
```

### Temporal Workflows

```bash
# View Temporal UI
open http://localhost:8080

# List workflows
docker-compose exec temporal temporal workflow list

# Describe workflow
docker-compose exec temporal temporal workflow describe \
  --workflow-id evidence-collection-daily
```

---

## Production Deployment

### Security Hardening

1. **Use proper SSL/TLS certificates**
   ```bash
   # Generate Let's Encrypt certs
   certbot certonly --webroot -w /var/www/html -d compliance.example.com
   ```

2. **Secure database**
   ```yaml
   # In docker-compose.yml, remove port exposure
   postgres:
     # ports:
     #   - "5432:5432"  # Remove this in production
   ```

3. **Enable database encryption**
   ```bash
   # Use encrypted volumes
   # Enable PostgreSQL SSL
   # Enable backup encryption
   ```

4. **Set up firewall**
   ```bash
   # Only expose necessary ports
   ufw allow 80/tcp
   ufw allow 443/tcp
   ufw deny 5432/tcp  # Block database from outside
   ```

### High Availability

```yaml
# Example: Multiple workers
temporal-worker:
  deploy:
    replicas: 3
    restart_policy:
      condition: on-failure

# Example: Database replication
postgres-replica:
  image: postgres:16
  environment:
    POSTGRES_MASTER_HOST: postgres
```

### Backup Strategy

```bash
# Daily database backup
0 1 * * * docker-compose exec postgres pg_dump -U grc_user grc_platform | gzip > /backup/grc-$(date +\%Y\%m\%d).sql.gz

# Weekly full backup
0 2 * * 0 tar -czf /backup/grc-full-$(date +\%Y\%m\%d).tar.gz /var/lib/grc

# Offsite backup
0 3 * * * rclone sync /backup remote:grc-backups
```

---

## Upgrading

### Update Code

```bash
git pull
docker-compose build
docker-compose up -d
```

### Database Migrations

```bash
# Apply schema changes
docker-compose exec postgres psql -U grc_user -d grc_platform -f migrations/001-add-column.sql
```

### Update Control Libraries

```bash
# Re-import updated controls
python import_oscal_controls.py --config config.yaml
```

---

## Cost Optimization

### LLM Costs

```yaml
# In config.yaml
llm:
  cost_limits:
    daily_max_usd: 100  # Hard limit
    per_request_max_tokens: 2000  # Reduce tokens

  # Use cheaper fallback models
  primary_model: "claude-sonnet-4"
  fallback_models:
    - "gpt-3.5-turbo"  # Much cheaper
```

### Caching

```python
# Enable LiteLLM caching
litellm:
  cache:
    type: redis
    host: redis
```

---

## Support & Community

- **Documentation**: https://docs.creature-grc.io
- **Issues**: https://github.com/your-org/CreatureGRC/issues
- **Discord**: https://discord.gg/creature-grc
- **Email**: support@creature-grc.io

---

## License

Open source (MIT License) - Free for commercial use
