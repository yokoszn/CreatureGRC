#!/usr/bin/env python3
"""
Map Creatures (from Master Creature Index) to GRC Controls
Uses AI to suggest mappings based on creature description and control requirements
"""

import json
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Any, Optional
import yaml
from litellm_integration import GRCLLMClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CreatureControlMapper:
    """Map infrastructure creatures to compliance controls"""

    def __init__(self, db_config: Dict[str, str], llm_config: Dict[str, Any]):
        self.db_config = db_config
        self.llm = GRCLLMClient(llm_config)

    def get_db_connection(self):
        return psycopg2.connect(**self.db_config, cursor_factory=RealDictCursor)

    def get_all_creatures(self) -> List[Dict[str, Any]]:
        """Get all creatures from database"""
        with self.get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        id,
                        name,
                        creature_class,
                        creature_domain,
                        description,
                        sovereignty_status,
                        criticality,
                        metadata
                    FROM creatures
                    ORDER BY criticality DESC, name
                """)
                return [dict(row) for row in cur.fetchall()]

    def get_controls_by_framework(self, framework: str) -> List[Dict[str, Any]]:
        """Get all controls for a framework"""
        with self.get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        c.id AS control_id,
                        c.control_code,
                        c.control_name,
                        c.control_description,
                        c.control_type,
                        cd.domain_code,
                        cd.domain_name,
                        cf.name AS framework_name
                    FROM controls c
                    JOIN control_domains cd ON c.domain_id = cd.id
                    JOIN compliance_frameworks cf ON cd.framework_id = cf.id
                    WHERE cf.name = %s
                    ORDER BY cd.domain_code, c.control_code
                """, (framework,))
                return [dict(row) for row in cur.fetchall()]

    def suggest_mappings_with_ai(
        self,
        creature: Dict[str, Any],
        controls: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Use AI to suggest creature-to-control mappings"""

        # Create a concise control summary for the prompt
        control_summary = []
        for control in controls[:100]:  # Limit to avoid token limits
            control_summary.append({
                'code': control['control_code'],
                'name': control['control_name'],
                'domain': control['domain_code'],
                'type': control['control_type']
            })

        prompt = f"""
You are a compliance mapping expert. Given this infrastructure component ("creature"),
suggest which compliance controls it relates to.

**CREATURE:**
- Name: {creature['name']}
- Class: {creature['creature_class']}
- Domain: {creature['creature_domain']}
- Description: {creature.get('description', 'No description')}
- Criticality: {creature.get('criticality', 'unknown')}

**CONTROLS AVAILABLE:**
{json.dumps(control_summary, indent=2)}

For each relevant control, specify:
1. **control_code**: The control code (e.g., "CC6.1")
2. **mapping_type**: One of:
   - "implements": This creature directly implements the control
   - "provides_evidence": This creature can provide automated evidence for the control
   - "scoped_to": The control applies to this creature
3. **automation_capability**: Can evidence be collected automatically? (true/false)
4. **evidence_method**: If automated, what can be collected? (e.g., "configuration snapshot", "access logs", "scan results")
5. **confidence**: Your confidence in this mapping (0-100)
6. **rationale**: Brief explanation

Only suggest mappings with confidence >= 70.

Return ONLY valid JSON array:
[
  {{
    "control_code": "CC6.1",
    "mapping_type": "provides_evidence",
    "automation_capability": true,
    "evidence_method": "MFA configuration export from Keycloak API",
    "confidence": 95,
    "rationale": "Keycloak provides authentication and MFA, directly relevant to CC6.1"
  }},
  ...
]
"""

        try:
            response = self.llm.complete(
                prompt=prompt,
                temperature=0.3,
                max_tokens=2000,
                response_format="json"
            )

            # Parse response
            if isinstance(response['content'], list):
                mappings = response['content']
            else:
                # Fallback parsing
                logger.warning(f"AI returned non-list response, attempting to parse")
                mappings = []

            # Filter by confidence
            high_confidence_mappings = [
                m for m in mappings
                if m.get('confidence', 0) >= 70
            ]

            logger.info(f"AI suggested {len(high_confidence_mappings)} high-confidence mappings for {creature['name']}")

            return high_confidence_mappings

        except Exception as e:
            logger.error(f"AI mapping failed for {creature['name']}: {e}")
            return []

    def store_mapping(
        self,
        creature_id: str,
        control_code: str,
        mapping_type: str,
        automation_capability: bool,
        evidence_source_config: Dict[str, Any]
    ):
        """Store creature-control mapping in database"""

        # First, add the creature_control_mappings table if it doesn't exist
        with self.get_db_connection() as conn:
            with conn.cursor() as cur:
                # Ensure table exists (should already exist from schema.sql update)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS creature_control_mappings (
                        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                        creature_id UUID NOT NULL REFERENCES creatures(id) ON DELETE CASCADE,
                        control_id UUID NOT NULL REFERENCES controls(id) ON DELETE CASCADE,
                        mapping_type TEXT NOT NULL,
                        automation_capability BOOLEAN DEFAULT false,
                        evidence_source_config JSONB DEFAULT '{}'::jsonb,
                        created_at TIMESTAMPTZ DEFAULT NOW(),
                        UNIQUE(creature_id, control_id, mapping_type)
                    )
                """)

                # Get control ID from code
                cur.execute("""
                    SELECT id FROM controls WHERE control_code = %s LIMIT 1
                """, (control_code,))

                row = cur.fetchone()
                if not row:
                    logger.warning(f"Control {control_code} not found, skipping mapping")
                    return None

                control_id = row['id']

                # Insert mapping
                cur.execute("""
                    INSERT INTO creature_control_mappings (
                        creature_id,
                        control_id,
                        mapping_type,
                        automation_capability,
                        evidence_source_config
                    ) VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (creature_id, control_id, mapping_type) DO UPDATE SET
                        automation_capability = EXCLUDED.automation_capability,
                        evidence_source_config = EXCLUDED.evidence_source_config
                    RETURNING id
                """, (
                    creature_id,
                    control_id,
                    mapping_type,
                    automation_capability,
                    json.dumps(evidence_source_config)
                ))

                mapping_id = cur.fetchone()['id']
                conn.commit()

                return mapping_id

    def map_all_creatures_to_framework(self, framework: str = "SOC2", auto_approve: bool = False):
        """Map all creatures to controls for a framework"""

        logger.info(f"Starting creature-to-control mapping for {framework}...")

        creatures = self.get_all_creatures()
        controls = self.get_controls_by_framework(framework)

        logger.info(f"Found {len(creatures)} creatures and {len(controls)} controls")

        total_mappings = 0

        for creature in creatures:
            logger.info(f"\nProcessing creature: {creature['name']}")

            # Get AI suggestions
            suggestions = self.suggest_mappings_with_ai(creature, controls)

            if not suggestions:
                logger.info(f"  No high-confidence mappings found")
                continue

            logger.info(f"  Found {len(suggestions)} suggested mappings:")

            for suggestion in suggestions:
                logger.info(f"    - {suggestion['control_code']}: {suggestion['rationale'][:80]}...")

                if auto_approve or self._user_approves_mapping(creature, suggestion):
                    # Store mapping
                    evidence_config = {
                        'evidence_method': suggestion.get('evidence_method', ''),
                        'ai_confidence': suggestion.get('confidence', 0),
                        'ai_rationale': suggestion.get('rationale', '')
                    }

                    self.store_mapping(
                        creature['id'],
                        suggestion['control_code'],
                        suggestion['mapping_type'],
                        suggestion['automation_capability'],
                        evidence_config
                    )

                    total_mappings += 1

        logger.info(f"\n✅ Mapping complete! Created {total_mappings} creature-control mappings")

    def _user_approves_mapping(self, creature: Dict, suggestion: Dict) -> bool:
        """Interactive approval for mappings (simple version)"""
        # In production, this could be a web UI
        # For now, auto-approve high confidence
        return suggestion['confidence'] >= 85

    def populate_example_creatures(self):
        """Populate database with example creatures from Master Creature Index"""

        examples = [
            {
                'name': 'Wazuh SIEM',
                'creature_class': 'application',
                'creature_domain': 'security',
                'description': 'SIEM and EDR platform for security monitoring, log collection, and threat detection',
                'sovereignty_status': 'self-hosted',
                'criticality': 'critical'
            },
            {
                'name': 'Keycloak IAM',
                'creature_class': 'application',
                'creature_domain': 'identity',
                'description': 'Identity and Access Management platform providing SSO, MFA, and RBAC',
                'sovereignty_status': 'self-hosted',
                'criticality': 'critical'
            },
            {
                'name': 'Hobart Data Center',
                'creature_class': 'facility',
                'creature_domain': 'physical',
                'description': 'Primary data center facility with physical security controls, CCTV, access cards',
                'sovereignty_status': 'self-owned',
                'criticality': 'critical'
            },
            {
                'name': 'GitHub Organization',
                'creature_class': 'platform',
                'creature_domain': 'development',
                'description': 'Source code repository with audit logs, branch protection, code review workflows',
                'sovereignty_status': 'vendor-controlled',
                'criticality': 'high'
            },
            {
                'name': 'PostgreSQL Production',
                'creature_class': 'database',
                'creature_domain': 'data',
                'description': 'Primary production database with encryption at rest, access controls, backup automation',
                'sovereignty_status': 'self-hosted',
                'criticality': 'critical'
            }
        ]

        with self.get_db_connection() as conn:
            with conn.cursor() as cur:
                for creature in examples:
                    cur.execute("""
                        INSERT INTO creatures (
                            name, creature_class, creature_domain, description,
                            sovereignty_status, criticality
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                        RETURNING id
                    """, (
                        creature['name'],
                        creature['creature_class'],
                        creature['creature_domain'],
                        creature['description'],
                        creature['sovereignty_status'],
                        creature['criticality']
                    ))

                conn.commit()

        logger.info(f"✅ Populated {len(examples)} example creatures")


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Map Creatures to Controls using AI')
    parser.add_argument('--config', required=True, help='Config YAML file')
    parser.add_argument('--framework', default='SOC2', help='Framework to map to')
    parser.add_argument('--populate-examples', action='store_true', help='Populate example creatures first')
    parser.add_argument('--auto-approve', action='store_true', help='Auto-approve high-confidence mappings')

    args = parser.parse_args()

    # Load config
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)

    # Create mapper
    mapper = CreatureControlMapper(
        config['database'],
        config['llm']
    )

    # Populate examples if requested
    if args.populate_examples:
        mapper.populate_example_creatures()

    # Map creatures to controls
    mapper.map_all_creatures_to_framework(
        framework=args.framework,
        auto_approve=args.auto_approve
    )

    print(f"\n✅ Creature-to-control mapping complete!")
    print(f"\nView mappings:")
    print(f"  psql -U {config['database']['user']} -d {config['database']['database']} -c 'SELECT * FROM creature_control_mappings;'")


if __name__ == "__main__":
    main()
