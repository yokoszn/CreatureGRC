#!/usr/bin/env python3
"""
Import CSA Cloud Controls Matrix (CCM) v4
Downloads and imports the complete CCM control library
"""

import json
import logging
import psycopg2
import requests
import pandas as pd
from typing import Dict, List, Any, Optional
from pathlib import Path
import yaml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CCMImporter:
    """Import CSA Cloud Controls Matrix"""

    def __init__(self, db_config: Dict[str, str]):
        self.db_config = db_config
        self.conn = psycopg2.connect(**db_config)

    def download_ccm_excel(self, output_path: Path) -> Path:
        """
        Download CCM Excel file from CSA

        CCM is freely available at:
        https://cloudsecurityalliance.org/research/cloud-controls-matrix
        """
        logger.info("Downloading CSA CCM v4...")

        # CCM is available on GitHub
        url = "https://raw.githubusercontent.com/cloudsecurityalliance/ccm/main/Cloud%20Controls%20Matrix%20v4.xlsx"

        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()

            with open(output_path, 'wb') as f:
                f.write(response.content)

            logger.info(f"Downloaded CCM to {output_path}")
            return output_path

        except Exception as e:
            logger.warning(f"Could not auto-download CCM: {e}")
            logger.warning("Please manually download from:")
            logger.warning("https://cloudsecurityalliance.org/research/cloud-controls-matrix")
            logger.warning(f"and save to: {output_path}")

            if not output_path.exists():
                raise FileNotFoundError(f"CCM file not found at {output_path}")

            return output_path

    def create_framework(self) -> str:
        """Create CCM framework entry"""
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO compliance_frameworks (name, version, source, description, framework_url)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (name) DO UPDATE SET
                    version = EXCLUDED.version,
                    description = EXCLUDED.description
                RETURNING id
            """, (
                "CSA-CCM",
                "v4",
                "Cloud Security Alliance",
                "Cloud Controls Matrix - Cloud security controls",
                "https://cloudsecurityalliance.org/research/cloud-controls-matrix"
            ))

            framework_id = cur.fetchone()[0]
            self.conn.commit()

        return framework_id

    def create_domain(self, framework_id: str, domain_code: str, domain_title: str, description: str = "") -> str:
        """Create or get domain ID"""
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO control_domains (framework_id, domain_code, domain_name, description)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (framework_id, domain_code) DO UPDATE SET
                    domain_name = EXCLUDED.domain_name,
                    description = EXCLUDED.description
                RETURNING id
            """, (framework_id, domain_code, domain_title, description))

            domain_id = cur.fetchone()[0]
            self.conn.commit()

        return domain_id

    def import_ccm_from_excel(self, excel_path: Path):
        """Import CCM controls from Excel file"""
        logger.info(f"Loading CCM Excel file: {excel_path}")

        # Read Excel file
        # CCM usually has a "CCM v4" or similar sheet
        try:
            df = pd.read_excel(excel_path, sheet_name='CCM v4')
        except ValueError:
            # Try first sheet
            df = pd.read_excel(excel_path, sheet_name=0)

        logger.info(f"Loaded {len(df)} rows from Excel")
        logger.info(f"Columns: {df.columns.tolist()}")

        # Create framework
        framework_id = self.create_framework()

        # CCM structure (approximate - may vary by version):
        # - Domain (e.g., "AIS", "BCR", "CCC")
        # - Domain Title (e.g., "Application & Interface Security")
        # - Control ID (e.g., "AIS-01")
        # - Control Title
        # - Control Specification
        # - Shared Responsibility (CSP/Customer)

        # Map column names (case-insensitive search)
        col_map = {}
        for col in df.columns:
            col_lower = str(col).lower()

            if 'domain' in col_lower and 'title' not in col_lower:
                col_map['domain'] = col
            elif 'domain title' in col_lower or 'domain name' in col_lower:
                col_map['domain_title'] = col
            elif 'control id' in col_lower or 'ccm id' in col_lower:
                col_map['control_id'] = col
            elif 'control title' in col_lower or 'control objective' in col_lower:
                col_map['control_title'] = col
            elif 'specification' in col_lower or 'control spec' in col_lower:
                col_map['control_spec'] = col
            elif 'shared' in col_lower and 'responsibility' in col_lower:
                col_map['shared_resp'] = col

        logger.info(f"Column mapping: {col_map}")

        # Check required columns
        required = ['domain', 'control_id', 'control_title', 'control_spec']
        missing = [c for c in required if c not in col_map]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        # Process rows
        domains_cache = {}
        control_count = 0

        for idx, row in df.iterrows():
            try:
                domain_code = row[col_map['domain']]
                control_id = row[col_map['control_id']]
                control_title = row[col_map['control_title']]
                control_spec = row[col_map['control_spec']]

                # Skip empty rows
                if pd.isna(domain_code) or pd.isna(control_id):
                    continue

                # Clean data
                domain_code = str(domain_code).strip()
                control_id = str(control_id).strip()
                control_title = str(control_title).strip()
                control_spec = str(control_spec).strip() if not pd.isna(control_spec) else ""

                # Get domain title
                domain_title = row[col_map.get('domain_title', domain_code)]
                if pd.isna(domain_title):
                    domain_title = f"CCM Domain {domain_code}"
                else:
                    domain_title = str(domain_title).strip()

                # Create domain if not exists
                if domain_code not in domains_cache:
                    domains_cache[domain_code] = self.create_domain(
                        framework_id,
                        domain_code,
                        domain_title
                    )

                domain_id = domains_cache[domain_code]

                # Get shared responsibility
                shared_resp = row[col_map.get('shared_resp', '')] if 'shared_resp' in col_map else ""

                # CCM controls are generally preventive (cloud security)
                control_type = 'preventive'

                metadata = {
                    'ccm_version': 'v4',
                    'shared_responsibility': str(shared_resp) if not pd.isna(shared_resp) else "",
                    'cloud_specific': True
                }

                # Insert control
                with self.conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO controls (
                            domain_id,
                            control_code,
                            control_name,
                            control_description,
                            control_type,
                            metadata
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (domain_id, control_code) DO UPDATE SET
                            control_name = EXCLUDED.control_name,
                            control_description = EXCLUDED.control_description,
                            metadata = EXCLUDED.metadata
                    """, (
                        domain_id,
                        control_id,
                        control_title,
                        control_spec,
                        control_type,
                        json.dumps(metadata)
                    ))

                control_count += 1

                if control_count % 20 == 0:
                    logger.info(f"Imported {control_count} CCM controls...")
                    self.conn.commit()

            except Exception as e:
                logger.error(f"Error processing row {idx}: {e}")
                logger.error(f"Row data: {row}")
                continue

        self.conn.commit()

        logger.info(f"✅ CCM import complete! Imported {control_count} controls")
        return control_count


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Import CSA Cloud Controls Matrix')
    parser.add_argument('--config', required=True, help='Database config YAML file')
    parser.add_argument('--ccm-excel', help='Path to CCM Excel file (will auto-download if not provided)')
    parser.add_argument('--download', action='store_true', help='Force download of CCM')

    args = parser.parse_args()

    # Load config
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)

    # Determine Excel path
    if args.ccm_excel:
        excel_path = Path(args.ccm_excel)
    else:
        excel_path = Path('/tmp/ccm_v4.xlsx')

    # Import
    importer = CCMImporter(config['database'])

    if args.download or not excel_path.exists():
        importer.download_ccm_excel(excel_path)

    total = importer.import_ccm_from_excel(excel_path)

    print(f"\n✅ Successfully imported {total} CSA CCM v4 controls!")


if __name__ == "__main__":
    main()
