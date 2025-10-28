# CreatureGRC Architecture: ServiceNow AI Control Tower Parity

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    CREATURE DATABASE (Foundation)                │
│  • Infrastructure tracking (servers, apps, networks, vendors)   │
│  • Dependency graphs                                             │
│  • Risk surfaces                                                 │
│  • Sovereignty tracking                                          │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    GRC EXTENSION LAYER                           │
│  • Control-to-Creature mapping                                  │
│  • Compliance frameworks (OSCAL, SCF, CCM)                      │
│  • Evidence automation                                           │
└────────────────┬────────────────────────────────────────────────┘
                 │
    ┌────────────┴────────────┐
    ▼                         ▼
┌──────────────┐    ┌──────────────────┐
│   LiteLLM    │    │  Temporal.io     │
│ Multi-LLM    │    │  Workflow        │
│ Gateway      │    │  Orchestration   │
└──────┬───────┘    └────────┬─────────┘
       │                     │
       │         ┌───────────┴──────────┐
       │         ▼                      ▼
       │   ┌──────────┐          ┌──────────┐
       └──→│   Obot   │          │ Evidence │
           │ Workflow │          │ Workers  │
           │ Automation│         │ (Daily)  │
           └────┬─────┘          └──────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   AI CONTROL TOWER (Public Layer)                │
│  • Questionnaire answering (auto + human review)                │
│  • Audit package generation                                      │
│  • Trust Center (public compliance portal)                       │
│  • Real-time compliance dashboards                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Architecture

### 1. LiteLLM Integration (Multi-LLM Gateway)

**Purpose:** Replace hardcoded Claude API with flexible multi-LLM support

**Features:**
- Support for Claude, GPT-4, Gemini, open-source models
- Automatic fallback if primary LLM fails
- Cost tracking per LLM call
- Load balancing across LLM providers
- Unified API interface

**Implementation:**
```python
# litellm_integration.py
import litellm
from litellm import completion

class GRCLLMClient:
    def __init__(self, config: dict):
        self.primary_model = config.get('primary_model', 'claude-sonnet-4')
        self.fallback_models = config.get('fallback_models', ['gpt-4', 'gemini-pro'])
        self.cost_tracking = []

    def complete(self, prompt: str, **kwargs):
        """Try primary model, fallback if fails"""
        try:
            response = litellm.completion(
                model=self.primary_model,
                messages=[{"role": "user", "content": prompt}],
                **kwargs
            )
            self._track_cost(self.primary_model, response)
            return response
        except Exception as e:
            logger.warning(f"Primary model {self.primary_model} failed: {e}")
            for fallback in self.fallback_models:
                try:
                    response = litellm.completion(
                        model=fallback,
                        messages=[{"role": "user", "content": prompt}],
                        **kwargs
                    )
                    self._track_cost(fallback, response)
                    return response
                except Exception as e2:
                    logger.warning(f"Fallback {fallback} failed: {e2}")
                    continue
            raise Exception("All LLM providers failed")
```

**Config:**
```yaml
llm:
  primary_model: "claude-sonnet-4-20250514"
  fallback_models:
    - "gpt-4-turbo"
    - "gemini-1.5-pro"
  api_keys:
    anthropic: "${ANTHROPIC_API_KEY}"
    openai: "${OPENAI_API_KEY}"
    google: "${GOOGLE_API_KEY}"
  cost_limits:
    daily_max_usd: 100
    per_request_max_tokens: 4000
```

---

### 2. Temporal.io Integration (Workflow Orchestration)

**Purpose:** Reliable, durable workflow execution for compliance automation

**Workflows:**

1. **Daily Evidence Collection Workflow**
   ```python
   @workflow.defn
   class DailyEvidenceCollectionWorkflow:
       @workflow.run
       async def run(self, framework: str):
           # Collect from all sources in parallel
           wazuh_task = workflow.execute_activity(
               collect_wazuh_evidence,
               framework,
               start_to_close_timeout=timedelta(minutes=10)
           )
           keycloak_task = workflow.execute_activity(
               collect_keycloak_evidence,
               framework,
               start_to_close_timeout=timedelta(minutes=5)
           )
           # ... other sources

           # Wait for all to complete
           results = await asyncio.gather(wazuh_task, keycloak_task, ...)

           # Store results
           await workflow.execute_activity(
               store_evidence_batch,
               results,
               start_to_close_timeout=timedelta(minutes=5)
           )
   ```

2. **Continuous Control Testing Workflow**
   ```python
   @workflow.defn
   class ContinuousControlTestingWorkflow:
       @workflow.run
       async def run(self, control_id: str):
           # Get control test definition
           control = await workflow.execute_activity(
               get_control_definition,
               control_id
           )

           # Execute test based on automation level
           if control.automation_level == 'fully_automated':
               result = await workflow.execute_activity(
                   run_automated_test,
                   control
               )
           else:
               # Schedule manual review
               await workflow.execute_activity(
                   create_manual_test_task,
                   control
               )

           # Update control implementation status
           await workflow.execute_activity(
               update_control_status,
               control_id,
               result
           )
   ```

3. **Audit Package Generation Workflow**
   ```python
   @workflow.defn
   class AuditPackageWorkflow:
       @workflow.run
       async def run(self, client: str, framework: str):
           # Collect all evidence
           evidence = await workflow.execute_activity(
               collect_framework_evidence,
               framework
           )

           # Generate control summaries (parallel)
           summaries = await asyncio.gather(*[
               workflow.execute_activity(generate_control_summary, ctrl)
               for ctrl in evidence.controls
           ])

           # Generate audit package
           package = await workflow.execute_activity(
               create_audit_zip,
               summaries
           )

           # Notify stakeholders
           await workflow.execute_activity(
               send_notification,
               f"Audit package ready: {package}"
           )

           return package
   ```

**Temporal Configuration:**
```python
# temporal_worker.py
from temporalio.client import Client
from temporalio.worker import Worker

async def main():
    client = await Client.connect("localhost:7233")

    worker = Worker(
        client,
        task_queue="grc-compliance",
        workflows=[
            DailyEvidenceCollectionWorkflow,
            ContinuousControlTestingWorkflow,
            AuditPackageWorkflow,
        ],
        activities=[
            collect_wazuh_evidence,
            collect_keycloak_evidence,
            run_automated_test,
            generate_control_summary,
            # ... all activities
        ],
    )

    await worker.run()
```

---

### 3. Obot Integration (Workflow Automation)

**Purpose:** High-level automation orchestrator (think: Zapier for compliance)

**Obot Workflows:**

1. **New Evidence → AI Analysis → Audit Trail**
   ```yaml
   name: evidence-ingestion-pipeline
   trigger:
     type: file_watch
     path: /var/lib/grc/evidence

   steps:
     - name: detect-file
       action: file.read
       output: raw_evidence

     - name: classify-evidence
       action: llm.classify
       model: claude-sonnet-4
       prompt: |
         Classify this evidence file:
         {{raw_evidence}}

         Which control domains does it apply to?

     - name: store-evidence
       action: database.insert
       table: evidence
       data:
         evidence_name: "{{file.name}}"
         evidence_type: "{{classify_evidence.type}}"
         control_domains: "{{classify_evidence.domains}}"

     - name: notify-compliance-team
       action: slack.message
       channel: "#compliance"
       message: "New evidence collected: {{file.name}}"
   ```

2. **Vendor Risk Assessment Workflow**
   ```yaml
   name: vendor-risk-assessment
   trigger:
     type: schedule
     cron: "0 0 1 */3 *"  # Quarterly

   steps:
     - name: get-vendors
       action: database.query
       query: SELECT * FROM vendors WHERE status='active'

     - name: check-soc2-reports
       action: foreach
       items: "{{get-vendors.results}}"
       steps:
         - action: llm.check
           model: gpt-4
           prompt: |
             Check if {{item.vendor_name}} has a valid SOC2 report.
             Search their website: {{item.website}}

         - action: database.update
           table: vendors
           where: id = {{item.id}}
           data:
             soc2_status: "{{llm.check.result}}"
             last_checked: "{{now}}"
   ```

3. **Control Gap Analysis**
   ```yaml
   name: control-gap-analysis
   trigger:
     type: webhook
     path: /api/gap-analysis

   steps:
     - name: get-implemented-controls
       action: database.query
       query: |
         SELECT control_code
         FROM control_implementations
         WHERE framework_id = {{request.framework_id}}
         AND implementation_status = 'implemented'

     - name: get-required-controls
       action: database.query
       query: |
         SELECT control_code
         FROM controls
         WHERE framework_id = {{request.framework_id}}

     - name: calculate-gap
       action: array.diff
       required: "{{get-required-controls.results}}"
       implemented: "{{get-implemented-controls.results}}"

     - name: generate-remediation-plan
       action: llm.generate
       model: claude-sonnet-4
       prompt: |
         We are missing these controls:
         {{calculate-gap.missing}}

         Generate a prioritized remediation plan.

     - name: create-jira-tickets
       action: foreach
       items: "{{remediation-plan.tasks}}"
       steps:
         - action: jira.create-issue
           project: COMPLIANCE
           summary: "Implement {{item.control}}"
           description: "{{item.implementation_guidance}}"
   ```

---

### 4. Complete Control Library Import

**OSCAL (NIST 800-53 Rev 5):**
```python
# import_oscal.py
import json
import requests
from pathlib import Path

def import_nist_800_53_oscal():
    """Import NIST 800-53 Rev 5 from official OSCAL catalog"""

    # Download official OSCAL catalog
    url = "https://raw.githubusercontent.com/usnistgov/oscal-content/main/nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_catalog.json"
    response = requests.get(url)
    catalog = response.json()

    # Parse catalog structure
    framework_id = create_framework("NIST-800-53", "Rev5", "OSCAL")

    for group in catalog['catalog']['groups']:
        # Create control domain
        domain_id = create_domain(
            framework_id,
            group['id'],
            group['title']
        )

        for control in group['controls']:
            # Create control
            create_control(
                domain_id,
                control['id'],
                control['title'],
                control['parts'][0]['prose'],  # Description
                control_type='preventive'  # Would need to parse from control
            )

            # Handle control enhancements
            if 'controls' in control:
                for enhancement in control['controls']:
                    create_control(
                        domain_id,
                        enhancement['id'],
                        enhancement['title'],
                        enhancement['parts'][0]['prose'],
                        control_type='preventive'
                    )
```

**ComplianceForge SCF:**
```python
# import_scf.py
import openpyxl

def import_complianceforge_scf():
    """Import ComplianceForge Secure Controls Framework"""

    # Download SCF Excel file
    # https://www.complianceforge.com/secure-controls-framework-scf/

    workbook = openpyxl.load_workbook('SCF_2024.1.xlsx')
    sheet = workbook['Controls']

    framework_id = create_framework("ComplianceForge-SCF", "2024.1", "ComplianceForge")

    for row in sheet.iter_rows(min_row=2, values_only=True):
        domain_code, control_id, control_title, control_desc, control_type, mappings = row[:6]

        # Create domain if doesn't exist
        domain_id = get_or_create_domain(framework_id, domain_code)

        # Create control
        create_control(
            domain_id,
            control_id,
            control_title,
            control_desc,
            control_type=control_type.lower()
        )

        # Parse mappings to NIST, ISO, etc.
        if mappings:
            create_control_mappings(control_id, mappings)
```

**CSA CCM v4:**
```python
# import_csa_ccm.py
import pandas as pd

def import_csa_ccm():
    """Import Cloud Security Alliance Cloud Controls Matrix"""

    # Download CCM Excel
    # https://cloudsecurityalliance.org/artifacts/cloud-controls-matrix-v4/

    df = pd.read_excel('CCM_v4.xlsx', sheet_name='Controls')

    framework_id = create_framework("CSA-CCM", "v4", "Cloud Security Alliance")

    for _, row in df.iterrows():
        domain_id = get_or_create_domain(
            framework_id,
            row['Domain'],
            row['Domain Title']
        )

        create_control(
            domain_id,
            row['Control ID'],
            row['Control Title'],
            row['Control Specification'],
            control_type='preventive'  # CCM doesn't specify
        )

        # Add CCM-specific metadata
        update_control_metadata(
            row['Control ID'],
            {
                'ccm_version': 'v4',
                'cloud_specific': True,
                'shared_responsibility': row['Shared Responsibility']
            }
        )
```

---

### 5. Creature Database → GRC Mapping

**Purpose:** Map your comprehensive Master Creature Index to GRC controls

**Mapping Table:**
```sql
-- Add to schema.sql
CREATE TABLE IF NOT EXISTS creature_control_mappings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    creature_id UUID NOT NULL REFERENCES creatures(id) ON DELETE CASCADE,
    control_id UUID NOT NULL REFERENCES controls(id) ON DELETE CASCADE,
    mapping_type TEXT NOT NULL, -- 'implements', 'provides_evidence', 'scoped_to'
    automation_capability BOOLEAN DEFAULT false,
    evidence_source_config JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(creature_id, control_id, mapping_type)
);

CREATE INDEX idx_creature_control_creature ON creature_control_mappings(creature_id);
CREATE INDEX idx_creature_control_control ON creature_control_mappings(control_id);
```

**Example Mappings:**
```python
# map_creatures_to_controls.py

# Example 1: Wazuh (monitoring creature) → CC6.1, CC7.1
create_creature_control_mapping(
    creature_id=get_creature_by_name("Wazuh SIEM"),
    control_id=get_control_by_code("CC6.1"),  # Authentication
    mapping_type='provides_evidence',
    automation_capability=True,
    evidence_source_config={
        'collector_class': 'WazuhEvidenceCollector',
        'collection_method': 'collect_authentication_logs',
        'frequency': 'daily'
    }
)

# Example 2: Keycloak (IAM creature) → CC6.1, CC6.2, CC6.3
create_creature_control_mapping(
    creature_id=get_creature_by_name("Keycloak IAM"),
    control_id=get_control_by_code("CC6.1"),
    mapping_type='implements',
    automation_capability=True,
    evidence_source_config={
        'collector_class': 'KeycloakEvidenceCollector',
        'collection_method': 'collect_mfa_config',
        'frequency': 'weekly'
    }
)

# Example 3: Physical data center → Physical security controls
create_creature_control_mapping(
    creature_id=get_creature_by_name("Hobart Data Center"),
    control_id=get_control_by_code("A.7.1.1"),  # ISO 27001 physical security
    mapping_type='scoped_to',
    automation_capability=False,  # Manual inspection required
    evidence_source_config={
        'evidence_type': 'physical_inspection_report',
        'frequency': 'quarterly'
    }
)
```

**Automated Mapping Generator:**
```python
# auto_map_creatures.py
def auto_map_creatures_to_controls():
    """Use AI to suggest creature-to-control mappings"""

    creatures = get_all_creatures()
    controls = get_all_controls()

    for creature in creatures:
        # Use LLM to suggest mappings
        prompt = f"""
        Given this infrastructure component:
        Name: {creature.name}
        Class: {creature.creature_class}
        Domain: {creature.creature_domain}
        Description: {creature.description}

        Which of these compliance controls does it relate to?
        {[f"{c.control_code}: {c.control_name}" for c in controls]}

        For each relevant control, specify:
        1. Mapping type: implements | provides_evidence | scoped_to
        2. Can evidence collection be automated? yes/no
        3. What evidence can be collected automatically?

        Return JSON.
        """

        response = llm_client.complete(prompt)
        suggested_mappings = parse_mapping_suggestions(response)

        # Store suggestions for human review
        store_mapping_suggestions(creature.id, suggested_mappings)
```

---

### 6. Continuous Compliance Monitoring

**Real-time Control Status:**
```python
# continuous_monitoring.py
from temporalio import workflow

@workflow.defn
class ContinuousComplianceMonitoring:
    @workflow.run
    async def run(self):
        """Run forever, checking controls continuously"""

        while True:
            # Get all controls that need testing
            controls_to_test = await workflow.execute_activity(
                get_controls_due_for_testing,
                start_to_close_timeout=timedelta(minutes=5)
            )

            # Test each control
            for control in controls_to_test:
                await workflow.execute_child_workflow(
                    ContinuousControlTestingWorkflow,
                    args=[control.id]
                )

            # Wait until next check (every hour)
            await asyncio.sleep(3600)
```

**Drift Detection:**
```python
# drift_detection.py
def detect_configuration_drift():
    """Detect when infrastructure config drifts from compliance baseline"""

    # Example: Keycloak MFA enforcement
    current_config = collect_keycloak_mfa_config()
    baseline_config = get_baseline_from_db("keycloak_mfa_baseline")

    if current_config != baseline_config:
        create_finding(
            control_id=get_control_by_code("CC6.1"),
            severity='high',
            title="MFA configuration drift detected",
            description=f"Current: {current_config}, Expected: {baseline_config}",
            remediation_plan="Review and revert Keycloak MFA settings"
        )

        send_alert("Compliance drift detected: Keycloak MFA")
```

---

## Deployment Architecture

### Production Stack

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: grc_platform
      POSTGRES_USER: grc_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - ./schema.sql:/docker-entrypoint-initdb.d/schema.sql
      - postgres_data:/var/lib/postgresql/data

  temporal:
    image: temporalio/auto-setup:latest
    ports:
      - "7233:7233"
    environment:
      - DB=postgresql
      - DB_PORT=5432
      - POSTGRES_SEEDS=postgres

  temporal-ui:
    image: temporalio/ui:latest
    ports:
      - "8080:8080"
    environment:
      - TEMPORAL_ADDRESS=temporal:7233

  temporal-worker:
    build: .
    command: python temporal_worker.py
    depends_on:
      - temporal
      - postgres
    environment:
      - TEMPORAL_HOST=temporal:7233
      - DATABASE_URL=postgresql://grc_user:${DB_PASSWORD}@postgres/grc_platform

  litellm:
    image: ghcr.io/berriai/litellm:latest
    ports:
      - "4000:4000"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
    volumes:
      - ./litellm_config.yaml:/app/config.yaml

  obot:
    image: obot/obot:latest
    ports:
      - "9000:9000"
    volumes:
      - ./obot_workflows:/workflows

  trust-center-ui:
    build: ./trust-center
    ports:
      - "3000:3000"
    environment:
      - API_URL=http://api:8000

  api:
    build: .
    command: uvicorn api:app --host 0.0.0.0 --port 8000
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - litellm
    environment:
      - DATABASE_URL=postgresql://grc_user:${DB_PASSWORD}@postgres/grc_platform
      - LITELLM_URL=http://litellm:4000

volumes:
  postgres_data:
```

---

## Comparison: ServiceNow AI Control Tower vs CreatureGRC

| Feature | ServiceNow | CreatureGRC |
|---------|------------|-------------|
| **Asset-Control Mapping** | CMDB → GRC | Creature DB → GRC |
| **Multi-LLM Support** | Built-in | LiteLLM |
| **Workflow Engine** | Flow Designer | Temporal.io + Obot |
| **Control Libraries** | Pre-loaded | Import via OSCAL/SCF/CCM |
| **Evidence Automation** | Integration Hub | Python collectors |
| **Continuous Monitoring** | Yes | Temporal workflows |
| **Trust Center** | Yes | Custom React UI |
| **Multi-tenant** | Yes | Database schema ready |
| **Cost** | $$$$ (per user) | $0 (self-hosted) |

**Result:** Full feature parity, zero licensing costs, full data sovereignty.

---

## Next Steps

1. ✅ **Confirm architecture** (this document)
2. 🚧 **Implement LiteLLM integration**
3. 🚧 **Set up Temporal.io workflows**
4. 🚧 **Configure Obot automations**
5. 🚧 **Import complete control libraries**
6. 🚧 **Map Creature Database to controls**
7. 🚧 **Build Trust Center UI**
8. 🚧 **Deploy to production**

Ready to proceed?
