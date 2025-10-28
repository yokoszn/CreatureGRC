#!/usr/bin/env python3
"""
Import NIST 800-53 Rev 5 from OSCAL catalog
Downloads official OSCAL JSON and imports all 1000+ controls
"""

import json
import logging
import psycopg2
import requests
from typing import Dict, List, Any, Optional
from pathlib import Path
import yaml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OSCALImporter:
    """Import controls from OSCAL format"""

    def __init__(self, db_config: Dict[str, str]):
        self.db_config = db_config
        self.conn = psycopg2.connect(**db_config)

    def download_nist_800_53_catalog(self) -> Dict[str, Any]:
        """Download official NIST 800-53 Rev 5 OSCAL catalog"""
        logger.info("Downloading NIST SP 800-53 Rev 5 OSCAL catalog...")

        url = "https://raw.githubusercontent.com/usnistgov/oscal-content/main/nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_catalog.json"

        response = requests.get(url, timeout=60)
        response.raise_for_status()

        catalog = response.json()
        logger.info(f"Downloaded catalog: {catalog['catalog']['metadata']['title']}")

        return catalog

    def create_framework(self, name: str, version: str, source: str, description: str, url: str) -> str:
        """Create or get framework ID"""
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO compliance_frameworks (name, version, source, description, framework_url)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (name) DO UPDATE SET
                    version = EXCLUDED.version,
                    description = EXCLUDED.description,
                    framework_url = EXCLUDED.framework_url
                RETURNING id
            """, (name, version, source, description, url))

            framework_id = cur.fetchone()[0]
            self.conn.commit()

        logger.info(f"Created/updated framework: {name} (ID: {framework_id})")
        return framework_id

    def create_domain(self, framework_id: str, domain_code: str, domain_name: str, description: str = "") -> str:
        """Create or get control domain ID"""
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO control_domains (framework_id, domain_code, domain_name, description)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (framework_id, domain_code) DO UPDATE SET
                    domain_name = EXCLUDED.domain_name,
                    description = EXCLUDED.description
                RETURNING id
            """, (framework_id, domain_code, domain_name, description))

            domain_id = cur.fetchone()[0]
            self.conn.commit()

        return domain_id

    def parse_control_description(self, parts: List[Dict[str, Any]]) -> str:
        """Parse OSCAL control parts into description"""
        description_parts = []

        for part in parts:
            if part.get('name') == 'statement':
                # Main control statement
                if 'prose' in part:
                    description_parts.append(part['prose'])

                # Handle nested parts (sub-statements)
                if 'parts' in part:
                    for subpart in part['parts']:
                        if 'prose' in subpart:
                            description_parts.append(f"  {subpart['prose']}")

        return "\n\n".join(description_parts)

    def parse_testing_procedures(self, parts: List[Dict[str, Any]]) -> Optional[str]:
        """Extract testing/assessment procedures from control"""
        for part in parts:
            if part.get('name') == 'assessment':
                if 'prose' in part:
                    return part['prose']

                # Check nested parts
                if 'parts' in part:
                    procedures = []
                    for subpart in part['parts']:
                        if 'prose' in subpart:
                            procedures.append(subpart['prose'])
                    if procedures:
                        return "\n".join(procedures)

        return None

    def determine_control_type(self, control_id: str, description: str) -> str:
        """Heuristically determine control type"""
        description_lower = description.lower()

        # Preventive controls
        if any(keyword in description_lower for keyword in ['prevent', 'block', 'restrict', 'enforce', 'require']):
            return 'preventive'

        # Detective controls
        if any(keyword in description_lower for keyword in ['monitor', 'detect', 'audit', 'log', 'review', 'assess']):
            return 'detective'

        # Corrective controls
        if any(keyword in description_lower for keyword in ['respond', 'remediate', 'recover', 'restore', 'fix']):
            return 'corrective'

        # Default to preventive for most NIST controls
        return 'preventive'

    def import_control(
        self,
        domain_id: str,
        control_id: str,
        title: str,
        parts: List[Dict[str, Any]],
        properties: List[Dict[str, Any]] = None
    ) -> str:
        """Import a single control"""

        description = self.parse_control_description(parts)
        testing_procedures = self.parse_testing_procedures(parts)
        control_type = self.determine_control_type(control_id, description)

        # Determine if it's a key control (NIST doesn't explicitly mark this)
        # We'll mark "core" controls (AC, AU, CM, IA, SC) as key controls
        is_key_control = control_id.split('-')[0] in ['AC', 'AU', 'CM', 'IA', 'SC', 'SI']

        # Extract additional metadata from properties
        metadata = {}
        if properties:
            for prop in properties:
                if prop.get('name') == 'label':
                    metadata['label'] = prop.get('value')
                elif prop.get('name') == 'sort-id':
                    metadata['sort_id'] = prop.get('value')

        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO controls (
                    domain_id,
                    control_code,
                    control_name,
                    control_description,
                    control_type,
                    testing_procedures,
                    is_key_control,
                    metadata
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (domain_id, control_code) DO UPDATE SET
                    control_name = EXCLUDED.control_name,
                    control_description = EXCLUDED.control_description,
                    control_type = EXCLUDED.control_type,
                    testing_procedures = EXCLUDED.testing_procedures,
                    is_key_control = EXCLUDED.is_key_control,
                    metadata = EXCLUDED.metadata
                RETURNING id
            """, (
                domain_id,
                control_id,
                title,
                description,
                control_type,
                testing_procedures,
                is_key_control,
                json.dumps(metadata)
            ))

            control_db_id = cur.fetchone()[0]
            self.conn.commit()

        return control_db_id

    def import_nist_800_53(self):
        """Import complete NIST 800-53 Rev 5 catalog"""
        logger.info("Starting NIST 800-53 Rev 5 import...")

        # Download catalog
        catalog_data = self.download_nist_800_53_catalog()
        catalog = catalog_data['catalog']

        # Create framework
        framework_id = self.create_framework(
            name="NIST-800-53",
            version="Rev5",
            source="OSCAL",
            description=catalog['metadata']['title'],
            url="https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final"
        )

        # Process control groups (families)
        control_count = 0
        enhancement_count = 0

        for group in catalog['groups']:
            # Create domain for this control family
            family_id = group['id']  # e.g., "ac" for Access Control
            family_title = group['title']  # e.g., "Access Control"

            logger.info(f"Processing family: {family_id.upper()} - {family_title}")

            domain_id = self.create_domain(
                framework_id,
                family_id.upper(),
                family_title,
                ""
            )

            # Process controls in this family
            for control in group.get('controls', []):
                control_id = control['id'].upper()  # e.g., "AC-1"
                control_title = control['title']
                control_parts = control.get('parts', [])
                control_props = control.get('props', [])

                # Import base control
                self.import_control(
                    domain_id,
                    control_id,
                    control_title,
                    control_parts,
                    control_props
                )
                control_count += 1

                # Process control enhancements (e.g., AC-1(1), AC-1(2))
                for enhancement in control.get('controls', []):
                    enhancement_id = enhancement['id'].upper()
                    enhancement_title = enhancement['title']
                    enhancement_parts = enhancement.get('parts', [])
                    enhancement_props = enhancement.get('props', [])

                    self.import_control(
                        domain_id,
                        enhancement_id,
                        f"{control_title} - {enhancement_title}",
                        enhancement_parts,
                        enhancement_props
                    )
                    enhancement_count += 1

                if (control_count + enhancement_count) % 50 == 0:
                    logger.info(f"Imported {control_count} controls, {enhancement_count} enhancements...")

        logger.info(f"✅ NIST 800-53 import complete!")
        logger.info(f"   Total base controls: {control_count}")
        logger.info(f"   Total enhancements: {enhancement_count}")
        logger.info(f"   Grand total: {control_count + enhancement_count}")

        return control_count + enhancement_count


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Import NIST 800-53 Rev 5 from OSCAL')
    parser.add_argument('--config', required=True, help='Database config YAML file')
    parser.add_argument('--test', action='store_true', help='Test mode (import only first 10 controls)')

    args = parser.parse_args()

    # Load config
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)

    # Import
    importer = OSCALImporter(config['database'])

    if args.test:
        logger.info("TEST MODE: Importing only first family...")
        # Modify to import only first family

    total = importer.import_nist_800_53()

    print(f"\n✅ Successfully imported {total} NIST 800-53 Rev 5 controls!")
    print(f"\nVerify with:")
    print(f"  psql -U {config['database']['user']} -d {config['database']['database']} -c \"SELECT COUNT(*) FROM controls WHERE domain_id IN (SELECT id FROM control_domains WHERE framework_id = (SELECT id FROM compliance_frameworks WHERE name = 'NIST-800-53'));\"")


if __name__ == "__main__":
    main()
