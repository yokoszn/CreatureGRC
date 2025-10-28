#!/usr/bin/env python3
"""
Audit Package Generator
Creates audit-ready evidence packages organized by control domains
"""

import os
import sys
import json
import zipfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import yaml
from jinja2 import Template
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AuditPackageGenerator:
    """Generates audit evidence packages"""
    
    def __init__(self, db_config: Dict[str, str], output_dir: Path):
        self.db_config = db_config
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config, cursor_factory=RealDictCursor)
    
    def get_framework_controls(self, framework_name: str) -> List[Dict]:
        """Get all controls for a framework"""
        with self.get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        cf.name AS framework_name,
                        cd.domain_code,
                        cd.domain_name,
                        c.id AS control_id,
                        c.control_code,
                        c.control_name,
                        c.control_description,
                        c.control_type,
                        c.testing_procedures,
                        ci.id AS control_implementation_id,
                        ci.implementation_status,
                        ci.implementation_description,
                        ci.automation_level,
                        ci.last_test_date,
                        ci.next_test_date,
                        p.full_name AS responsible_party,
                        pol.policy_name,
                        pol.document_url AS policy_url
                    FROM compliance_frameworks cf
                    JOIN control_domains cd ON cf.id = cd.framework_id
                    JOIN controls c ON cd.id = c.domain_id
                    LEFT JOIN control_implementations ci ON c.id = ci.control_id
                    LEFT JOIN persons p ON ci.responsible_party_id = p.id
                    LEFT JOIN policies pol ON ci.policy_id = pol.id
                    WHERE cf.name = %s
                    ORDER BY cd.domain_code, c.control_code
                """, (framework_name,))
                return cur.fetchall()
    
    def get_control_evidence(self, control_impl_id: str) -> List[Dict]:
        """Get all evidence for a control implementation"""
        with self.get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        e.id,
                        e.evidence_name,
                        e.evidence_type,
                        e.collection_timestamp,
                        e.evidence_period_start,
                        e.evidence_period_end,
                        e.file_path,
                        e.file_hash,
                        e.source_system,
                        e.source_query,
                        e.review_status,
                        p.full_name AS collected_by
                    FROM evidence e
                    LEFT JOIN persons p ON e.collected_by_id = p.id
                    WHERE e.control_implementation_id = %s
                    ORDER BY e.collection_timestamp DESC
                """, (control_impl_id,))
                return cur.fetchall()
    
    def get_audit_findings(self, control_impl_id: str) -> List[Dict]:
        """Get audit findings for a control"""
        with self.get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        af.finding_title,
                        af.finding_description,
                        af.severity,
                        af.status,
                        af.identified_date,
                        af.remediation_plan,
                        af.due_date,
                        af.resolution_date,
                        p.full_name AS remediation_owner
                    FROM audit_findings af
                    LEFT JOIN persons p ON af.remediation_owner_id = p.id
                    WHERE af.control_implementation_id = %s
                    AND af.status IN ('open', 'in_progress')
                    ORDER BY af.severity DESC, af.identified_date DESC
                """, (control_impl_id,))
                return cur.fetchall()
    
    def generate_control_summary_html(self, control: Dict, evidence: List[Dict], findings: List[Dict]) -> str:
        """Generate HTML summary for a control"""
        template = Template('''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{{ control.control_code }}: {{ control.control_name }}</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 1200px; margin: 20px auto; padding: 0 20px; }
        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
        h2 { color: #34495e; margin-top: 30px; border-bottom: 2px solid #ecf0f1; padding-bottom: 5px; }
        .control-info { background: #ecf0f1; padding: 15px; border-radius: 5px; margin: 20px 0; }
        .status-implemented { color: #27ae60; font-weight: bold; }
        .status-not-implemented { color: #e74c3c; font-weight: bold; }
        .status-partial { color: #f39c12; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th { background: #34495e; color: white; padding: 12px; text-align: left; }
        td { padding: 10px; border-bottom: 1px solid #ecf0f1; }
        tr:hover { background: #f8f9fa; }
        .evidence-item { margin: 10px 0; padding: 10px; background: #f8f9fa; border-left: 4px solid #3498db; }
        .finding-critical { border-left: 4px solid #e74c3c; }
        .finding-high { border-left: 4px solid #e67e22; }
        .finding-medium { border-left: 4px solid #f39c12; }
        .finding-low { border-left: 4px solid #3498db; }
        .metadata { font-size: 0.9em; color: #7f8c8d; }
    </style>
</head>
<body>
    <h1>{{ control.control_code }}: {{ control.control_name }}</h1>
    
    <div class="control-info">
        <p><strong>Framework:</strong> {{ control.framework_name }}</p>
        <p><strong>Domain:</strong> {{ control.domain_code }} - {{ control.domain_name }}</p>
        <p><strong>Control Type:</strong> {{ control.control_type|capitalize }}</p>
        <p><strong>Implementation Status:</strong> 
            <span class="status-{{ control.implementation_status }}">{{ control.implementation_status|upper }}</span>
        </p>
        <p><strong>Automation Level:</strong> {{ control.automation_level|capitalize|replace('_', ' ') }}</p>
        <p><strong>Responsible Party:</strong> {{ control.responsible_party or 'Not assigned' }}</p>
        <p><strong>Last Tested:</strong> {{ control.last_test_date or 'Never' }}</p>
        <p><strong>Next Test Due:</strong> {{ control.next_test_date or 'Not scheduled' }}</p>
    </div>
    
    <h2>Control Description</h2>
    <p>{{ control.control_description }}</p>
    
    {% if control.implementation_description %}
    <h2>Implementation Details</h2>
    <p>{{ control.implementation_description }}</p>
    {% endif %}
    
    {% if control.policy_name %}
    <h2>Related Policies</h2>
    <p><strong>Policy:</strong> {{ control.policy_name }}</p>
    {% if control.policy_url %}
    <p><strong>Document:</strong> <a href="{{ control.policy_url }}">{{ control.policy_url }}</a></p>
    {% endif %}
    {% endif %}
    
    <h2>Testing Procedures</h2>
    <p>{{ control.testing_procedures or 'No specific testing procedures defined.' }}</p>
    
    <h2>Evidence ({{ evidence|length }} items)</h2>
    {% if evidence %}
        {% for item in evidence %}
        <div class="evidence-item">
            <strong>{{ item.evidence_name }}</strong>
            <p class="metadata">
                Type: {{ item.evidence_type }} | 
                Source: {{ item.source_system }} | 
                Collected: {{ item.collection_timestamp }}
                {% if item.evidence_period_start and item.evidence_period_end %}
                | Period: {{ item.evidence_period_start }} to {{ item.evidence_period_end }}
                {% endif %}
            </p>
            <p><strong>File:</strong> <code>{{ item.file_path }}</code></p>
            <p><strong>SHA256:</strong> <code>{{ item.file_hash }}</code></p>
            <p><strong>Review Status:</strong> {{ item.review_status or 'Pending' }}</p>
        </div>
        {% endfor %}
    {% else %}
        <p><em>No evidence collected for this control yet.</em></p>
    {% endif %}
    
    {% if findings %}
    <h2>⚠️ Open Findings ({{ findings|length }})</h2>
    {% for finding in findings %}
    <div class="evidence-item finding-{{ finding.severity }}">
        <strong>{{ finding.finding_title }}</strong> 
        <span class="metadata">[{{ finding.severity|upper }}] - {{ finding.status|replace('_', ' ')|capitalize }}</span>
        <p>{{ finding.finding_description }}</p>
        <p><strong>Identified:</strong> {{ finding.identified_date }}</p>
        {% if finding.remediation_plan %}
        <p><strong>Remediation Plan:</strong> {{ finding.remediation_plan }}</p>
        <p><strong>Owner:</strong> {{ finding.remediation_owner }} | <strong>Due:</strong> {{ finding.due_date }}</p>
        {% endif %}
    </div>
    {% endfor %}
    {% endif %}
    
    <hr style="margin: 40px 0;">
    <p class="metadata">Generated on {{ generation_date }} by GRC Platform</p>
</body>
</html>
        ''')
        
        return template.render(
            control=control,
            evidence=evidence,
            findings=findings,
            generation_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
    
    def generate_framework_summary(self, framework_name: str, controls: List[Dict]) -> str:
        """Generate executive summary for the framework"""
        # Calculate statistics
        total_controls = len(controls)
        implemented = sum(1 for c in controls if c['implementation_status'] == 'implemented')
        not_implemented = sum(1 for c in controls if c['implementation_status'] == 'not_implemented')
        partial = sum(1 for c in controls if c['implementation_status'] == 'partially_implemented')
        automated = sum(1 for c in controls if c['automation_level'] == 'fully_automated')
        
        # Group by domain
        domains = {}
        for control in controls:
            domain = control['domain_code']
            if domain not in domains:
                domains[domain] = {
                    'name': control['domain_name'],
                    'controls': []
                }
            domains[domain]['controls'].append(control)
        
        template = Template('''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{{ framework_name }} Compliance Summary</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 1200px; margin: 20px auto; padding: 0 20px; }
        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
        h2 { color: #34495e; margin-top: 30px; }
        .summary-box { background: #ecf0f1; padding: 20px; border-radius: 5px; margin: 20px 0; }
        .stat { display: inline-block; margin: 10px 20px 10px 0; }
        .stat-number { font-size: 2em; font-weight: bold; color: #3498db; }
        .stat-label { font-size: 0.9em; color: #7f8c8d; }
        .progress-bar { background: #ecf0f1; height: 30px; border-radius: 5px; overflow: hidden; margin: 10px 0; }
        .progress-fill { height: 100%; background: #27ae60; text-align: center; color: white; line-height: 30px; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th { background: #34495e; color: white; padding: 12px; text-align: left; }
        td { padding: 10px; border-bottom: 1px solid #ecf0f1; }
        .status-ok { color: #27ae60; }
        .status-warn { color: #f39c12; }
        .status-error { color: #e74c3c; }
    </style>
</head>
<body>
    <h1>{{ framework_name }} Compliance Report</h1>
    <p><strong>Generated:</strong> {{ generation_date }}</p>
    
    <div class="summary-box">
        <h2>Executive Summary</h2>
        <div class="stat">
            <div class="stat-number">{{ total_controls }}</div>
            <div class="stat-label">Total Controls</div>
        </div>
        <div class="stat">
            <div class="stat-number">{{ implemented }}</div>
            <div class="stat-label">Implemented</div>
        </div>
        <div class="stat">
            <div class="stat-number">{{ partial }}</div>
            <div class="stat-label">Partial</div>
        </div>
        <div class="stat">
            <div class="stat-number">{{ not_implemented }}</div>
            <div class="stat-label">Not Implemented</div>
        </div>
        <div class="stat">
            <div class="stat-number">{{ automated }}</div>
            <div class="stat-label">Automated</div>
        </div>
        
        <h3>Implementation Progress</h3>
        <div class="progress-bar">
            <div class="progress-fill" style="width: {{ (implemented / total_controls * 100)|round(1) }}%">
                {{ (implemented / total_controls * 100)|round(1) }}% Complete
            </div>
        </div>
    </div>
    
    <h2>Control Domains</h2>
    <table>
        <thead>
            <tr>
                <th>Domain</th>
                <th>Controls</th>
                <th>Implemented</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
            {% for domain_code, domain_data in domains.items() %}
            <tr>
                <td><strong>{{ domain_code }}</strong> - {{ domain_data.name }}</td>
                <td>{{ domain_data.controls|length }}</td>
                <td>{{ domain_data.controls|selectattr('implementation_status', 'equalto', 'implemented')|list|length }}</td>
                <td>
                    {% set impl_pct = (domain_data.controls|selectattr('implementation_status', 'equalto', 'implemented')|list|length / domain_data.controls|length * 100) %}
                    {% if impl_pct == 100 %}
                        <span class="status-ok">✓ Complete</span>
                    {% elif impl_pct >= 75 %}
                        <span class="status-warn">⚠ In Progress</span>
                    {% else %}
                        <span class="status-error">✗ Needs Attention</span>
                    {% endif %}
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    
    <h2>Control Details</h2>
    <p>See individual control folders for detailed evidence and testing results.</p>
    
</body>
</html>
        ''')
        
        return template.render(
            framework_name=framework_name,
            generation_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            total_controls=total_controls,
            implemented=implemented,
            not_implemented=not_implemented,
            partial=partial,
            automated=automated,
            domains=domains
        )
    
    def generate_audit_package(self, client: str, framework: str) -> str:
        """Generate complete audit evidence package"""
        logger.info(f"Generating audit package for {client} - {framework}")
        
        # Create package directory
        timestamp = datetime.now().strftime('%Y%m%d')
        package_name = f"{client}-{framework}-evidence-{timestamp}"
        package_dir = self.output_dir / package_name
        package_dir.mkdir(parents=True, exist_ok=True)
        
        # Get all controls for framework
        controls = self.get_framework_controls(framework)
        logger.info(f"Found {len(controls)} controls for {framework}")
        
        # Group controls by domain
        domains = {}
        for control in controls:
            domain_code = control['domain_code']
            if domain_code not in domains:
                domains[domain_code] = []
            domains[domain_code].append(control)
        
        # Create directory structure and generate HTML for each control
        for domain_code, domain_controls in domains.items():
            domain_dir = package_dir / f"{domain_code}-{domain_controls[0]['domain_name'].replace(' ', '-').lower()}"
            domain_dir.mkdir(parents=True, exist_ok=True)
            
            for control in domain_controls:
                if not control['control_implementation_id']:
                    continue
                
                # Get evidence and findings
                evidence = self.get_control_evidence(control['control_implementation_id'])
                findings = self.get_audit_findings(control['control_implementation_id'])
                
                # Generate control summary HTML
                html = self.generate_control_summary_html(control, evidence, findings)
                html_file = domain_dir / f"{control['control_code']}.html"
                with open(html_file, 'w') as f:
                    f.write(html)
                
                # Copy evidence files
                for ev in evidence:
                    if ev['file_path'] and Path(ev['file_path']).exists():
                        evidence_file = Path(ev['file_path'])
                        dest_file = domain_dir / evidence_file.name
                        try:
                            shutil.copy2(evidence_file, dest_file)
                        except Exception as e:
                            logger.warning(f"Could not copy evidence file {evidence_file}: {e}")
        
        # Generate framework summary
        summary_html = self.generate_framework_summary(framework, controls)
        with open(package_dir / "00-SUMMARY.html", 'w') as f:
            f.write(summary_html)
        
        # Create README
        readme_content = f"""
# {framework} Audit Evidence Package
**Client:** {client}
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Package Contents

- `00-SUMMARY.html` - Executive summary and compliance dashboard
- Each control domain has its own directory (e.g., CC1-control-environment/)
- Within each domain:
  - Control summary HTML files (e.g., CC1.1.html)
  - Evidence files referenced in the summaries

## How to Review

1. Start with `00-SUMMARY.html` for high-level compliance status
2. Navigate to specific control domains of interest
3. Open control HTML files to see implementation details and evidence
4. Evidence files are stored alongside their control summaries

## Evidence Verification

All evidence files include SHA256 hashes in their control summaries for integrity verification.

## Questions?

Contact: GRC Team
Generated by: GRC Platform (Open Source)
        """
        
        with open(package_dir / "README.md", 'w') as f:
            f.write(readme_content)
        
        # Create ZIP archive
        zip_path = self.output_dir / f"{package_name}.zip"
        logger.info(f"Creating ZIP archive: {zip_path}")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(package_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(package_dir.parent)
                    zipf.write(file_path, arcname)
        
        # Clean up directory (optional - keep it for now)
        # shutil.rmtree(package_dir)
        
        logger.info(f"✅ Audit package generated: {zip_path}")
        return str(zip_path)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate Audit Evidence Package')
    parser.add_argument('--client', required=True, help='Client name')
    parser.add_argument('--framework', required=True, choices=['SOC2', 'ISO27001', 'NIST-800-53', 'HIPAA', 'PCI-DSS'], help='Compliance framework')
    parser.add_argument('--config', required=True, help='Database config file')
    parser.add_argument('--output-dir', default='/tmp/audit-packages', help='Output directory')
    
    args = parser.parse_args()
    
    # Load database config
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
    
    generator = AuditPackageGenerator(
        config['database'],
        Path(args.output_dir)
    )
    
    package_path = generator.generate_audit_package(args.client, args.framework)
    
    print(f"\n✅ Audit package generated successfully!")
    print(f"📦 Location: {package_path}")
    print(f"\nExtract and open 00-SUMMARY.html to review compliance status.")


if __name__ == "__main__":
    main()
