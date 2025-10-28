# Cloud & SaaS Service Tracking

This guide explains how CreatureGRC discovers and tracks cloud services and SaaS platforms that developers use, including shadow IT created through tools like v0.dev.

## Why Track Cloud/SaaS?

Modern development teams use cloud services extensively:
- **Vercel** for hosting and deployments
- **Supabase** for backend-as-a-service
- **Neon** for serverless PostgreSQL
- **GitHub** for code and CI/CD
- **Cloudflare** for CDN and security
- **v0.dev** for AI-generated application templates

These services often get created **outside formal approval processes**, creating:
- **Shadow IT risk**: Ungoverned infrastructure with unknown data classification
- **Compliance gaps**: Services not mapped to controls
- **Cost sprawl**: Untracked spending on cloud services
- **Security blind spots**: No visibility into configurations, secrets, or access

CreatureGRC solves this by automatically discovering these services via API integration.

## Supported Platforms

### Vercel
**What CreatureGRC Tracks:**
- Projects and deployments
- Domain configurations
- Environment variables (detects secrets)
- Team membership and access
- Deployment frequency and source (GitHub repos)
- Projects created via v0.dev templates

**API Requirements:**
- Vercel API token with `read` scope
- Team-level or personal account access

**Configuration:**
```bash
# .env
VERCEL_API_TOKEN=your-vercel-token
VERCEL_TEAM_ID=your-team-id  # Optional, for team accounts
```

**Evidence Collected:**
- CM-8 (System Inventory): All Vercel projects
- CM-3 (Change Management): Deployment history
- SA-9 (Third-Party Services): External service usage
- SC-13 (Cryptography): SSL/TLS configurations

### Supabase
**What CreatureGRC Tracks:**
- Database instances and schemas
- Authentication configurations
- Storage buckets and policies
- API usage and keys
- Database size and table counts
- Region and data residency
- Backup policies

**API Requirements:**
- Supabase Management API token
- Project API keys for each instance

**Configuration:**
```bash
# .env
SUPABASE_ACCESS_TOKEN=your-access-token
```

**Evidence Collected:**
- CM-8 (System Inventory): Database instances
- AC-3 (Access Enforcement): Auth configs, RLS policies
- SC-28 (Data at Rest): Encryption settings
- CP-9 (Backup): Backup configurations

**Data Classification Warnings:**
CreatureGRC scans table names and warns about:
- Tables named "users", "customers", "payments" → Likely PII
- Tables with "health", "medical" columns → Likely PHI
- Tables with "card", "ssn", "account" → Likely sensitive data

### Neon
**What CreatureGRC Tracks:**
- PostgreSQL database instances
- Branch structures (main, dev, feature branches)
- Compute settings and auto-scaling
- Storage usage
- Connection strings and access
- Database roles and privileges

**API Requirements:**
- Neon API key

**Configuration:**
```bash
# .env
NEON_API_KEY=your-neon-api-key
```

**Evidence Collected:**
- CM-8 (System Inventory): Database instances
- CM-3 (Change Management): Branch-based development tracking
- SC-28 (Data at Rest): Encryption settings
- AU-2 (Audit Events): Database activity logs

### GitHub
**What CreatureGRC Tracks:**
- Repositories (public/private/internal)
- Organization membership and teams
- Deploy keys and secrets
- GitHub Actions workflows
- Branch protection rules
- Code review requirements
- Audit logs (Enterprise only)

**API Requirements:**
- GitHub Personal Access Token or GitHub App
- Scopes: `repo`, `admin:org`, `read:audit_log` (Enterprise)

**Configuration:**
```bash
# .env
GITHUB_TOKEN=your-github-token
GITHUB_ORG=your-organization-name
```

**Evidence Collected:**
- CM-3 (Change Management): Code reviews, branch protection
- AC-3 (Access Enforcement): Repository access controls
- AU-2 (Audit Events): GitHub audit logs
- SA-10 (Developer Configuration): CI/CD pipeline security

### Cloudflare
**What CreatureGRC Tracks:**
- DNS zones and records
- CDN and proxy settings
- WAF rules and firewall configurations
- SSL/TLS certificates and settings
- DDoS protection status
- Page rules and redirects

**API Requirements:**
- Cloudflare API token with `Zone:Read` permissions

**Configuration:**
```bash
# .env
CLOUDFLARE_API_TOKEN=your-cloudflare-token
CLOUDFLARE_ACCOUNT_ID=your-account-id
```

**Evidence Collected:**
- SC-7 (Boundary Protection): Firewall rules, CDN configs
- SC-8 (Transmission Confidentiality): SSL/TLS settings
- SC-13 (Cryptography): Certificate management
- SI-4 (Information System Monitoring): WAF logs

### v0.dev (Vercel AI)
**What CreatureGRC Tracks:**
- AI-generated projects
- Template usage patterns
- Deployment frequency from v0.dev templates
- Associated Vercel projects

**API Requirements:**
- Vercel API token (v0.dev projects appear as Vercel deployments)

**Detection:**
CreatureGRC detects v0.dev usage by:
- Project metadata indicating v0.dev origin
- Template references in package.json
- Deployment source URLs
- Git commit messages referencing v0.dev

**Risk Flags:**
- ⚠️ Projects created without security review
- ⚠️ AI-generated code not reviewed by senior developers
- ⚠️ Environment variables copied from templates (may contain example secrets)

## Shadow IT Discovery Workflow

### Step 1: Configure API Access
Add API tokens for all platforms to your `.env` file:

```bash
# Cloud/SaaS Platforms
VERCEL_API_TOKEN=vercel_xxx
SUPABASE_ACCESS_TOKEN=sbp_xxx
NEON_API_KEY=neon_xxx
GITHUB_TOKEN=ghp_xxx
CLOUDFLARE_API_TOKEN=cf_xxx
```

### Step 2: Run Discovery Scan
```bash
# Scan all cloud platforms for Creatures
creaturegrc discover cloud --all

# Or scan specific platforms
creaturegrc discover cloud --platform vercel
creaturegrc discover cloud --platform supabase
creaturegrc discover cloud --platform neon
```

**Output:**
```
Scanning Vercel...
✓ Found 12 projects across 2 teams
  ├─ 4 projects created in last 30 days
  ├─ 2 projects created via v0.dev templates
  └─ 3 projects with environment variables containing "SECRET"

Scanning Supabase...
✓ Found 8 database instances
  ├─ 3 instances in us-east-1
  ├─ 2 instances with tables containing PII (users, payments)
  └─ 1 instance missing backup configuration

Scanning Neon...
✓ Found 5 database instances
  ├─ 12 total branches across all databases
  └─ 2 instances with compute auto-scaling enabled

Scanning GitHub...
✓ Found 47 repositories
  ├─ 23 private repositories
  ├─ 8 repositories with GitHub Actions enabled
  └─ 4 repositories missing branch protection

Scanning Cloudflare...
✓ Found 6 DNS zones
  ├─ 4 zones with proxy enabled (CDN)
  ├─ 2 zones with WAF enabled
  └─ All zones have SSL/TLS Full (Strict)

Total: 78 new Creatures discovered
  ├─ 52 Applications (Vercel, Supabase, Neon)
  ├─ 18 Accounts (developer accounts on each platform)
  └─ 8 Infrastructure (Cloudflare zones)
```

### Step 3: Review Risk Assessment
```bash
# Show shadow IT risks
creaturegrc risks list --source cloud-discovery

Shadow IT Risks:
┌─────────────────────────────┬──────────┬────────────────────────────┐
│ Service                      │ Severity │ Issue                      │
├─────────────────────────────┼──────────┼────────────────────────────┤
│ customer-db-staging          │ HIGH     │ PII without classification │
│ api-prototype                │ MEDIUM   │ No security review         │
│ internal-tools-preview       │ MEDIUM   │ Environment secrets exposed│
│ alex-personal-blog           │ LOW      │ Personal project on co acct│
│ supabase-test-db             │ LOW      │ No backup policy           │
└─────────────────────────────┴──────────┴────────────────────────────┘

Recommendations:
1. Review "customer-db-staging" for PII - classify and apply controls
2. Add backup policy to "supabase-test-db"
3. Security review required for 4 v0.dev generated projects
4. Separate personal projects to personal accounts
```

### Step 4: Map to Controls
```bash
# Automatically map discovered services to controls
creaturegrc controls map-creatures --source cloud-discovery

Mapping cloud services to controls...
✓ Mapped 78 Creatures to 47 controls
  ├─ CM-8 (System Inventory): All 78 services
  ├─ SA-9 (Third-Party Services): All 78 services
  ├─ SC-28 (Data at Rest): 13 database instances
  ├─ SC-13 (Cryptography): 6 Cloudflare zones
  └─ CM-3 (Change Management): 12 Vercel projects
```

### Step 5: Set Up Continuous Monitoring
```bash
# Enable daily cloud discovery scans
creaturegrc schedule create \
  --name "Daily Cloud Discovery" \
  --task "discover cloud --all" \
  --frequency daily \
  --time "02:00"

# Send Slack alerts for new shadow IT
creaturegrc alerts create \
  --name "Shadow IT Alert" \
  --condition "new_cloud_service_detected" \
  --action "slack_notify" \
  --channel "#security-alerts"
```

## Example: Tracking a v0.dev Project Lifecycle

### Discovery
Developer uses v0.dev to generate a dashboard:
```
1. alex@v0.dev → Generates "customer-dashboard" template
2. v0.dev → Creates GitHub repo "alex/customer-dash"
3. alex@vercel → Deploys to "customer-dashboard-staging.vercel.app"
4. alex@supabase → Creates "customer-db-staging" database
5. alex@cloudflare → Sets up "dashboard.example.com" domain
```

### CreatureGRC Detection (within 24 hours)
```bash
$ creaturegrc creatures show customer-dashboard-staging

Creature: customer-dashboard-staging (Application)
Type: Vercel Project
Created: 2024-10-15 14:23 UTC
Created By: alex.johnson (Identity)
Source: v0.dev template (AI-generated)

Connected Services:
├─ GitHub: alex/customer-dash (Repository)
├─ Supabase: customer-db-staging (Database)
└─ Cloudflare: dashboard.example.com (DNS)

Environment Variables (12):
├─ SUPABASE_URL=https://xxx.supabase.co
├─ SUPABASE_ANON_KEY=eyJhbG... (Public)
├─ SUPABASE_SERVICE_KEY=eyJhbG... (SECRET - ⚠️  Exposed in Vercel dashboard!)
├─ DATABASE_URL=postgresql://... (SECRET)
└─ ... (8 more)

Risk Assessment:
⚠️  Created via v0.dev without security review
⚠️  Supabase service key exposed in environment variables
⚠️  Database contains "users" and "payments" tables (likely PII)
⚠️  No data classification applied
⚠️  No backup policy configured

Mapped Controls:
├─ CM-8 (System Inventory) - SATISFIED
├─ SA-9 (Third-Party Services) - SATISFIED
├─ SC-28 (Data at Rest) - PARTIAL (needs classification)
└─ CP-9 (Backup) - NOT SATISFIED

Recommended Actions:
1. Security review: Code review of v0.dev generated code
2. Data classification: Review database for PII/PHI
3. Secrets management: Move service keys to Infisical
4. Backup policy: Enable Supabase automated backups
5. Access review: Limit who can access this project
```

## CLI Commands

### Discovery
```bash
# Discover all cloud services
creaturegrc discover cloud --all

# Discover specific platform
creaturegrc discover cloud --platform vercel
creaturegrc discover cloud --platform supabase

# Discover for specific user
creaturegrc discover cloud --identity alex.johnson

# Dry run (show what would be discovered)
creaturegrc discover cloud --all --dry-run
```

### Listing
```bash
# List all cloud Creatures
creaturegrc creatures list --type application --platform cloud

# List by platform
creaturegrc creatures list --platform vercel
creaturegrc creatures list --platform supabase

# List by creator
creaturegrc creatures list --created-by alex.johnson

# List v0.dev projects only
creaturegrc creatures list --source v0.dev
```

### Risk Assessment
```bash
# Show all cloud risks
creaturegrc risks list --source cloud

# Show risks for specific service
creaturegrc risks show customer-dashboard-staging

# Export risk report
creaturegrc risks export --format pdf --output cloud-risks-report.pdf
```

### Evidence Collection
```bash
# Collect evidence from cloud platforms
creaturegrc collect evidence --source vercel
creaturegrc collect evidence --source supabase
creaturegrc collect evidence --source github

# Generate cloud compliance report
creaturegrc audit generate \
  --framework soc2 \
  --scope cloud-services \
  --output cloud-audit-package/
```

## API Integration Examples

### Vercel API
```python
# scripts/collectors/vercel_collector.py
import requests

def collect_vercel_projects(api_token, team_id=None):
    """Collect all Vercel projects and create Creatures."""

    headers = {"Authorization": f"Bearer {api_token}"}
    url = f"https://api.vercel.com/v9/projects"

    if team_id:
        url += f"?teamId={team_id}"

    response = requests.get(url, headers=headers)
    projects = response.json()["projects"]

    for project in projects:
        creature = {
            "name": project["name"],
            "type": "application",
            "platform": "vercel",
            "metadata": {
                "url": f"https://{project['name']}.vercel.app",
                "created": project["createdAt"],
                "framework": project.get("framework"),
                "source": detect_v0_source(project),  # Detect v0.dev
                "env_vars": count_secrets(project["env"])
            },
            "controls": ["CM-8", "CM-3", "SA-9"]
        }

        create_creature(creature)
```

### Supabase API
```python
# scripts/collectors/supabase_collector.py
import requests

def collect_supabase_projects(access_token):
    """Collect all Supabase projects and scan for sensitive data."""

    headers = {"Authorization": f"Bearer {access_token}"}
    url = "https://api.supabase.com/v1/projects"

    response = requests.get(url, headers=headers)
    projects = response.json()

    for project in projects:
        # Connect to database and scan schema
        tables = scan_database_schema(project["database_url"])

        creature = {
            "name": project["name"],
            "type": "application",
            "platform": "supabase",
            "metadata": {
                "region": project["region"],
                "plan": project["plan"],
                "tables": len(tables),
                "data_classification": classify_tables(tables),  # AI-powered
                "has_auth": project["settings"]["auth_enabled"],
                "backup_policy": project["backup_enabled"]
            },
            "controls": ["CM-8", "SC-28", "AC-3", "CP-9"],
            "risks": detect_data_risks(tables)
        }

        create_creature(creature)
```

## Continuous Monitoring

CreatureGRC runs daily scans to detect:
- **New projects** created by developers
- **Configuration changes** (SSL/TLS downgrades, firewall rule changes)
- **New secrets** added to environment variables
- **Data growth** in databases (PII classification)
- **Cost increases** (spending alerts)

Alerts are sent via:
- Slack/Teams notifications
- Email reports
- Jira tickets (auto-created for high-risk findings)

## Compliance Mapping

Cloud services map to these common controls:

| Service | NIST 800-53 | SOC 2 | ISO 27001 |
|---------|-------------|-------|-----------|
| **All Cloud** | CM-8 (Inventory), SA-9 (Third-Party) | CC9.1, CC9.2 | A.15.1.1 |
| **Vercel** | CM-3 (Change Mgmt), SC-13 (Crypto) | CC8.1, CC6.6 | A.14.2.2 |
| **Supabase/Neon** | SC-28 (Data at Rest), AC-3 (Access) | CC6.1, CC6.7 | A.9.1.1, A.10.1.1 |
| **GitHub** | CM-3, SA-10 (Dev Config), AU-2 (Audit) | CC8.1, CC7.2 | A.14.2.2 |
| **Cloudflare** | SC-7 (Boundary), SC-8 (Transmission) | CC6.6, CC6.7 | A.13.1.1 |

## Best Practices

1. **Enable SSO** for all cloud platforms (Keycloak, Google Workspace)
2. **Use API tokens** with read-only scope for CreatureGRC
3. **Schedule daily scans** during off-hours (2am)
4. **Review weekly reports** for new shadow IT
5. **Automate remediation** (create Jira tickets for policy violations)
6. **Train developers** on proper cloud service request process

## Roadmap

- [ ] AWS account discovery (EC2, S3, RDS, Lambda)
- [ ] Azure resource discovery (VMs, Storage, Cosmos DB)
- [ ] GCP project discovery (Compute, Cloud SQL)
- [ ] Railway deployment tracking
- [ ] Fly.io app discovery
- [ ] Render service tracking
- [ ] Netlify site tracking
- [ ] Cost tracking integration (show spend per Creature)
- [ ] Auto-remediation (revoke unauthorized projects)
