# Jira & Confluence Integration

CreatureGRC integrates with Atlassian Jira and Confluence to discover policies, processes, and documentation, and automatically create compliance-related tickets.

## What It Does

### Confluence Integration
**Scan and extract compliance documentation:**
- **Policies & Procedures**: Automatically discover security policies, SOPs, runbooks
- **Controls Documentation**: Map documented policies to NIST/SOC 2/ISO controls
- **Architectural Decision Records (ADRs)**: Track design decisions and their compliance implications
- **Change Records**: Extract change management documentation
- **AI-Powered Extraction**: Use LLMs to parse unstructured policy documents and extract control implementations

**Example: Policy Discovery**
```
Confluence Space: Security Policies
├─ Page: "Access Control Policy" (Created: 2024-01-15, Last Modified: 2024-09-20)
│   ├─ AI Extraction: Maps to NIST AC-2, AC-3, AC-6
│   ├─ AI Extraction: Maps to SOC 2 CC6.1, CC6.2
│   ├─ Evidence: Policy approved by CISO on 2024-01-20
│   └─ Compliance Gap: Policy review date passed (90-day review cycle)
│
├─ Page: "Incident Response Plan" (Created: 2023-11-01, Last Modified: 2024-10-15)
│   ├─ AI Extraction: Maps to NIST IR-1, IR-4, IR-5, IR-6
│   ├─ AI Extraction: Maps to SOC 2 CC7.3, CC7.4
│   └─ Evidence: Tabletop exercise conducted 2024-09-01
│
└─ Page: "Password Policy" (Created: 2023-06-01, Last Modified: 2023-06-01)
    ├─ AI Extraction: Maps to NIST IA-5, IA-5(1)
    ├─ Evidence: Policy document exists
    └─ Risk: Policy not updated in 16 months (recommend annual review)
```

### Jira Integration
**Automated ticket management:**
- **Change Tickets**: Collect evidence of change management process
- **Incident Tickets**: Security incidents as compliance evidence
- **Risk Tickets**: Track risk register items
- **Remediation Tickets**: Auto-create tickets for compliance gaps
- **JQL Queries**: Custom evidence collection (e.g., "All security incidents in Q4 2024")

**Example: Automated Ticket Creation**
```bash
$ creaturegrc audit generate --framework soc2

Gap Analysis: 12 controls not fully satisfied
Creating Jira tickets for remediation...

✓ Created: SEC-1247 "Implement automated backup verification (CC7.3)"
  Priority: High
  Assignee: DevOps Team
  Due Date: 2024-11-30
  Labels: compliance, soc2, cc7.3
  Linked Evidence: Backup policy document (Confluence)

✓ Created: SEC-1248 "Document offboarding process (CC6.7)"
  Priority: Medium
  Assignee: Security Team
  Due Date: 2024-11-15
  Labels: compliance, soc2, cc6.7
```

## Configuration

### Prerequisites

**Jira Cloud:**
- Jira Cloud instance URL
- Email address
- API token (create at: https://id.atlassian.com/manage-profile/security/api-tokens)

**Confluence Cloud:**
- Confluence Cloud URL (usually same as Jira)
- Same API token works for both Jira and Confluence

**Permissions Required:**
- **Jira**: Browse projects, create issues, edit issues, view issue comments
- **Confluence**: View pages, view comments

### Environment Variables

Add to `.env`:

```bash
# Atlassian Jira/Confluence
JIRA_URL=https://yourorg.atlassian.net
JIRA_EMAIL=grc@example.com
JIRA_API_TOKEN=ATATT3xFfGF0...  # Create at id.atlassian.com

# Jira Project Configuration
JIRA_GRC_PROJECT_KEY=SEC  # Project where compliance tickets are created
JIRA_GRC_ISSUE_TYPE=Task  # Or "Story", "Epic", etc.
JIRA_GRC_ASSIGNEE=  # Default assignee (leave blank for unassigned)

# Confluence Configuration
CONFLUENCE_URL=${JIRA_URL}/wiki  # Usually /wiki suffix
CONFLUENCE_SPACES=SEC,ENG,OPS  # Comma-separated list of spaces to scan
CONFLUENCE_LABELS=policy,security,compliance,sop  # Filter pages by labels
```

## Usage

### Discover Policies from Confluence

```bash
# Scan all configured Confluence spaces
$ creaturegrc discover policies --source confluence

Scanning Confluence spaces: SEC, ENG, OPS...

✓ Security Policies (SEC) - 24 pages found
  ├─ Access Control Policy (5,234 words) → NIST AC-2, AC-3, AC-6
  ├─ Incident Response Plan (3,891 words) → NIST IR-1, IR-4, IR-5, IR-6
  ├─ Password Policy (1,452 words) → NIST IA-5, IA-5(1)
  └─ ... (21 more policies)

✓ Engineering Runbooks (ENG) - 47 pages found
  ├─ Database Backup Procedure → CP-9 (Backup)
  ├─ Server Hardening Guide → CM-6 (Configuration Settings)
  └─ ... (45 more runbooks)

✓ Operations SOPs (OPS) - 15 pages found
  ├─ On-Call Rotation SOP → CP-2 (Contingency Plan)
  └─ ... (14 more SOPs)

Total: 86 policy/procedure documents discovered
Mapped to 127 controls across 12 frameworks
```

### Scan Specific Policy

```bash
$ creaturegrc policies show "Access Control Policy"

Policy: Access Control Policy
Source: Confluence (SEC space)
URL: https://yourorg.atlassian.net/wiki/spaces/SEC/pages/123456
Created: 2024-01-15 by jane.doe
Last Modified: 2024-09-20 by john.smith
Word Count: 5,234
Labels: policy, security, access-control, soc2

AI-Extracted Controls:
├─ NIST AC-2 (Account Management)
│   └─ Excerpt: "All user accounts must be approved by department manager..."
│
├─ NIST AC-3 (Access Enforcement)
│   └─ Excerpt: "Role-based access control (RBAC) shall be implemented..."
│
├─ NIST AC-6 (Least Privilege)
│   └─ Excerpt: "Users are granted minimum necessary privileges..."
│
├─ SOC 2 CC6.1 (Logical Access Controls)
│   └─ Maps from: NIST AC-2, AC-3
│
└─ ISO 27001 A.9.2.1 (User Registration)
    └─ Maps from: NIST AC-2

Compliance Status:
✓ Policy document exists and is current
✓ Policy reviewed within last 90 days (last review: 2024-09-20)
✗ Policy lacks formal approval signature (recommend digital signature)
✗ Policy missing review schedule (recommend annual review)

Evidence Collection:
✓ Policy text extracted and stored
✓ Control mappings recorded
✓ Last modified date tracked for freshness checks
```

### Query Jira Tickets for Evidence

```bash
# Collect change management evidence
$ creaturegrc collect evidence --source jira --jql "project = ENG AND type = 'Change Request' AND created >= -90d"

Collecting Jira evidence...
JQL: project = ENG AND type = 'Change Request' AND created >= -90d

✓ Found 34 change tickets (last 90 days)
  ├─ ENG-1234: Deploy v2.3.0 to production (Completed)
  ├─ ENG-1235: Update SSL certificates (Completed)
  ├─ ENG-1236: Patch critical vulnerability CVE-2024-1234 (Completed)
  └─ ... (31 more tickets)

Evidence mapped to controls:
├─ CM-3 (Configuration Change Control): 34 tickets
├─ CM-4 (Security Impact Analysis): 12 tickets (change requests with security review)
└─ SA-11 (Developer Security Testing): 8 tickets (changes with security testing evidence)

Evidence stored and ready for audit package generation.

# Collect incident management evidence
$ creaturegrc collect evidence --source jira --jql "project = SEC AND type = Incident AND priority in (High, Critical) AND created >= -180d"

Collecting Jira evidence...
JQL: project = SEC AND type = Incident AND priority in (High, Critical) AND created >= -180d

✓ Found 7 high/critical security incidents (last 180 days)
  ├─ SEC-891: Unauthorized access attempt detected (Resolved)
  ├─ SEC-894: Phishing email campaign (Resolved)
  ├─ SEC-897: Ransomware blocked by EDR (Resolved)
  └─ ... (4 more incidents)

Evidence mapped to controls:
├─ IR-4 (Incident Handling): 7 tickets
├─ IR-5 (Incident Monitoring): 7 tickets
├─ IR-6 (Incident Reporting): 7 tickets
└─ SI-4 (Information System Monitoring): 7 tickets

Incident Response Metrics:
├─ Mean Time to Detect (MTTD): 4.2 hours
├─ Mean Time to Respond (MTTR): 2.1 hours
└─ All incidents resolved within SLA (24 hours)
```

### Auto-Create Remediation Tickets

```bash
# Generate audit and create Jira tickets for gaps
$ creaturegrc audit generate --framework soc2 --create-tickets

Generating SOC 2 Type II audit package...

Gap Analysis: 5 controls not fully satisfied

Creating Jira remediation tickets...

✓ Created SEC-1247: "Implement automated backup verification"
  Control: CC7.3 (System Operations)
  Gap: No automated verification of backup restoration
  Recommendation: Implement monthly automated restore tests
  Priority: High
  Due Date: 2024-11-30
  Assignee: devops-team
  Labels: compliance, soc2, cc7.3, backup
  Description:
    Gap identified during SOC 2 audit preparation:

    Control CC7.3 (System Operations) requires automated backup verification.

    Current State:
    - Backups run nightly via Proxmox Backup Server
    - Manual restore testing performed quarterly
    - No automated verification

    Required Actions:
    1. Implement automated restore test scripts
    2. Schedule monthly automated restore tests
    3. Configure alerts for failed tests
    4. Document restore test procedures

    References:
    - SOC 2 CC7.3 requirements
    - Backup Policy: https://yourorg.atlassian.net/wiki/spaces/SEC/pages/789
    - Current backup evidence: Proxmox Backup Server logs

✓ Created SEC-1248: "Document formal offboarding process"
  Control: CC6.7 (Access Removal)
  Gap: Offboarding process not formally documented
  Recommendation: Create Confluence SOP for employee offboarding
  Priority: Medium
  Due Date: 2024-11-15
  Assignee: hr-team
  Labels: compliance, soc2, cc6.7, access-control
  Description:
    Gap identified during SOC 2 audit preparation:

    Control CC6.7 (Access Removal) requires formal offboarding procedures.

    Current State:
    - Ad-hoc offboarding via manager notifications
    - No centralized checklist
    - Inconsistent access revocation

    Required Actions:
    1. Document offboarding SOP in Confluence
    2. Create offboarding checklist (FreeIPA, Keycloak, GitHub, AWS, etc.)
    3. Define timeline (access revoked on last day, accounts disabled immediately)
    4. Assign ownership (HR initiates, IT executes, managers verify)

    References:
    - SOC 2 CC6.7 requirements
    - Current FreeIPA/Keycloak procedures (informal)

... (3 more tickets created)

All remediation tickets created: https://yourorg.atlassian.net/issues/?jql=labels%3Dcompliance

Audit package includes:
✓ Gap analysis report (PDF)
✓ Remediation tracker (Excel with Jira ticket links)
✓ Evidence bundle (ZIP)
```

## AI-Powered Policy Extraction

CreatureGRC uses LLMs to extract compliance evidence from unstructured Confluence documentation.

**How it works:**

1. **Fetch Confluence page** → Get page content via API
2. **Send to LLM** → "Extract security controls from this policy document"
3. **Parse response** → LLM identifies NIST controls with supporting excerpts
4. **Store mappings** → Link Confluence page → Control → Framework

**Example LLM prompt:**

```
You are a compliance auditor reviewing a security policy document.

Extract all security controls that this policy implements. For each control:
1. Identify the NIST 800-53 Rev 5 control ID (e.g., AC-2, CM-3)
2. Quote the specific excerpt from the document that implements the control
3. Rate the implementation strength (Full, Partial, Minimal)

Document:
---
[Confluence page content here]
---

Respond in JSON format.
```

**Example LLM response:**

```json
{
  "controls": [
    {
      "framework": "NIST 800-53 Rev 5",
      "control_id": "AC-2",
      "control_name": "Account Management",
      "excerpt": "All user accounts must be approved by department manager and provisioned through FreeIPA",
      "implementation_strength": "Full"
    },
    {
      "framework": "NIST 800-53 Rev 5",
      "control_id": "AC-6",
      "control_name": "Least Privilege",
      "excerpt": "Users are granted minimum necessary privileges based on job function",
      "implementation_strength": "Partial",
      "gap": "No formal role definition or privilege escalation process documented"
    }
  ]
}
```

## CLI Commands

### Confluence

```bash
# Discover all policies
creaturegrc discover policies --source confluence

# Discover from specific space
creaturegrc discover policies --source confluence --space SEC

# Discover with specific labels
creaturegrc discover policies --source confluence --labels policy,security

# Show specific policy
creaturegrc policies show "Access Control Policy"

# List all discovered policies
creaturegrc policies list

# Refresh policy (re-scan for changes)
creaturegrc policies refresh "Access Control Policy"

# Detect policy staleness
creaturegrc policies audit --check-freshness --max-age 90
```

### Jira

```bash
# Collect change management evidence
creaturegrc collect evidence --source jira \
  --jql "project = ENG AND type = 'Change Request' AND created >= -90d"

# Collect incident evidence
creaturegrc collect evidence --source jira \
  --jql "project = SEC AND type = Incident AND created >= -180d"

# Create remediation tickets from gaps
creaturegrc audit generate --framework soc2 --create-tickets

# Create custom ticket
creaturegrc tickets create \
  --project SEC \
  --type Task \
  --summary "Review access control policy" \
  --description "Annual policy review required" \
  --assignee jane.doe \
  --priority Medium \
  --labels compliance,policy-review

# Link Creature to Jira ticket
creaturegrc creatures link prod-db-01 --ticket SEC-1234
```

## MCP Integration (Future)

CreatureGRC will support Model Context Protocol (MCP) for enhanced Confluence/Jira integration:

```bash
# Use MCP server for Confluence
creaturegrc mcp use confluence-server

# AI can now query Confluence directly
creaturegrc chat "What does our password policy say about complexity requirements?"

Response (via MCP → Confluence):
According to the Password Policy (https://yourorg.atlassian.net/wiki/spaces/SEC/pages/456):

"Passwords must meet the following complexity requirements:
- Minimum 12 characters
- At least 1 uppercase letter
- At least 1 number
- At least 1 special character
- Cannot contain username
- Cannot reuse last 5 passwords"

This implements NIST IA-5(1)(a) password complexity requirements.
```

## Compliance Mappings

Jira/Confluence evidence maps to these controls:

| Evidence Type | NIST 800-53 | SOC 2 | ISO 27001 |
|---------------|-------------|-------|-----------|
| **Policies (Confluence)** | PL-1, PL-2 (Planning) | All TSC | A.5 (Policies) |
| **Change Tickets (Jira)** | CM-3, CM-4 | CC8.1 | A.14.2.2 |
| **Incident Tickets (Jira)** | IR-4, IR-5, IR-6 | CC7.3, CC7.4 | A.16.1.4, A.16.1.5 |
| **Risk Tickets (Jira)** | RA-1, RA-3 | CC4.1, CC4.2 | A.6.1.2 |
| **SOPs (Confluence)** | All procedural controls | CC1.2 | A.5, A.6 |

## Best Practices

1. **Structure Confluence Spaces** by compliance domain:
   - Space: `SEC` → Security policies
   - Space: `ENG` → Engineering procedures
   - Space: `OPS` → Operational runbooks

2. **Use Confluence Labels** consistently:
   - `policy` → Formal policies requiring annual review
   - `sop` → Standard operating procedures
   - `runbook` → Technical runbooks
   - `soc2`, `iso27001`, `hipaa` → Framework-specific docs

3. **Jira Project Structure**:
   - Project: `SEC` → Security incidents and compliance tasks
   - Project: `ENG` → Change requests and engineering work
   - Issue types: Incident, Change Request, Risk, Compliance Task

4. **Review Schedules**:
   - Policies: Review annually, update metadata in Confluence
   - SOPs: Review quarterly
   - Runbooks: Review on each major system change

5. **Ticket Templates**:
   - Create Jira templates for compliance tickets
   - Include required fields: Control ID, Framework, Gap Description

## Roadmap

- [ ] MCP server integration for real-time AI queries
- [ ] Confluence page templates for compliance policies
- [ ] Jira automation rules (auto-label compliance tickets)
- [ ] Bidirectional sync (update Confluence when controls change)
- [ ] Policy version control (track changes via Confluence API)
- [ ] Auto-detect policy review dates and create reminder tickets
- [ ] Integration with Confluence Questionnaires for control testing
