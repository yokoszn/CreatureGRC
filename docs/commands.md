# CreatureGRC Command Reference

Complete guide to all CreatureGRC CLI commands for compliance automation and infrastructure mapping.

---

## Quick Start Commands

### 01 - Initialize
**Set up your compliance framework and project**

```bash
$ creaturegrc import-controls --framework nist-800-53
$ creaturegrc frameworks list
```

Initialize your CreatureGRC instance by importing security control frameworks. This creates the foundational compliance library that all other operations will reference.

**Options:**
- `--framework`: Framework to import (`nist-800-53`, `scf`, `ccm`)
- `--file`: File path (required for SCF/CCM Excel imports)

**Examples:**
```bash
# Import NIST 800-53 controls (1,084 controls)
$ creaturegrc import-controls --framework nist-800-53

# Import ComplianceForge SCF (212 controls with 137+ framework mappings)
$ creaturegrc import-controls --framework scf --file ./data/SCF-2024.1.xlsx

# Import CSA Cloud Controls Matrix (197 controls)
$ creaturegrc import-controls --framework ccm
```

**What it does:**
- Downloads control frameworks from official sources (NIST OSCAL, ComplianceForge, CSA)
- Parses controls, domains, and implementation guidance
- Loads controls into PostgreSQL database
- Creates cross-framework mappings (e.g., NIST AC-2 → SOC 2 CC6.1)

---

### 02 - Scan
**Discover creatures across your infrastructure**

```bash
$ creaturegrc creatures sync --source netbox
```

Automatically discover and import infrastructure assets, identities, accounts, and applications from integrated systems into CreatureGRC's creature database.

**Options:**
- `--source`: Source system to sync from
  - `netbox`: Infrastructure inventory and IPAM
  - `yaml`: Custom YAML file (use with `--file`)
  - `keycloak`: SSO users and roles
  - `freeipa`: LDAP users and groups
  - `wazuh`: Security agents and monitored systems
  - `github`: Repositories, users, deploy keys
  - `aws`: EC2, IAM, S3 resources
  - `vercel`: Projects and deployments
  - `supabase`: Database instances
- `--file`: YAML file path (when `--source=yaml`)

**Examples:**
```bash
# Sync infrastructure from Netbox (servers, VMs, network devices)
$ creaturegrc creatures sync --source netbox

# Sync identities from Keycloak SSO
$ creaturegrc creatures sync --source keycloak

# Sync LDAP users and groups from FreeIPA
$ creaturegrc creatures sync --source freeipa

# Sync from custom YAML file
$ creaturegrc creatures sync --source yaml --file ./infrastructure.yaml

# Discover cloud/SaaS resources (shadow IT)
$ creaturegrc creatures sync --source vercel
$ creaturegrc creatures sync --source supabase
$ creaturegrc creatures sync --source github
```

**What it does:**
- Connects to source systems via REST APIs
- Discovers infrastructure, identities, accounts, applications
- Normalizes data into creature taxonomy (4 types: Infrastructure, Identities, Accounts, Applications)
- Imports metadata (IP addresses, roles, criticality, relationships)
- Identifies shadow IT and unapproved cloud resources

**Discovered creature types:**
- **Infrastructure**: Servers, VMs, containers (LXC, Docker), Kubernetes clusters, network devices, storage
- **Identities**: Staff members, contractors, AI agents, service accounts, external vendors
- **Accounts**: User accounts in each system (SSO, LDAP, cloud IAM, SSH keys, API tokens)
- **Applications**: SaaS apps, internal services, databases, CI/CD pipelines

---

### 03 - Map
**Connect creatures to security controls**

```bash
$ creaturegrc controls map-creatures --framework soc2
```

Map discovered creatures to compliance controls, creating an auditable relationship graph between your infrastructure, identities, and security requirements.

**Options:**
- `--framework`: Framework to map against (e.g., `soc2`, `nist`, `iso27001`, `pci-dss`)
- `--control`: Map to specific control (e.g., `AC-2`, `CC6.1`)
- `--creature`: Map specific creature by name or ID
- `--auto`: Automatically map based on heuristics and metadata

**Examples:**
```bash
# Map all creatures to SOC 2 controls
$ creaturegrc controls map-creatures --framework soc2

# Map creatures to specific NIST control
$ creaturegrc controls map-creatures --framework nist --control AC-2

# Map specific infrastructure to controls
$ creaturegrc controls map-creatures --creature prod-web-01

# Automatically map based on creature metadata and roles
$ creaturegrc controls map-creatures --framework soc2 --auto
```

**What it does:**
- Analyzes creature metadata (roles, criticality, data classification, access patterns)
- Maps creatures to relevant security controls
- Creates relationship graph: Identity → Account → Infrastructure → Data → Control
- Identifies gaps where creatures lack control coverage
- Generates mapping justifications for auditors

**Example mapping:**
```
Creature: jane.doe (Identity - Person)
├─ Account: jane.doe@keycloak → Control: NIST AC-3, SOC 2 CC6.1
├─ Account: jane.doe@aws → Control: NIST AC-6, SOC 2 CC6.2
├─ Infrastructure: prod-db-01 → Control: NIST AC-2, AU-2, SOC 2 CC7.2
└─ Data: customer-pii → Control: HIPAA §164.308(a)(4), GDPR Art. 32
```

---

### 04 - Audit
**Generate compliance audit packages**

```bash
$ creaturegrc audit generate --framework soc2 --output ./audit-package-2024-q4/
```

Export comprehensive audit packages for auditors including control matrices, evidence bundles, infrastructure maps, and gap analysis reports.

**Options:**
- `--framework`: Framework to audit (`soc2`, `iso27001`, `nist`, `pci-dss`, `hipaa`)
- `--output`: Output directory for audit package files
- `--period`: Evidence collection period (e.g., `90-days`, `2024-q4`, `2024-01-01:2024-12-31`)
- `--format`: Output format (`pdf`, `excel`, `zip`, `all`) (default: `all`)
- `--include-evidence`: Include raw evidence files in bundle (default: true)

**Examples:**
```bash
# Generate SOC 2 Type II audit package (last 90 days)
$ creaturegrc audit generate --framework soc2 --output ./soc2-audit-2024-q4/

# Generate ISO 27001 audit package with specific date range
$ creaturegrc audit generate --framework iso27001 \
  --period 2024-01-01:2024-12-31 \
  --output ./iso27001-annual-audit/

# Generate PCI-DSS audit (Excel and PDF only, no raw evidence)
$ creaturegrc audit generate --framework pci-dss \
  --format excel,pdf \
  --include-evidence=false \
  --output ./pci-audit/

# Generate HIPAA compliance audit
$ creaturegrc audit generate --framework hipaa --output ./hipaa-audit/
```

**Generated files:**
- **control-matrix.xlsx**: Spreadsheet mapping controls to evidence and implementation status
- **evidence-bundle.zip**: All collected evidence files (logs, configs, screenshots, policies)
- **infrastructure-map.pdf**: Visual diagram of creatures and their control relationships
- **gap-analysis.pdf**: Missing controls, weak areas, remediation recommendations
- **risk-register.xlsx**: Identified risks, likelihood, impact, mitigation status
- **audit-summary.pdf**: Executive summary with compliance percentages and key findings

**What it does:**
- Queries database for all controls, creatures, and evidence for specified framework
- Calculates compliance percentages and implementation status
- Generates cross-referenced documentation linking evidence to controls
- Exports infrastructure relationship graphs
- Identifies and reports gaps in control coverage
- Creates auditor-ready package with timestamped snapshots

---

## Core Commands

### Creature Management

#### `creatures list`
**List all discovered creatures**

```bash
$ creaturegrc creatures list
```

Display all creatures (infrastructure, identities, accounts, applications) tracked in your environment.

**Options:**
- `--type`: Filter by creature type (`identity`, `account`, `infrastructure`, `application`)
- `--class`: Filter by creature class (e.g., `server`, `vm`, `container`, `person`, `ai-agent`)
- `--criticality`: Filter by criticality level (`critical`, `high`, `medium`, `low`)
- `--controls`: Show mapped controls count
- `--format`: Output format (`table`, `json`, `csv`) (default: `table`)

**Examples:**
```bash
# List all creatures
$ creaturegrc creatures list

# List only identities (people and AI agents)
$ creaturegrc creatures list --type identity

# List critical infrastructure
$ creaturegrc creatures list --type infrastructure --criticality critical

# List AI agents and service accounts
$ creaturegrc creatures list --class ai-agent

# Export to JSON
$ creaturegrc creatures list --format json > creatures.json
```

#### `creatures show <name>`
**Show detailed creature information**

```bash
$ creaturegrc creatures show jane.doe
```

Display detailed information about a specific creature including accounts, infrastructure access, and mapped controls.

**Examples:**
```bash
# View person's details
$ creaturegrc creatures show jane.doe

# View infrastructure details
$ creaturegrc creatures show prod-web-01

# View AI agent details
$ creaturegrc creatures show github-actions-bot
```

---

### Control Management

#### `controls list`
**List compliance controls**

```bash
$ creaturegrc controls list
```

Display available security controls from imported frameworks.

**Options:**
- `--framework`: Filter by framework (`nist`, `soc2`, `iso27001`, `pci-dss`, `hipaa`)
- `--domain`: Filter by control domain (e.g., `AC`, `AU`, `SC`, `SI`)
- `--implemented`: Filter by implementation status (`true`, `false`)
- `--format`: Output format (`table`, `json`, `csv`)

**Examples:**
```bash
# List all controls
$ creaturegrc controls list

# List NIST 800-53 controls
$ creaturegrc controls list --framework nist

# List Access Control (AC) domain controls
$ creaturegrc controls list --domain AC

# List implemented SOC 2 controls
$ creaturegrc controls list --framework soc2 --implemented true
```

#### `controls show <control-code>`
**Show control details**

```bash
$ creaturegrc controls show AC-2
```

Display detailed information about a specific control including description, testing procedures, and implementation guidance.

**Examples:**
```bash
# View NIST AC-2 (Account Management)
$ creaturegrc controls show AC-2

# View SOC 2 CC6.1 (Logical Access Controls)
$ creaturegrc controls show CC6.1

# View ISO 27001 A.9.2.1
$ creaturegrc controls show A.9.2.1
```

#### `controls status`
**Show compliance status for framework**

```bash
$ creaturegrc controls status --framework soc2
```

Display implementation and evidence collection status for all controls in a framework.

**Options:**
- `--framework`: Framework to check (`soc2`, `nist`, `iso27001`, `pci-dss`, `hipaa`)
- `--summary`: Show summary only (default: false)

**Examples:**
```bash
# SOC 2 compliance status
$ creaturegrc controls status --framework soc2

# NIST 800-53 detailed status
$ creaturegrc controls status --framework nist

# ISO 27001 summary
$ creaturegrc controls status --framework iso27001 --summary
```

---

### Framework Management

#### `frameworks list`
**List available compliance frameworks**

```bash
$ creaturegrc frameworks list
```

Display all imported compliance frameworks with version numbers and control counts.

**Examples:**
```bash
# List frameworks
$ creaturegrc frameworks list
```

**Example output:**
```
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

---

### Evidence Collection

#### `collect evidence`
**Collect compliance evidence from integrated systems**

```bash
$ creaturegrc collect evidence --source wazuh --days 30
```

Automatically collect security events, logs, and artifacts from infrastructure tools for compliance evidence.

**Options:**
- `--source`: Source system to collect from
  - `wazuh`: Security alerts, vulnerability scans, FIM events
  - `keycloak`: Authentication logs, user sessions, access grants
  - `freeipa`: LDAP lifecycle events, group membership changes
  - `netbox`: Configuration changes, device role modifications
  - `infisical`: Secret access audit trail, rotation logs
  - `github`: Repository audits, deploy key usage, commit signatures
  - `jira`: Change tickets, incident management records
  - `confluence`: Policy documents, SOPs, runbooks
  - `all`: Collect from all configured sources
- `--days`: Number of days to collect (default: 90)
- `--framework`: Framework context for targeted evidence collection (e.g., `soc2`)
- `--control`: Collect evidence for specific control (e.g., `AC-2`)

**Examples:**
```bash
# Collect Wazuh security events (last 30 days)
$ creaturegrc collect evidence --source wazuh --days 30

# Collect Keycloak authentication logs (last 90 days)
$ creaturegrc collect evidence --source keycloak --days 90

# Collect from all sources
$ creaturegrc collect evidence --source all --days 90

# Collect SOC 2-specific evidence
$ creaturegrc collect evidence --framework soc2 --days 90

# Collect evidence for specific control
$ creaturegrc collect evidence --control AC-2 --days 30
```

**What it collects:**

**Security (Wazuh):**
- Vulnerability scan results
- Security alerts and incidents
- File integrity monitoring (FIM) events
- Compliance check results
- Intrusion detection alerts

**Identity & Access (Keycloak, FreeIPA):**
- User authentication events (success/failure)
- SSO session creation/termination
- Role and permission changes
- MFA enrollment and usage
- Password policy compliance

**Infrastructure (Netbox):**
- Asset inventory changes
- IP address allocations
- Device configuration modifications
- Network topology changes

**Secrets (Infisical, Vaultwarden):**
- Secret access audit logs
- Credential rotation events
- Vault policy changes

**Code & CI/CD (GitHub, OneDev):**
- Code review records
- Branch protection enforcement
- CI/CD pipeline execution logs
- Commit signing verification

**Documentation (Jira, Confluence):**
- Security policies and procedures
- Change management tickets
- Incident response records
- Architectural decision records (ADRs)

---

### Status & Reporting

#### `status`
**Show overall compliance status**

```bash
$ creaturegrc status --framework soc2
```

Display high-level compliance dashboard with implementation percentages, evidence coverage, and automation status.

**Options:**
- `--framework`: Framework to check (default: `soc2`)
- `--detailed`: Show detailed breakdown by control domain

**Examples:**
```bash
# SOC 2 compliance dashboard
$ creaturegrc status --framework soc2

# Detailed NIST 800-53 status
$ creaturegrc status --framework nist --detailed
```

**Example output:**
```
Compliance Status Dashboard - SOC 2

Total Controls: 64
Implemented: 58 (90.6%)
Not Implemented: 6 (9.4%)
With Evidence: 52 (81.3%)
Automated: 48 (75.0%)

Gaps:
- CC7.3: System Operations - No backup verification
- CC6.7: Access Removal - Offboarding not documented
```

---

## Advanced Commands

### AI-Powered Analysis

#### `analyze gaps`
**AI-powered gap analysis**

```bash
$ creaturegrc analyze gaps --framework soc2 --use-ai
```

Use AI to identify missing controls, weak implementations, and provide remediation recommendations.

**Options:**
- `--framework`: Framework to analyze
- `--use-ai`: Enable AI analysis (requires AI Foundry deployment)
- `--model`: LLM model to use (`claude-3-5-sonnet`, `gpt-4`, `gemini-pro`)
- `--output`: Save analysis report to file

**Examples:**
```bash
# AI gap analysis for SOC 2
$ creaturegrc analyze gaps --framework soc2 --use-ai

# Save analysis to file
$ creaturegrc analyze gaps --framework iso27001 --use-ai --output gaps-report.pdf
```

#### `questionnaire generate`
**Generate AI questionnaires for controls**

```bash
$ creaturegrc questionnaire generate --control AC-2 --use-ai
```

Generate intelligent questionnaires for control implementation assessment using LLMs.

**Options:**
- `--control`: Control to generate questionnaire for
- `--framework`: Framework context
- `--use-ai`: Enable AI generation
- `--send-to`: Email address to send questionnaire

**Examples:**
```bash
# Generate questionnaire for NIST AC-2
$ creaturegrc questionnaire generate --control AC-2 --use-ai

# Send to stakeholder
$ creaturegrc questionnaire generate --control CC6.1 --use-ai \
  --send-to security-team@example.com
```

#### `evidence extract`
**Extract evidence from unstructured documents**

```bash
$ creaturegrc evidence extract --file security-policy.pdf --use-ai
```

Use AI to parse unstructured documents (PDFs, Word docs) and extract compliance evidence.

**Options:**
- `--file`: Document to analyze
- `--use-ai`: Enable AI extraction
- `--framework`: Framework to map evidence to
- `--auto-import`: Automatically import extracted evidence

**Examples:**
```bash
# Extract evidence from policy document
$ creaturegrc evidence extract --file security-policy.pdf --use-ai

# Map to specific framework
$ creaturegrc evidence extract --file incident-response-plan.docx \
  --use-ai --framework soc2 --auto-import
```

---

## Workflow Commands

### Scheduling & Automation

#### `schedule enable`
**Enable scheduled evidence collection**

```bash
$ creaturegrc schedule enable --source wazuh --frequency daily
```

Set up recurring evidence collection workflows using Temporal.

**Options:**
- `--source`: Source system to schedule
- `--frequency`: Collection frequency (`hourly`, `daily`, `weekly`, `monthly`)
- `--time`: Specific time to run (e.g., `02:00`)
- `--framework`: Framework context for targeted collection

**Examples:**
```bash
# Daily Wazuh evidence collection at 2 AM
$ creaturegrc schedule enable --source wazuh --frequency daily --time 02:00

# Weekly full compliance scan
$ creaturegrc schedule enable --source all --frequency weekly --time Sunday:00:00
```

#### `schedule list`
**List active scheduled workflows**

```bash
$ creaturegrc schedule list
```

#### `schedule disable`
**Disable scheduled workflow**

```bash
$ creaturegrc schedule disable --id <workflow-id>
```

---

## Configuration

### Environment Variables

CreatureGRC reads configuration from environment variables (`.env` file):

```bash
# Database
GRC_DB_HOST=localhost
GRC_DB_PORT=5432
GRC_DB_NAME=grc_platform
GRC_DB_USER=grc_user
GRC_DB_PASSWORD=your-password

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

# Code & CI/CD
GITHUB_API_URL=https://api.github.com
GITHUB_TOKEN=ghp_your-token

# Documentation (MCP)
JIRA_URL=https://your-company.atlassian.net
JIRA_USER=your-email@example.com
JIRA_API_TOKEN=your-jira-api-token

CONFLUENCE_URL=https://your-company.atlassian.net/wiki
CONFLUENCE_USER=your-email@example.com
CONFLUENCE_API_TOKEN=your-confluence-api-token

# Cloud/SaaS
VERCEL_API_TOKEN=your-vercel-token
SUPABASE_ACCESS_TOKEN=your-supabase-token
```

See [config/.env.minimal.example](../config/.env.minimal.example) for complete configuration template.

---

## Command Cheat Sheet

### Quick Reference

```bash
# Initial Setup
creaturegrc import-controls --framework nist-800-53
creaturegrc frameworks list

# Discovery
creaturegrc creatures sync --source netbox
creaturegrc creatures sync --source keycloak
creaturegrc creatures list

# Mapping
creaturegrc controls map-creatures --framework soc2 --auto
creaturegrc controls list --framework soc2

# Evidence
creaturegrc collect evidence --source wazuh --days 30
creaturegrc collect evidence --source keycloak --days 90

# Audit
creaturegrc audit generate --framework soc2 --output ./audit-package/

# Status
creaturegrc status --framework soc2
creaturegrc controls status --framework nist
```

---

## Next Steps

- **[Quick Start Guide](quickstart.md)** - Get running in 5 minutes
- **[Deployment Guide](deployment.md)** - Production deployment patterns
- **[API Integration Guide](api-integration.md)** - Connect your infrastructure tools
- **[Control Mapping Guide](control-mapping.md)** - Map infrastructure to controls
- **[Evidence Collection Guide](evidence-collection.md)** - Automate compliance evidence

---

**Built for teams who need compliance without compromise.**
