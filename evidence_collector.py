#!/usr/bin/env python3
"""
Evidence Automation Engine
Automatically collects evidence from various sources to prove control effectiveness
"""

import os
import sys
import json
import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import psycopg2
from psycopg2.extras import RealDictCursor
import requests
from dataclasses import dataclass, asdict
import subprocess
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class EvidenceRecord:
    """Represents a piece of evidence"""
    evidence_name: str
    evidence_type: str
    control_implementation_id: str
    collection_method: str
    collection_timestamp: datetime
    evidence_period_start: Optional[datetime]
    evidence_period_end: Optional[datetime]
    file_path: str
    file_hash: str
    source_system: str
    source_query: Optional[str]
    collected_by_id: str
    metadata: Dict[str, Any]


class EvidenceCollector:
    """Base class for evidence collectors"""
    
    def __init__(self, db_config: Dict[str, str], output_dir: Path):
        self.db_config = db_config
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)
    
    def save_evidence_file(self, content: str, filename: str, subdir: str = "") -> tuple[str, str]:
        """Save evidence to file and return path and hash"""
        if subdir:
            evidence_dir = self.output_dir / subdir
            evidence_dir.mkdir(parents=True, exist_ok=True)
        else:
            evidence_dir = self.output_dir
            
        filepath = evidence_dir / filename
        
        # Write content
        if isinstance(content, dict):
            with open(filepath, 'w') as f:
                json.dump(content, f, indent=2, default=str)
        else:
            with open(filepath, 'w') as f:
                f.write(str(content))
        
        # Calculate hash
        sha256 = hashlib.sha256()
        with open(filepath, 'rb') as f:
            sha256.update(f.read())
        file_hash = sha256.hexdigest()
        
        return str(filepath), file_hash
    
    def store_evidence_record(self, evidence: EvidenceRecord):
        """Store evidence record in database"""
        with self.get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO evidence (
                        evidence_name, evidence_type, control_implementation_id,
                        collection_method, collection_timestamp, evidence_period_start,
                        evidence_period_end, file_path, file_hash, source_system,
                        source_query, collected_by_id, metadata
                    ) VALUES (
                        %(evidence_name)s, %(evidence_type)s, %(control_implementation_id)s,
                        %(collection_method)s, %(collection_timestamp)s, %(evidence_period_start)s,
                        %(evidence_period_end)s, %(file_path)s, %(file_hash)s, %(source_system)s,
                        %(source_query)s, %(collected_by_id)s, %(metadata)s
                    )
                    RETURNING id
                """, {
                    **asdict(evidence),
                    'collection_timestamp': evidence.collection_timestamp,
                    'evidence_period_start': evidence.evidence_period_start,
                    'evidence_period_end': evidence.evidence_period_end,
                    'metadata': json.dumps(evidence.metadata)
                })
                evidence_id = cur.fetchone()[0]
                conn.commit()
                logger.info(f"Stored evidence record: {evidence_id}")
                return evidence_id


class WazuhEvidenceCollector(EvidenceCollector):
    """Collects evidence from Wazuh SIEM/EDR"""
    
    def __init__(self, db_config: Dict[str, str], output_dir: Path, wazuh_config: Dict[str, str]):
        super().__init__(db_config, output_dir)
        self.wazuh_api_url = wazuh_config['api_url']
        self.wazuh_user = wazuh_config['user']
        self.wazuh_password = wazuh_config['password']
        self.token = self._authenticate()
    
    def _authenticate(self) -> str:
        """Authenticate with Wazuh API"""
        response = requests.post(
            f"{self.wazuh_api_url}/security/user/authenticate",
            auth=(self.wazuh_user, self.wazuh_password),
            verify=False  # Use proper cert in production
        )
        response.raise_for_status()
        return response.json()['data']['token']
    
    def _get_headers(self) -> Dict[str, str]:
        """Get API headers with auth token"""
        return {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
    
    def collect_authentication_logs(self, days: int = 90) -> str:
        """Collect authentication logs for CC6.1 (MFA/authentication)"""
        logger.info(f"Collecting Wazuh authentication logs for last {days} days")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Query Wazuh for authentication events
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"range": {"@timestamp": {"gte": start_date.isoformat(), "lte": end_date.isoformat()}}},
                        {"terms": {"rule.groups": ["authentication_success", "authentication_failed"]}}
                    ]
                }
            },
            "size": 10000
        }
        
        response = requests.post(
            f"{self.wazuh_api_url}/events",
            headers=self._get_headers(),
            json=query
        )
        response.raise_for_status()
        events = response.json()
        
        # Save to file
        filename = f"wazuh-auth-logs-{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}.json"
        filepath, file_hash = self.save_evidence_file(events, filename, "CC6-authentication")
        
        # Create evidence record
        evidence = EvidenceRecord(
            evidence_name=f"Wazuh Authentication Logs ({days} days)",
            evidence_type="log_export",
            control_implementation_id="<control_impl_id>",  # Would be provided
            collection_method="automated",
            collection_timestamp=datetime.now(),
            evidence_period_start=start_date,
            evidence_period_end=end_date,
            file_path=filepath,
            file_hash=file_hash,
            source_system="wazuh",
            source_query=json.dumps(query),
            collected_by_id="<system_user_id>",
            metadata={
                "total_events": len(events.get('data', {}).get('hits', {}).get('hits', [])),
                "api_endpoint": f"{self.wazuh_api_url}/events"
            }
        )
        
        return filepath
    
    def collect_security_alerts(self, severity: str = "high", days: int = 90) -> str:
        """Collect high-severity security alerts for CC7 (monitoring)"""
        logger.info(f"Collecting Wazuh security alerts (severity: {severity}, days: {days})")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"range": {"@timestamp": {"gte": start_date.isoformat(), "lte": end_date.isoformat()}}},
                        {"range": {"rule.level": {"gte": 10 if severity == "high" else 7}}}
                    ]
                }
            },
            "size": 10000,
            "sort": [{"@timestamp": {"order": "desc"}}]
        }
        
        response = requests.post(
            f"{self.wazuh_api_url}/events",
            headers=self._get_headers(),
            json=query
        )
        response.raise_for_status()
        alerts = response.json()
        
        filename = f"wazuh-security-alerts-{severity}-{start_date.strftime('%Y%m%d')}.json"
        filepath, file_hash = self.save_evidence_file(alerts, filename, "CC7-monitoring")
        
        return filepath
    
    def collect_agent_status(self) -> str:
        """Collect Wazuh agent deployment status"""
        logger.info("Collecting Wazuh agent status")
        
        response = requests.get(
            f"{self.wazuh_api_url}/agents",
            headers=self._get_headers()
        )
        response.raise_for_status()
        agents = response.json()
        
        filename = f"wazuh-agent-status-{datetime.now().strftime('%Y%m%d')}.json"
        filepath, file_hash = self.save_evidence_file(agents, filename, "CC7-monitoring")
        
        return filepath


class KeycloakEvidenceCollector(EvidenceCollector):
    """Collects evidence from Keycloak IAM"""
    
    def __init__(self, db_config: Dict[str, str], output_dir: Path, keycloak_config: Dict[str, str]):
        super().__init__(db_config, output_dir)
        self.keycloak_url = keycloak_config['url']
        self.realm = keycloak_config['realm']
        self.client_id = keycloak_config['client_id']
        self.client_secret = keycloak_config['client_secret']
        self.token = self._get_admin_token()
    
    def _get_admin_token(self) -> str:
        """Get Keycloak admin token"""
        response = requests.post(
            f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/token",
            data={
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'grant_type': 'client_credentials'
            }
        )
        response.raise_for_status()
        return response.json()['access_token']
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
    
    def collect_mfa_config(self) -> str:
        """Collect MFA configuration for CC6.1"""
        logger.info("Collecting Keycloak MFA configuration")
        
        # Get realm authentication flows
        response = requests.get(
            f"{self.keycloak_url}/admin/realms/{self.realm}/authentication/flows",
            headers=self._get_headers()
        )
        response.raise_for_status()
        flows = response.json()
        
        # Get required actions
        response = requests.get(
            f"{self.keycloak_url}/admin/realms/{self.realm}/authentication/required-actions",
            headers=self._get_headers()
        )
        response.raise_for_status()
        required_actions = response.json()
        
        config_data = {
            "authentication_flows": flows,
            "required_actions": required_actions,
            "collection_date": datetime.now().isoformat()
        }
        
        filename = f"keycloak-mfa-config-{datetime.now().strftime('%Y%m%d')}.json"
        filepath, file_hash = self.save_evidence_file(config_data, filename, "CC6-authentication")
        
        return filepath
    
    def collect_user_list(self) -> str:
        """Collect user list for access reviews (CC6.3)"""
        logger.info("Collecting Keycloak user list")
        
        response = requests.get(
            f"{self.keycloak_url}/admin/realms/{self.realm}/users",
            headers=self._get_headers(),
            params={'max': 10000}
        )
        response.raise_for_status()
        users = response.json()
        
        # Sanitize sensitive data
        sanitized_users = []
        for user in users:
            sanitized_users.append({
                'id': user['id'],
                'username': user['username'],
                'email': user.get('email', ''),
                'enabled': user['enabled'],
                'createdTimestamp': user['createdTimestamp'],
                'groups': user.get('groups', []),
                'requiredActions': user.get('requiredActions', [])
            })
        
        filename = f"keycloak-users-{datetime.now().strftime('%Y%m%d')}.json"
        filepath, file_hash = self.save_evidence_file(
            {'users': sanitized_users, 'total': len(sanitized_users)},
            filename,
            "CC6-access-reviews"
        )
        
        return filepath
    
    def collect_role_mappings(self) -> str:
        """Collect role mappings for RBAC evidence (CC6.2)"""
        logger.info("Collecting Keycloak role mappings")
        
        response = requests.get(
            f"{self.keycloak_url}/admin/realms/{self.realm}/roles",
            headers=self._get_headers()
        )
        response.raise_for_status()
        roles = response.json()
        
        filename = f"keycloak-roles-{datetime.now().strftime('%Y%m%d')}.json"
        filepath, file_hash = self.save_evidence_file(roles, filename, "CC6-access-controls")
        
        return filepath


class OpenSCAPCollector(EvidenceCollector):
    """Collects OpenSCAP compliance scan results"""
    
    def __init__(self, db_config: Dict[str, str], output_dir: Path, oscap_config: Dict[str, Any]):
        super().__init__(db_config, output_dir)
        self.profile = oscap_config.get('profile', 'xccdf_org.ssgproject.content_profile_cis')
        self.datastream = oscap_config.get('datastream', '/usr/share/xml/scap/ssg/content/ssg-ubuntu2204-ds.xml')
    
    def run_compliance_scan(self, target: str = "localhost") -> str:
        """Run OpenSCAP compliance scan"""
        logger.info(f"Running OpenSCAP scan on {target}")
        
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        report_path = self.output_dir / f"oscap-report-{target}-{timestamp}.html"
        results_path = self.output_dir / f"oscap-results-{target}-{timestamp}.xml"
        
        cmd = [
            'oscap', 'xccdf', 'eval',
            '--profile', self.profile,
            '--results', str(results_path),
            '--report', str(report_path),
            self.datastream
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            logger.info(f"OpenSCAP scan completed with exit code: {result.returncode}")
        except subprocess.TimeoutExpired:
            logger.error("OpenSCAP scan timed out")
            raise
        
        return str(report_path)


class GitHubAuditCollector(EvidenceCollector):
    """Collects audit logs from GitHub"""
    
    def __init__(self, db_config: Dict[str, str], output_dir: Path, github_config: Dict[str, str]):
        super().__init__(db_config, output_dir)
        self.org = github_config['organization']
        self.token = github_config['token']
    
    def collect_audit_log(self, days: int = 90) -> str:
        """Collect GitHub audit log for change management (CC8)"""
        logger.info(f"Collecting GitHub audit log for last {days} days")
        
        headers = {
            'Authorization': f'token {self.token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        # GitHub API for audit log (requires GitHub Enterprise)
        response = requests.get(
            f"https://api.github.com/orgs/{self.org}/audit-log",
            headers=headers,
            params={'per_page': 100}
        )
        
        if response.status_code == 200:
            audit_events = response.json()
            filename = f"github-audit-log-{datetime.now().strftime('%Y%m%d')}.json"
            filepath, file_hash = self.save_evidence_file(audit_events, filename, "CC8-change-mgmt")
            return filepath
        else:
            logger.warning(f"GitHub audit log not available: {response.status_code}")
            return None


class EvidenceOrchestrator:
    """Orchestrates evidence collection across all sources"""
    
    def __init__(self, config_path: str):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.output_dir = Path(self.config['evidence']['output_dir'])
        self.db_config = self.config['database']
        
        # Initialize collectors
        self.collectors = {
            'wazuh': WazuhEvidenceCollector(
                self.db_config,
                self.output_dir,
                self.config['wazuh']
            ) if 'wazuh' in self.config else None,
            
            'keycloak': KeycloakEvidenceCollector(
                self.db_config,
                self.output_dir,
                self.config['keycloak']
            ) if 'keycloak' in self.config else None,
            
            'openscap': OpenSCAPCollector(
                self.db_config,
                self.output_dir,
                self.config.get('openscap', {})
            ) if 'openscap' in self.config else None,
            
            'github': GitHubAuditCollector(
                self.db_config,
                self.output_dir,
                self.config['github']
            ) if 'github' in self.config else None,
        }
    
    def collect_all_evidence(self, framework: str = "SOC2"):
        """Collect all evidence for a framework"""
        logger.info(f"Starting evidence collection for {framework}")
        
        evidence_files = []
        
        # Wazuh evidence
        if self.collectors['wazuh']:
            try:
                evidence_files.append(self.collectors['wazuh'].collect_authentication_logs())
                evidence_files.append(self.collectors['wazuh'].collect_security_alerts())
                evidence_files.append(self.collectors['wazuh'].collect_agent_status())
            except Exception as e:
                logger.error(f"Wazuh collection failed: {e}")
        
        # Keycloak evidence
        if self.collectors['keycloak']:
            try:
                evidence_files.append(self.collectors['keycloak'].collect_mfa_config())
                evidence_files.append(self.collectors['keycloak'].collect_user_list())
                evidence_files.append(self.collectors['keycloak'].collect_role_mappings())
            except Exception as e:
                logger.error(f"Keycloak collection failed: {e}")
        
        # OpenSCAP evidence
        if self.collectors['openscap']:
            try:
                evidence_files.append(self.collectors['openscap'].run_compliance_scan())
            except Exception as e:
                logger.error(f"OpenSCAP collection failed: {e}")
        
        # GitHub evidence
        if self.collectors['github']:
            try:
                github_audit = self.collectors['github'].collect_audit_log()
                if github_audit:
                    evidence_files.append(github_audit)
            except Exception as e:
                logger.error(f"GitHub collection failed: {e}")
        
        logger.info(f"Evidence collection complete. Files collected: {len(evidence_files)}")
        return evidence_files


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Evidence Automation Engine')
    parser.add_argument('--config', required=True, help='Path to config YAML file')
    parser.add_argument('--framework', default='SOC2', help='Compliance framework')
    
    args = parser.parse_args()
    
    orchestrator = EvidenceOrchestrator(args.config)
    evidence_files = orchestrator.collect_all_evidence(args.framework)
    
    print(f"\n✅ Evidence collection complete!")
    print(f"📁 Evidence files: {len(evidence_files)}")
    for filepath in evidence_files:
        print(f"   - {filepath}")


if __name__ == "__main__":
    main()
